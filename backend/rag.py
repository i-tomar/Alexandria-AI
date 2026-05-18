import os
import json
import math
from .utils.similarity import keyword_similarity
from .utils.transcript_store import get_chunks
from .utils.gemini_client import generate_text, gemini_available
from .utils.summary_helper import extractive_summary


def _embeddings_enabled() -> bool:
    return os.getenv("ENABLE_EMBEDDINGS", "0").strip().lower() in {"1", "true", "yes", "on"}


def _chroma_enabled() -> bool:
    return os.getenv("ENABLE_CHROMA", "0").strip().lower() in {"1", "true", "yes", "on"}


def _format_context(chunks):
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        start = chunk.get('start_time', 0)
        end = chunk.get('end_time', 0)
        lines.append(f"[{i}] ({start:.2f}-{end:.2f}s) {chunk.get('text', '').strip()}")
    return "\n".join(lines)


def _build_answer_prompt(question, context, history):
    history_text = ""
    if history:
        turns = []
        for item in history[-4:]:
            turns.append(f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}")
        history_text = "\n\n[Previous conversation for context]:\n" + "\n\n".join(turns)
    
    return (
        "### SYSTEM INSTRUCTION\n"
        "You are a strict 'Video-Grounded Learning Assistant'. Your ONLY source of truth is the provided Transcript Context. "
        "Strictly adhere to these rules:\n"
        "1. If the question is about a topic NOT mentioned in the transcript (e.g., Swiggy, personal advice, or unrelated general knowledge), "
        "you MUST say: 'I'm sorry, but that topic is not discussed in this video.'\n"
        "2. Do NOT use your own internal knowledge to fill in gaps. Only use the transcript.\n"
        "3. If the context is empty or irrelevant, refuse to answer.\n"
        "4. Be concise and academic.\n\n"
        "### TRANSCRIPT CONTEXT\n"
        f"{context}\n\n"
        "### USER QUESTION\n"
        f"{question}\n"
        f"{history_text}\n\n"
        "### RESPONSE"
    )


def _build_quality_guidance(quality_score: str, quality_warnings: list[str]) -> str:
    if quality_score == "low":
        detail = "; ".join(str(w) for w in quality_warnings[:3])
        return (
            "Transcript quality is low. Be careful, brief, and explicitly note uncertainty. "
            f"If useful, mention these warnings: {detail}."
        )
    if quality_score == "medium":
        return "Transcript quality is moderate. Be concise and include a small uncertainty note if the answer is not fully supported."
    return "Transcript quality is high. Answer normally, but stay grounded in the transcript."


def _coerce_warnings(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in value.split(";") if part.strip()]
    return []


_model_cache = {}

def _get_embedding_model():
    if 'model' not in _model_cache:
        try:
            from sentence_transformers import SentenceTransformer
            _model_cache['model'] = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Failed to load embedding model: {e}")
            return None
    return _model_cache['model']


