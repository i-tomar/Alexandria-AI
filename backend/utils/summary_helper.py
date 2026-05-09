import re
from typing import List, Tuple
from .gemini_client import generate_text, gemini_available


def _chunk_context(chunks: List[dict], limit: int = 12) -> str:
    parts = []
    for chunk in chunks[:limit]:
        start = chunk.get('start', 0)
        end = chunk.get('end', 0)
        parts.append(f"({start:.2f}-{end:.2f}s) {chunk.get('text', '').strip()}")
    return "\n".join(parts)

def extract_topics(text: str, num_topics: int = 5) -> List[str]:
    """Extract key topics from text using simple heuristics."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    topics = []
    seen = set()
    for sentence in sentences[:20]:
        words = sentence.lower().split()
        key_words = [w for w in words if len(w) > 5 and w not in {'about', 'which', 'would', 'there', 'their', 'these'}]
        if key_words:
            topic = ' '.join(key_words[:3])
            if topic not in seen:
                topics.append(sentence[:100])
                seen.add(topic)
                if len(topics) >= num_topics:
                    break
    return topics

def summarize_by_topics(text: str, chunks: List[dict]) -> List[dict]:
    """Create topic-wise summaries from chunks."""
    if not chunks:
        return []
    topics = extract_topics(text, num_topics=5)
    result = []
    for i, topic in enumerate(topics):
        relevant_chunks = []
        for chunk in chunks:
            chunk_text = chunk.get('text', '').lower()
            if any(word in chunk_text for word in topic.lower().split()[:2]):
                relevant_chunks.append(chunk)
        if relevant_chunks:
            summary_text = ' '.join([c.get('text', '')[:150] for c in relevant_chunks[:2]])
            if gemini_available():
                prompt = (
                    "Summarize the following transcript snippets as a short topic summary. "
                    "Stay faithful to the text, avoid adding facts, and keep it concise.\n\n"
                    f"Topic: {topic}\n\nSnippets:\n{_chunk_context(relevant_chunks, limit=6)}"
                )
                try:
                    gemini_summary = generate_text(prompt, temperature=0.2, max_output_tokens=160)
                    if gemini_summary:
                        summary_text = gemini_summary
                except Exception:
                    pass
            result.append({
                'topic': topic[:80],
                'summary': summary_text,
                'timestamp': relevant_chunks[0].get('start', 0)
            })
    return result

def get_last_n_minutes_summary(chunks: List[dict], minutes: int = 5) -> Tuple[str, float]:
    """Get summary of last N minutes based on timestamps."""
    if not chunks:
        return ("No content available", 0)
    last_chunk = chunks[-1]
    end_time = last_chunk.get('end', 0)
    start_time = end_time - (minutes * 60)
    relevant_chunks = [
        c for c in chunks
        if c.get('end', 0) > start_time
    ]
    if relevant_chunks:
        summary_text = ' '.join([c.get('text', '') for c in relevant_chunks])
        if gemini_available():
            prompt = (
                f"Summarize the last {minutes} minutes of this transcript in 2-4 sentences. "
                "Be grounded only in the transcript, concise, and human-readable.\n\n"
                f"Transcript:\n{_chunk_context(relevant_chunks, limit=16)}"
            )
            try:
                gemini_summary = generate_text(prompt, temperature=0.2, max_output_tokens=220)
                if gemini_summary:
                    summary_text = gemini_summary
            except Exception:
                pass
        return (summary_text[:500], relevant_chunks[0].get('start', end_time))
    return (' '.join([c.get('text', '') for c in chunks[-3:]]), end_time - 300)

def format_timestamp(seconds: float) -> str:
    """Format seconds to HH:MM:SS."""
    seconds = max(0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
