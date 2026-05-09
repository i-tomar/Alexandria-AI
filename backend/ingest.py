from sentence_transformers import SentenceTransformer
import chromadb
import re
import importlib
from .utils.chunker import chunk_transcript
from .utils.transcript_loader import load_transcript
from .utils.transcript_store import store_chunks
from .utils.assemblyai_client import transcribe_uploaded_file, assemblyai_available

_youtube_transcript_spec = importlib.util.find_spec("youtube_transcript_api")
if _youtube_transcript_spec is not None:
    YouTubeTranscriptApi = importlib.import_module("youtube_transcript_api").YouTubeTranscriptApi
else:
    YouTubeTranscriptApi = None


def _extract_youtube_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)",
        r"youtu\.be\/([0-9A-Za-z_-]{11})(?:[&?]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _load_youtube_transcript(url: str):
    if not YouTubeTranscriptApi:
        print("YouTubeTranscriptApi not installed; skipping YouTube subtitle load.")
        return None
    video_id = _extract_youtube_id(url)
    if not video_id:
        return None
    try:
        # Newer versions expose `list_transcripts` as a classmethod
        if hasattr(YouTubeTranscriptApi, "list_transcripts"):
            print(f"Using YouTubeTranscriptApi.list_transcripts for {video_id}")
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

            # Prefer manually created English, then generated English, then translations
            for finder in ("find_manually_created_transcript", "find_generated_transcript", "find_transcript"):
                if hasattr(transcripts, finder):
                    try:
                        t = getattr(transcripts, finder)(["en"])
                        return list(t.fetch())
                    except Exception:
                        pass

            for t in transcripts:
                try:
                    translated = t.translate("en")
                    entries = list(translated.fetch())
                    print(f"Translated transcript fetched: {len(entries)} entries")
                    return entries
                except Exception:
                    continue

            try:
                entries = YouTubeTranscriptApi.get_transcript(video_id)
                entries = list(entries)
                print(f"get_transcript returned {len(entries)} entries")
                return entries
            except Exception as e:
                print(f"YouTube subtitle load failed: {e}")
                return None

        # Older versions use instance methods `list` and `fetch`
        print(f"Falling back to instance API for {video_id}")
        api = YouTubeTranscriptApi()
        try:
            transcripts = api.list(video_id)
        except Exception:
            transcripts = None

        # If we got a TranscriptList, try to pick English or translated transcripts
        if transcripts is not None:
            # Try methods that may exist on TranscriptList
            for finder in ("find_manually_created_transcript", "find_generated_transcript", "find_transcript"):
                if hasattr(transcripts, finder):
                    try:
                        t = getattr(transcripts, finder)(["en"])
                        return list(t.fetch())
                    except Exception:
                        pass

            # Fallback: try to find an item with language 'en' or 'English' in its repr
            for t in transcripts:
                try:
                    if getattr(t, 'language_code', None) == 'en' or 'English' in str(t):
                        try:
                            entries = list(t.fetch())
                            print(f"Instance transcript fetched: {len(entries)} entries from {t}")
                            return entries
                        except Exception:
                            pass
                except Exception:
                    continue

        # Last resort: instance fetch (returns a reasonable transcript if available)
        try:
            entries = api.fetch(video_id)
            entries = list(entries)
            print(f"api.fetch returned {len(entries)} entries")
            return entries
        except Exception as e:
            print(f"YouTube subtitle load failed: {e}")
            return None
    except Exception as e:
        print(f"YouTube transcript listing failed: {e}")
        return None


def _get_entry_value(entry, key, default=""):
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _create_segments_from_entries(entries):
    segments = []
    for entry in entries:
        text = str(_get_entry_value(entry, "text", "")).strip()
        if not text:
            continue
        start = float(_get_entry_value(entry, "start", 0.0) or 0.0)
        duration = float(_get_entry_value(entry, "duration", 0.0) or 0.0)
        end = start + duration if duration > 0 else start + 2.0
        segments.append({"text": text, "start": start, "end": end})
    return segments


def _create_segments_from_assemblyai(result):
    words = result.get("words") or []
    segments = []
    if words:
        current_words = []
        segment_start = None
        segment_end = None
        for word in words:
            text = str(word.get("text", "")).strip()
            if not text:
                continue
            if segment_start is None:
                segment_start = float(word.get("start", 0.0) or 0.0)
            segment_end = float(word.get("end", segment_start or 0.0) or 0.0)
            current_words.append(text)
            if len(current_words) >= 40:
                segments.append(
                    {
                        "text": " ".join(current_words).strip(),
                        "start": segment_start or 0.0,
                        "end": segment_end or (segment_start or 0.0) + 2.0,
                    }
                )
                current_words = []
                segment_start = None
                segment_end = None
        if current_words:
            segments.append(
                {
                    "text": " ".join(current_words).strip(),
                    "start": segment_start or 0.0,
                    "end": segment_end or (segment_start or 0.0) + 2.0,
                }
            )

    if not segments:
        transcript_text = str(result.get("text", "")).strip()
        if transcript_text:
            segments = [{"text": transcript_text, "start": 0.0, "end": max(2.0, len(transcript_text.split()) * 0.5)}]

    return segments


def ingest_transcript(transcript, video_id, segments):
    if not transcript:
        transcript = load_transcript()
    if not segments:
        segments = [{"text": transcript, "start": 0.0, "end": max(2.0, len(transcript.split()) * 0.5)}]

    chunks = chunk_transcript(transcript, segments)
    try:
        model_emb = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model_emb.encode([c['text'] for c in chunks])
    except Exception as e:
        print(f"Embeddings failed: {e}, using keyword fallback")
        embeddings = None

    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_or_create_collection(name="transcripts")
        try:
            collection.delete(where={"video_id": video_id})
        except Exception:
            pass

        ids = [f"{video_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "text": chunk['text'],
                "start_time": chunk['start'],
                "end_time": chunk['end'],
                "video_id": video_id
            }
            for chunk in chunks
        ]

        if embeddings is not None and len(embeddings) != len(ids):
            print(f"Embedding length {len(embeddings)} != chunks {len(ids)}, dropping embeddings")
            embeddings = None

        if embeddings is not None:
            collection.add(ids=ids, embeddings=[[float(value) for value in embedding] for embedding in embeddings], metadatas=metadatas)
        else:
            collection.add(ids=ids, metadatas=metadatas)
    except Exception as e:
        print(f"ChromaDB failed: {e}, storing in memory")
        store_chunks(video_id, [
            {
                "text": chunk['text'],
                "start_time": chunk['start'],
                "end_time": chunk['end'],
                "video_id": video_id
            }
            for chunk in chunks
        ])


def ingest_assemblyai_file(file_bytes: bytes, file_name: str, video_id: str):
    if not assemblyai_available():
        raise RuntimeError("AssemblyAI is not configured. Set ASSEMBLYAI_API_KEY in .env.")
    result = transcribe_uploaded_file(file_bytes, file_name)
    transcript = str(result.get("text", "")).strip()
    segments = _create_segments_from_assemblyai(result)
    ingest_transcript(transcript, video_id, segments)


def ingest_video(video_url, video_id):
    transcript = None
    segments = []
    if video_url and ("youtube.com" in video_url or "youtu.be" in video_url):
        entries = _load_youtube_transcript(video_url)
        if entries:
            segments = _create_segments_from_entries(entries)
            transcript = " ".join([seg["text"] for seg in segments])

    if not transcript:
        transcript = load_transcript()
        segments = [{"text": transcript, "start": 0.0, "end": len(transcript.split()) * 0.5}]

    ingest_transcript(transcript, video_id, segments)