def ask_question(video_id, question, history=None):
    if history is None:
        history = []
    try:
        if _chroma_enabled():
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            collection = client.get_or_create_collection(name="transcripts")
            results = collection.get(where={"video_id": video_id}, include=['metadatas', 'embeddings'])
            if not results['ids']:
                raise Exception("No data found")
            texts = results['metadatas']
            embeddings = results.get('embeddings')
        else:
            raise Exception("Chroma persistence disabled")
    except Exception as e:
        print(f"ChromaDB failed: {e}, using fallback")
        texts = get_chunks(video_id)
        embeddings = None

    if not texts:
        return (
            "I could not find transcript data for that video yet. Please ingest a video first.",
            [0, 0],
        )

    best_idx = 0
    top_indices = [0]
    max_score = 0.0
    
    if _embeddings_enabled():
        model_emb = _get_embedding_model()
        if model_emb and embeddings:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                import numpy as np

                q_emb = model_emb.encode([question])[0]
                similarities = cosine_similarity([q_emb], embeddings)[0]
                max_score = float(np.max(similarities))
                best_idx = int(np.argmax(similarities))
                top_indices = list(np.argsort(similarities)[::-1][:3])
            except Exception as e:
                print(f"Embedding QA failed: {e}, falling back to text matching")
                embeddings = None
        
        if model_emb and not embeddings:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                import numpy as np

                text_embs = model_emb.encode([t['text'] for t in texts])
                q_emb = model_emb.encode([question])[0]
                similarities = cosine_similarity([q_emb], text_embs)[0]
                max_score = float(np.max(similarities))
                best_idx = int(np.argmax(similarities))
                top_indices = list(np.argsort(similarities)[::-1][:3])
            except Exception as e:
                print(f"Text embedding failed: {e}, using keyword matching")
                scored = sorted(
                    [(i, t, keyword_similarity(question, t.get('text', ''))) for i, t in enumerate(texts)],
                    key=lambda x: x[2],
                    reverse=True
                )
                if scored:
                    best_idx = scored[0][0]
                    max_score = scored[0][2]
                    top_indices = [x[0] for x in scored[:3]]
        elif not model_emb:
             scored = sorted(
                [(i, t, keyword_similarity(question, t.get('text', ''))) for i, t in enumerate(texts)],
                key=lambda x: x[2],
                reverse=True
            )
             if scored:
                best_idx = scored[0][0]
                max_score = scored[0][2]
                top_indices = [x[0] for x in scored[:3]]
    else:
        scored = sorted(
            [(i, t, keyword_similarity(question, t.get('text', ''))) for i, t in enumerate(texts)],
            key=lambda x: x[2],
            reverse=True
        )
        if scored:
            best_idx = scored[0][0]
            max_score = scored[0][2]
            top_indices = [x[0] for x in scored[:3]]

    # RELEVANCE GUARD: If the max similarity score is extremely low, 
    # we mark it as irrelevant to prevent hallucinations.
    is_irrelevant = False
    if _embeddings_enabled() and max_score < 0.25:
        is_irrelevant = True
    elif not _embeddings_enabled() and max_score < 0.05:
        is_irrelevant = True

    selected_chunks = [texts[i] for i in top_indices if i < len(texts)] or [texts[best_idx]]
    best_chunk = selected_chunks[0]
    timestamps = [best_chunk.get('start_time', 0), best_chunk.get('end_time', 0)]

    source = str(best_chunk.get('source', '')).lower()
    if source in {"youtube_metadata", "url_only"}:
        return (
            "I could not answer from the actual video speech because no real transcript was available. "
            "I only have YouTube metadata for this link. Try a video with captions, upload the video/audio file, "
            "or use the AssemblyAI transcription path so I can answer from spoken content.",
            timestamps,
        )

    quality_score = str(best_chunk.get('quality_score', 'unknown')).lower()
    quality_warnings = _coerce_warnings(best_chunk.get('quality_warnings'))
    quality_note = ""
    if quality_score == "low":
        quality_note = "Note: this answer is based on a low-confidence transcript, so it may be incomplete or approximate.\n\n"
    elif quality_score == "medium":
        quality_note = "Note: this answer is based on a moderate-confidence transcript.\n\n"

    context = _format_context(selected_chunks)
    answer = None
    if gemini_available():
        # Get video title for better context
        video_title = "Unknown Video"
        if texts and len(texts) > 0:
            video_title = texts[0].get('title', 'this video')

        history_text = ""
        if history:
            turns = []
            for item in history[-4:]:
                turns.append(f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}")
            history_text = "\n\n[Previous conversation for context]:\n" + "\n\n".join(turns)


        prompt = (
            "### ROLE\n"
            "You are Alexandria, a brilliant AI Learning Companion. Your goal is to help the user master the content of the video "
            f"titled '{video_title}'.\n\n"
            "### TRANSCRIPT CONTEXT\n"
            f"{context}\n\n"
            "### RULES\n"
            "1. Be helpful, clear, and structured. Use bullet points if helpful.\n"
            "2. STAY GROUNDED: Only use info from the transcript. If a question is totally unrelated to the video topic, politely say so.\n"
            "3. If the user asks 'what is this about', use the context and the title to give a high-level summary.\n\n"
            "### USER QUESTION\n"
            f"{question}\n"
            f"{history_text}\n\n"
            "### YOUR RESPONSE"
        )

        if is_irrelevant:
            # Special nudge for irrelevant questions
            prompt = "NOTE: The user is asking something that might be outside the video. Check carefully.\n" + prompt
        
        quality_guidance = _build_quality_guidance(quality_score, quality_warnings)
        prompt = f"{quality_guidance}\n\n{prompt}"
        try:
            answer = generate_text(prompt, temperature=0.4, max_output_tokens=512)
        except Exception as e:
            print(f"Gemini QA failed: {e}")

    if not answer:
        # Create a concise local answer by extractive-summarizing the selected chunks
        try:
            combined = ' '.join([c.get('text', '') for c in selected_chunks])
            answer = extractive_summary(combined, num_sentences=2)
        except Exception:
            answer = best_chunk.get('text', '').strip()
    if not answer:
        answer = "I found a relevant section, but the transcript chunk is empty."

    if quality_note and answer:
        answer = f"{quality_note}{answer}"
        if quality_warnings:
            answer += "\n\nTranscript warnings: " + "; ".join(str(w) for w in quality_warnings[:3])

    return answer, timestamps


