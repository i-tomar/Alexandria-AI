import chromadb
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .utils.similarity import keyword_similarity
from .utils.transcript_store import get_chunks
from .utils.gemini_client import generate_text, gemini_available


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
        history_text = "\n\nPrevious conversation:\n" + "\n\n".join(turns)
    return (
        "You are the AI Learning Companion. Answer only from the provided transcript context. "
        "If the context does not contain the answer, say you could not find it in the video. "
        "Keep the answer concise, human-like, and grounded in the transcript. Do not invent facts.\n\n"
        f"Transcript context:\n{context}\n\n"
        f"Question: {question}\n"
        f"{history_text}\n\n"
        "Answer with a short paragraph."
    )

def ask_question(video_id, question, history=[]):
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get(where={"video_id": video_id})
        if not results['ids']:
            raise Exception("No data found")
        texts = results['metadatas']
        embeddings = results.get('embeddings')
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
    if embeddings:
        try:
            model_emb = SentenceTransformer('all-MiniLM-L6-v2')
            q_emb = model_emb.encode([question])[0]
            similarities = cosine_similarity([q_emb], embeddings)[0]
            best_idx = int(np.argmax(similarities))
            top_indices = list(np.argsort(similarities)[::-1][:3])
        except Exception as e:
            print(f"Embedding QA failed: {e}, falling back to text matching")
            embeddings = None

    if embeddings is None:
        try:
            model_emb = SentenceTransformer('all-MiniLM-L6-v2')
            text_embs = model_emb.encode([t['text'] for t in texts])
            q_emb = model_emb.encode([question])[0]
            similarities = cosine_similarity([q_emb], text_embs)[0]
            best_idx = int(np.argmax(similarities))
            top_indices = list(np.argsort(similarities)[::-1][:3])
        except Exception as e:
            print(f"Text embedding failed: {e}, using keyword matching")
            similarities = [keyword_similarity(question, t['text']) for t in texts]
            best_idx = int(np.argmax(similarities))
            top_indices = list(np.argsort(similarities)[::-1][:3])

    selected_chunks = [texts[i] for i in top_indices if i < len(texts)] or [texts[best_idx]]
    best_chunk = selected_chunks[0]
    timestamps = [best_chunk.get('start_time', 0), best_chunk.get('end_time', 0)]

    context = _format_context(selected_chunks)
    answer = None
    if gemini_available():
        prompt = _build_answer_prompt(question, context, history)
        try:
            answer = generate_text(prompt, temperature=0.2, max_output_tokens=256)
        except Exception as e:
            print(f"Gemini QA failed: {e}")

    if not answer:
        answer = best_chunk.get('text', '').strip()
    if not answer:
        answer = "I found a relevant section, but the transcript chunk is empty."
    return answer, timestamps
