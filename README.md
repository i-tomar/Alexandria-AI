# AI Learning Companion

AI Learning Companion is a FastAPI-based video learning assistant that lets users ingest a YouTube lecture, ask grounded questions about it, and jump to exact timestamps. It uses local transcript processing and embeddings by default, with optional Gemini 1.5 Flash responses when `GOOGLE_API_KEY` is configured.

## What’s Included

- YouTube transcript ingestion with automatic caption selection and translation fallback
- Local file upload ingestion through AssemblyAI
- Chunked transcript storage in ChromaDB with timestamp metadata
- Q&A with timestamps for jump-to-moment navigation
- Overall, topic-wise, and last-N-minutes summaries
- Session support for multi-turn Q&A
- Optional Gemini 1.5 Flash generation for more natural answers and summaries

## Stack

- Backend: FastAPI
- Vector store: ChromaDB
- Embeddings: `sentence-transformers` with `all-MiniLM-L6-v2`
- Transcript source: `youtube-transcript-api` and AssemblyAI
- Optional generation: Gemini 1.5 Flash via `google-generativeai`

## Backend Structure

- `backend/main.py`: API routes and app setup
- `backend/ingest.py`: transcript loading, chunking, and storage
- `backend/rag.py`: retrieval and grounded answer generation
- `backend/summarizer.py`: overall and timed summaries
- `backend/utils/`: chunking, similarity, Gemini client, and transcript storage helpers

## Environment

Create a `.env` file in the project root with:

```env
GOOGLE_API_KEY=your_google_api_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
```

`GOOGLE_API_KEY` is optional. If it is not present, the backend keeps working with the local fallback pipeline.

## Run the Backend

```powershell
cd z:\AI-Learning-Companion
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open the docs at `http://127.0.0.1:8000/docs`.

## Core API

- `GET /` - service overview
- `GET /ping` - health check
- `POST /ingest` - ingest a YouTube URL
- `POST /ingest-file` - upload a local audio/video file for transcription
- `POST /ask` - ask a question about the ingested video
- `POST /ask/stream` - streaming answer endpoint
- `GET /summary/{video_id}` - overall summary
- `GET /topic-summaries/{video_id}` - topic summaries
- `GET /last-minutes/{video_id}?minutes=5` - time-based summary
- `GET /timestamps/{video_id}` - chunk timestamps for the UI

Example ingest request:

```json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

Example ask request:

```json
{
  "video_id": "your-video-id",
  "question": "What is the main topic?",
  "session_id": "optional-session-id"
}
```

## Frontend Next Step

The frontend should call the FastAPI endpoints above, render the answer plus timestamps, and use those timestamps to seek the video player. See [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) for the request flow and UI recommendations.

## Removed Legacy Code

The old Express/Node MVP files and temporary debugging scripts were removed so the repository now centers on the active FastAPI + Gemini stack.

Response:

```json
{
  "summary": "Short lecture summary appears here..."
}
```

## Future Improvements

- Add persistent storage for multiple videos
- Return timestamps with answers
- Improve scoring with TF-IDF or embeddings
- Add real LLM-based summaries when free credits or local models are available
- Add user sessions
- Add upload support for `.txt` transcript files
- Add CORS configuration for production frontend deployment
- Add tests for transcript fetching, chunking, Q&A, and summaries
- Add better language support for non-English captions

## Demo Guide for Judges

1. Start the backend:

```powershell
cd backend
npm install
npm start
```

2. Open the React frontend.

3. Paste a YouTube lecture URL.

4. Click the load button.

5. If captions are available, the app will show that the transcript is loaded.

6. If captions are unavailable, paste a short transcript manually and load again.

7. Ask a question such as:

```text
What is the main idea of this lecture?
```

8. Review the answer returned from the transcript.

9. Click the summary button to see a short lecture summary.

Recommended demo flow:

- Show automatic caption loading first.
- Ask one specific question from the lecture.
- Show the summary.
- Then show the manual transcript fallback to prove the app still works when YouTube captions are unavailable.

## Notes

This project is optimized for a hackathon MVP. The backend currently stores one loaded transcript in memory, so restarting the server clears the loaded video. This keeps the implementation simple and free while leaving a clear path for future upgrades.

// # RAG in oour project 


YouTube Video
       ↓
Transcript Extraction
       ↓
Transcript Chunking
       ↓
Store Chunks in Memory
       ↓
User Question
       ↓
Keyword Matching / Retrieval
       ↓
Find Best Chunk
       ↓
Return Answer
