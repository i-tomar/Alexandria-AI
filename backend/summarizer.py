import chromadb
from .utils.summary_helper import summarize_by_topics, get_last_n_minutes_summary
from .utils.transcript_store import get_chunks
from .utils.gemini_client import generate_text, gemini_available


def _build_overall_summary_prompt(chunks):
    context = []
    for chunk in chunks[:16]:
        context.append(f"({chunk.get('start', 0):.2f}-{chunk.get('end', 0):.2f}s) {chunk.get('text', '')}")
    return (
        "Write a concise overall summary of the video transcript below. "
        "Stay faithful to the transcript only. Do not add outside knowledge.\n\n"
        + "\n".join(context)
    )

def get_summary(video_id):
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get(where={"video_id": video_id})
        chunks = [
            {
                'text': m.get('text', ''),
                'start': m.get('start_time', 0),
                'end': m.get('end_time', 0)
            }
            for m in results['metadatas']
        ]
        # Start with a compact concatenation of the first few chunks
        summary = " ".join([c['text'] for c in chunks[:12] if c.get('text')])
        # Prefer the Gemini summarizer when available; otherwise try a lightweight local topic summary
        if chunks and gemini_available():
            try:
                gemini_summary = generate_text(_build_overall_summary_prompt(chunks), temperature=0.2, max_output_tokens=220)
                if gemini_summary:
                    summary = gemini_summary
            except Exception as e:
                print(f"Gemini overall summary failed: {e}")
                # fall through to local summarization below
        else:
            try:
                # Derive a compact overall summary from topic summaries if possible
                topics = summarize_by_topics(" ".join([c.get('text', '') for c in chunks]), chunks)
                if topics:
                    # Join the first few topic summaries into a single paragraph
                    summary = " ".join([t.get('summary', '') for t in topics[:4]]).strip()
            except Exception as e:
                print(f"Local topic summarization failed: {e}")
        # Ensure summary isn't excessively long; truncate to a reasonable size
        if summary and len(summary) > 1200:
            summary = summary[:1200].rsplit('.', 1)[0] + '.'
    except Exception as e:
        print(f"Summary failed: {e}, using fallback")
        chunks = get_chunks(video_id)[:5]
        summary = " ".join([c['text'] for c in chunks])
    if not summary:
        return "Summary is not available yet. Please ingest a video first."
    return summary

def get_topic_summaries(video_id):
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get(where={"video_id": video_id})
        if not results['ids']:
            raise Exception("No data found")
        chunks = [
            {
                'text': m.get('text', ''),
                'start': m.get('start_time', 0),
                'end': m.get('end_time', 0)
            }
            for m in results['metadatas']
        ]
        full_text = " ".join([c['text'] for c in chunks])
    except Exception as e:
        print(f"Topic summary failed: {e}, using fallback")
        chunks = get_chunks(video_id)
        full_text = " ".join([c['text'] for c in chunks])
    
    if not chunks:
        return []
    return summarize_by_topics(full_text, chunks)

def get_last_minutes_summary(video_id, minutes: int = 5):
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get(where={"video_id": video_id})
        if not results['ids']:
            raise Exception("No data found")
        chunks = [
            {
                'text': m.get('text', ''),
                'start': m.get('start_time', 0),
                'end': m.get('end_time', 0)
            }
            for m in results['metadatas']
        ]
    except Exception as e:
        print(f"Last N minutes summary failed: {e}, using fallback")
        chunks = get_chunks(video_id)
    
    if not chunks:
        return {"summary": "No content available", "timestamp": 0}
    
    summary_text, timestamp = get_last_n_minutes_summary(chunks, minutes)
    return {"summary": summary_text, "timestamp": timestamp}
