# AI Learning Companion

AI Learning Companion is a FastAPI-based learning assistant that turns a YouTube video or uploaded file into a grounded study companion. It can ingest transcripts, answer questions with timestamps, generate summaries, and support multi-turn conversations.

## What It Does

- Ingests YouTube links and uses transcript extraction with translation fallback when captions are available
- Accepts uploaded audio/video files and transcribes them through AssemblyAI
- Chunks transcripts and stores them in ChromaDB with timestamp metadata
- Answers questions using transcript context and returns jump-to-moment timestamps
- Generates overall summaries, topic summaries, and last-N-minutes summaries
- Supports session IDs for continuing a conversation across multiple questions
- Uses Gemini 1.5 Flash when `GOOGLE_API_KEY` is configured, with safe local fallbacks if it is not

## Tech Stack

- Backend: FastAPI
- Vector store: ChromaDB
- Embeddings: `sentence-transformers` with `all-MiniLM-L6-v2`
- YouTube transcript source: `youtube-transcript-api`
- File transcription: AssemblyAI
- Optional generation: Gemini 1.5 Flash via `google-generativeai`
- API docs: Swagger UI at `/docs`

## Project Structure

- `backend/main.py`: FastAPI app, routes, CORS, and request handling
- `backend/ingest.py`: YouTube transcript loading, AssemblyAI file transcription, chunk creation, and storage
- `backend/rag.py`: retrieval logic and grounded question answering
- `backend/summarizer.py`: overall, topic-wise, and last-minutes summaries
- `backend/session.py`: simple session memory for multi-turn Q&A
- `backend/utils/`: chunking, similarity scoring, transcript storage, Gemini client, AssemblyAI client, and env loading helpers
- `chroma_db/`: persistent transcript vector store

## Requirements

Create a `.env` file in the project root with your API keys:

```env
GOOGLE_API_KEY=your_google_api_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
```

`GOOGLE_API_KEY` is optional. If it is missing, the backend still runs and uses the local retrieval fallback for answers and summaries.

`ASSEMBLYAI_API_KEY` is required for file upload transcription through `/ingest-file`.

## Install And Run

From the project root:

```powershell
cd z:\AI-Learning-Companion
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open the API docs in your browser:

```text
http://127.0.0.1:8000/docs
```

## Quick Health Check

Verify the backend is running:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ping"
```

Expected response:

```json
{
  "message": "working",
  "status": "ok"
}
```

## How To Use It

### 1. Ingest a YouTube video

Send a YouTube URL to `/ingest`.

```powershell
$body = @{
  video_url = "https://www.youtube.com/watch?v=VIDEO_ID"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/ingest" -Method Post -ContentType "application/json" -Body $body
$response | ConvertTo-Json -Depth 4

$videoId = $response.video_id
```

The response returns a `video_id`. Save it because every later question and summary uses that ID.

Example response:

```json
{
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "message": "Video ingested successfully. Use video_id '550e8400-e29b-41d4-a716-446655440000' for queries."
}
```

### 2. Ask a question

Use `/ask` with the returned `video_id`.

```powershell
$body = @{
  video_id = "550e8400-e29b-41d4-a716-446655440000"
  question = "What is the main topic?"
  session_id = "mentor-demo-session"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post -ContentType "application/json" -Body $body
```

The response includes:

- `answer`: grounded response from the transcript
- `timestamps`: best matching start/end timestamps in seconds
- `session_id`: returned or reused session identifier

### 3. Read summaries

Use these endpoints after ingesting a video:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/summary/$videoId"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/topic-summaries/$videoId"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/last-minutes/$videoId?minutes=5"
```

### 4. Build a clickable timeline

Fetch timestamps for each chunk:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/timestamps/$videoId"
```

Each chunk includes a start time and duration, which you can use to seek a video player.

### 5. Upload a local file

Upload an audio or video file to `/ingest-file`.

```powershell
curl.exe -s -X POST `
  -F "file=@Z:\AI-Learning-Companion\sample.wav" `
  -F "title=sample upload" `
  http://127.0.0.1:8000/ingest-file
```

Replace `sample.wav` with any local audio or video file you want to upload.

This path uses AssemblyAI, so make sure `ASSEMBLYAI_API_KEY` is present in `.env`.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | API overview |
| `GET` | `/ping` | Health check |
| `GET` | `/health` | Detailed health response |
| `POST` | `/ingest` | Ingest a YouTube URL |
| `POST` | `/ingest-file` | Upload a local audio/video file for transcription |
| `POST` | `/ask` | Ask a grounded question |
| `POST` | `/ask/stream` | Stream an answer as NDJSON chunks |
| `GET` | `/summary/{video_id}` | Overall summary |
| `GET` | `/topic-summaries/{video_id}` | Topic-wise summaries |
| `GET` | `/last-minutes/{video_id}?minutes=5` | Summary for the last N minutes |
| `GET` | `/timestamps/{video_id}` | Timeline data for UI seeking |

## Response Shapes

### Ingest

```json
{
  "video_id": "uuid-string",
  "status": "success",
  "message": "Video ingested successfully. Use video_id 'uuid-string' for queries."
}
```

### Ask

```json
{
  "answer": "Grounded answer from the transcript.",
  "timestamps": [100, 125],
  "session_id": "mentor-demo-session",
  "status": "success"
}
```

### Summary

```json
{
  "video_id": "uuid-string",
  "summary": "Short lecture summary goes here.",
  "type": "overall",
  "status": "success"
}
```

## Recommended Demo Flow For The Mentor

1. Start the backend.
2. Open `http://127.0.0.1:8000/docs` to show the live API.
3. Ingest a YouTube video.
4. Ask one specific question from the lecture.
5. Show the timestamps and explain that they can drive video seeking.
6. Open the summary endpoints to show the overall and topic summaries.
7. Upload a file to `/ingest-file` to show the AssemblyAI fallback.
8. If `GOOGLE_API_KEY` is configured, show that answers and summaries become more natural while staying grounded in the transcript.

## Frontend Integration

The frontend should call these endpoints directly and use the returned timestamps to jump in the player. The file [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) contains example request flows and UI recommendations for the next stage.

## Notes

- Answers stay grounded in the ingested transcript context.
- Session support allows the mentor to ask follow-up questions without reloading the video each time.
- If Gemini is not configured, the app still works with local retrieval and fallback summaries.
- If file transcription fails, the first thing to check is `ASSEMBLYAI_API_KEY` in `.env`.

## Troubleshooting

- If `/ingest-file` returns an AssemblyAI configuration error, add `ASSEMBLYAI_API_KEY` and restart the backend.
- If `/ask` says no data was found, make sure you copied the `video_id` from `/ingest` correctly.
- If transcript ingestion looks weak for a YouTube video, try a different public video with captions enabled.
- If the backend will not start, check the terminal running Uvicorn for import or dependency errors.

## What Changed In This Version

- Replaced the old Node/Express demo instructions with the actual FastAPI startup flow
- Added the live YouTube transcript pipeline with translation fallback
- Added AssemblyAI file upload transcription
- Added Gemini-backed grounded Q&A and summaries as an optional enhancement
- Added timestamps, streaming answers, and session support
- Added a mentor-focused demo workflow and troubleshooting notes