def stream_question(video_id, question, history=None):
    if history is None:
        history = []
    
    # 1. Retrieval (Same as ask_question)
    try:
        if _chroma_enabled():
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            collection = client.get_or_create_collection(name="transcripts")
            results = collection.get(where={"video_id": video_id}, include=['metadatas', 'embeddings'])
            if not results['ids']:
                raise Exception("No data found")
            texts = results['metadatas']
            embeddings = results.get('embeddings')
        else:
            texts = get_chunks(video_id)
            embeddings = None
    except Exception as e:
        texts = get_chunks(video_id)
        embeddings = None

    if not texts:
        yield json.dumps({"chunk": "I could not find transcript data for that video yet. Please ingest a video first."}) + "\n"
        yield json.dumps({"done": True}) + "\n"
        return

    # 2. Ranking & Relevance (Same as ask_question)
    # (Abbreviated ranking logic for speed, focusing on the core generator)
    best_idx = 0
    top_indices = [0]
    max_score = 0.0
    
    scored = sorted(
        [(i, t, keyword_similarity(question, t.get('text', ''))) for i, t in enumerate(texts)],
        key=lambda x: x[2],
        reverse=True
    )
    if scored:
        best_idx = scored[0][0]
        max_score = scored[0][2]
        top_indices = [x[0] for x in scored[:3]]

    is_irrelevant = max_score < 0.05
    selected_chunks = [texts[i] for i in top_indices if i < len(texts)] or [texts[best_idx]]
    timestamps = [selected_chunks[0].get('start_time', 0), selected_chunks[0].get('end_time', 0)]
    context = _format_context(selected_chunks)

    # 3. Streaming (New logic)
    from .utils.gemini_client import gemini_available, generate_text_stream
    if gemini_available():
        # Get video title
        video_title = texts[0].get('title', 'this video')
        
        history_text = ""
        if history:
            turns = []
            for item in history[-4:]:
                turns.append(f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}")
            history_text = "\n\n[Previous conversation for context]:\n" + "\n\n".join(turns)
        
        prompt = (
            "### ROLE\n"
            "You are Alexandria, a brilliant AI Learning Companion. Answer concisely based on "
            f"'{video_title}'.\n\n"
            f"### CONTEXT\n{context}\n\n"
            f"### QUESTION\n{question}\n\n"
            "### RESPONSE"
        )
        
        if is_irrelevant:
            prompt = "NOTE: Context might be irrelevant. Use caution.\n" + prompt

        full_answer = ""
        for token in generate_text_stream(prompt, temperature=0.4):
            full_answer += token
            yield json.dumps({"chunk": token}) + "\n"
        
        yield json.dumps({"timestamps": timestamps, "done": True}) + "\n"
    else:
        # Fallback to extractive if Gemini unavailable
        combined = ' '.join([c.get('text', '') for c in selected_chunks])
        answer = extractive_summary(combined, num_sentences=2)
        for char in answer:
            yield json.dumps({"chunk": char}) + "\n"
        yield json.dumps({"timestamps": timestamps, "done": True}) + "\n"
