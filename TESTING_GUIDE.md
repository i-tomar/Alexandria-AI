# Basic Video Testing Guide - Step by Step

Simple instructions to test the AI Learning Companion backend with any YouTube video.

---

## 🎬 Prerequisites

- Backend running: `python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000`
- A public YouTube video URL (must have captions/subtitles enabled)
- PowerShell terminal

---

## 📺 Example Videos to Test With

Use any of these (they have public captions):
- https://www.youtube.com/watch?v=kJQP7kiw5Fk (Despacito - music with captions)
- https://www.youtube.com/watch?v=dQw4w9WgXcQ (Rick Roll - music with captions)
- https://www.youtube.com/watch?v=jNQXAC9IVRw (Me at the zoo - first YouTube video)

---

## 🚀 Step 1: Start the Backend Server

Open PowerShell and run:

```powershell
cd z:\AI-Learning-Companion
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

✅ Backend is now running and ready to accept requests!

---

## 🧪 Step 2: Test Health Check

Open a **NEW PowerShell window** (keep the first one running) and test:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ping"
```

**Expected Output:**
```
message status
------- ------
working ok
```

✅ Backend is responsive!

---

## 📥 Step 3: Ingest a Video (Upload/Process)

This tells the backend to download captions from a YouTube video and prepare it for Q&A.

```powershell
$videoUrl = "https://www.youtube.com/watch?v=kJQP7kiw5Fk"

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/ingest" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body "{`"video_url`":`"$videoUrl`"}"

$videoId = $response.video_id
Write-Host "Video ID: $videoId"
Write-Host "Status: $($response.status)"
Write-Host "Message: $($response.message)"
```

**Expected Output:**
```
Video ID: 550e8400-e29b-41d4-a716-446655440000
Status: success
Message: Video ingested successfully. Use video_id '550e8400-e29b-41d4-a716-446655440000' for queries.
```

💾 **Save the video_id!** You'll use it for all next steps.

✅ Video is now ingested and ready for Q&A!

---

## ❓ Step 4: Ask a Question

Ask the backend about the video content:

```powershell
$videoId = "550e8400-e29b-41d4-a716-446655440000"  # From Step 3
$question = "What is being discussed?"

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body "{`"video_id`":`"$videoId`",`"question`":`"$question`"}"

Write-Host "Answer: $($response.answer)"
Write-Host "Timestamps: $($response.timestamps)"
```

**Expected Output:**
```
Answer: The content discusses music, rhythm, and lyrics about love and dancing...
Timestamps: 60 85
```

📍 The timestamps tell you WHERE in the video the answer is found!
- Start at 60 seconds
- End at 85 seconds

✅ You got an intelligent answer with exact video location!

---

## 📋 Step 5: Get Overall Summary

Get a summary of the entire video:

```powershell
$videoId = "550e8400-e29b-41d4-a716-446655440000"

$response = Invoke-RestMethod -Uri "http://localhost:8000/summary/$videoId"

Write-Host "Summary:"
Write-Host $response.summary
```

**Expected Output:**
```
Summary:
This video is about a song that discusses various themes of music, rhythm, and dancing...
```

✅ Quick overview of the entire video!

---

## 🎯 Step 6: Get Topic Summaries

Get 5 key topics with their summaries and timestamps:

```powershell
$videoId = "550e8400-e29b-41d4-a716-446655440000"

$response = Invoke-RestMethod -Uri "http://localhost:8000/topic-summaries/$videoId"

Write-Host "Found $($response.count) topics:`n"

foreach ($topic in $response.topics) {
    Write-Host "Topic: $($topic.topic)"
    Write-Host "Summary: $($topic.summary)"
    Write-Host "Timestamp: $($topic.timestamp)s"
    Write-Host "---"
}
```

**Expected Output:**
```
Found 5 topics:

Topic: Yeah, you know that I've been looking at you for a long time
Summary: Come, try my mouth and see if you like its taste...
Timestamp: 45.2s
---
Topic: Dancing and moving
Summary: Details about dancing and rhythm...
Timestamp: 120.5s
---
```

✅ Key topics with navigation points!

---

## ⏱️ Step 7: Get Last N Minutes Summary

Get a summary of just the last 5 minutes:

```powershell
$videoId = "550e8400-e29b-41d4-a716-446655440000"
$minutes = 5

$response = Invoke-RestMethod -Uri "http://localhost:8000/last-minutes/$videoId`?minutes=$minutes"

Write-Host "Summary of last $($response.minutes) minutes:"
Write-Host $response.summary
Write-Host "Starting at: $($response.timestamp)s"
```

**Expected Output:**
```
Summary of last 5 minutes:
The final part of the video emphasizes the main message...
Starting at: 285.7s
```

✅ Focused summary of a time period!

---

## 📍 Step 8: Get All Timestamps (Timeline)

Get every chunk with its timestamp for building a clickable timeline:

```powershell
$videoId = "550e8400-e29b-41d4-a716-446655440000"

$response = Invoke-RestMethod -Uri "http://localhost:8000/timestamps/$videoId"

Write-Host "Total chunks: $($response.count)`n"

foreach ($ts in $response.timestamps) {
    $time = $ts.time
    $mins = [Math]::Floor($time / 60)
    $secs = [Math]::Floor($time % 60)
    Write-Host "$($ts.label): ${mins}:$($secs.ToString('00'))"
}
```

**Expected Output:**
```
Total chunks: 12

Chunk 1: 0:00
Chunk 2: 0:20
Chunk 3: 0:45
Chunk 4: 1:10
...
```

✅ Complete timeline ready to display in a player!

---

## 🎥 Step 9: Jump to a Timestamp (in Video Player)

When you get timestamps back from any API call, you can jump to that point:

```javascript
// In your video player (e.g., YouTube embed, HTML5 video):
// Jump to 60 seconds (from the timestamps in Step 4)
player.seek(60);

// Or in YouTube embedded player:
// (timestamps are ready for direct use with video.currentTime = 60)
```

✅ Exact navigation in video!

---

## 🔄 Complete Test Workflow (All Steps Together)

Here's a full PowerShell script that does everything:

```powershell
# Configuration
$videoUrl = "https://www.youtube.com/watch?v=kJQP7kiw5Fk"
$question = "What is the main topic?"
$backendUrl = "http://127.0.0.1:8000"

# Step 1: Ingest
Write-Host "[1] Ingesting video..." -ForegroundColor Cyan
$ingestResponse = Invoke-RestMethod -Uri "$backendUrl/ingest" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body "{`"video_url`":`"$videoUrl`"}"

$videoId = $ingestResponse.video_id
Write-Host "[OK] Video ID: $videoId`n" -ForegroundColor Green

# Step 2: Ask Question
Write-Host "[2] Asking question..." -ForegroundColor Cyan
$askResponse = Invoke-RestMethod -Uri "$backendUrl/ask" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body "{`"video_id`":`"$videoId`",`"question`":`"$question`"}"

Write-Host "[OK] Answer: $($askResponse.answer.Substring(0, 100))..." -ForegroundColor Green
Write-Host "[OK] Jump to: $($askResponse.timestamps[0])s - $($askResponse.timestamps[1])s`n" -ForegroundColor Green

# Step 3: Get Summary
Write-Host "[3] Getting overall summary..." -ForegroundColor Cyan
$summaryResponse = Invoke-RestMethod -Uri "$backendUrl/summary/$videoId"
Write-Host "[OK] $($summaryResponse.summary.Substring(0, 100))...`n" -ForegroundColor Green

# Step 4: Get Topic Summaries
Write-Host "[4] Getting topic summaries..." -ForegroundColor Cyan
$topicsResponse = Invoke-RestMethod -Uri "$backendUrl/topic-summaries/$videoId"
Write-Host "[OK] Found $($topicsResponse.count) topics`n" -ForegroundColor Green

# Step 5: Get Timestamps
Write-Host "[5] Getting timeline..." -ForegroundColor Cyan
$timestampsResponse = Invoke-RestMethod -Uri "$backendUrl/timestamps/$videoId"
Write-Host "[OK] Timeline has $($timestampsResponse.count) chunks`n" -ForegroundColor Green

Write-Host "============================================" -ForegroundColor Yellow
Write-Host "All tests completed successfully!" -ForegroundColor Green
Write-Host "Video ID for future queries: $videoId" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow
```

Copy this entire script, save it as `test-backend.ps1`, and run:

```powershell
.\test-backend.ps1
```

---

## 🆘 Troubleshooting

### Problem: "Connection refused"
- **Solution**: Make sure backend is running (Step 1)
- Check: http://127.0.0.1:8000/ping

### Problem: "No transcripts available"
- **Solution**: YouTube video doesn't have public captions
- Try: One of the example videos from the list above
- Or: Enable captions on your YouTube video first

### Problem: Empty answers
- **Solution**: Video transcript is very short
- Try: A longer video (5+ minutes)

### Problem: "SyntaxError" in PowerShell
- **Solution**: Copy the exact code with backticks
- Don't change `"` to `'` for JSON

---

## ✅ Success Checklist

- [ ] Backend running and /ping returns "working"
- [ ] Video ingested and got a video_id
- [ ] Asked a question and got an answer with timestamps
- [ ] Got overall summary
- [ ] Got topic summaries with 5 topics
- [ ] Got last 5 minutes summary
- [ ] Got full timeline with 10+ chunks

If all checked, your backend is **working perfectly**! 🎉

---

## 📝 Notes

- Each API call returns a status field: `"success"` or `"no_data"`
- Timestamps are in **seconds** (float/integer)
- Video ID is unique per ingestion
- You can ask multiple questions for the same video_id
- Try different questions to test accuracy!

---

## 🎯 Next Steps

1. **Test with YOUR video**: Replace the URL and try
2. **Try different questions**: Ask various things
3. **Read the responses**: Check if they're accurate
4. **Note timestamps**: Verify they point to the right place
5. **Build your frontend**: Use this API with a video player

**You're all set!** Start testing! 🚀

---

## 🧠 AI Learning Companion: Master Project Blueprint

Use this as the project-level reference when extending or rebuilding the system.

**Goal**: A RAG-based video learning assistant that lets users chat with lectures, get smart summaries, and jump to exact timestamps from questions.

**Stack**:
- Backend: FastAPI (Python)
- Vector store: ChromaDB
- Embeddings: `sentence-transformers` with `all-MiniLM-L6-v2`
- Generative model: Gemini 1.5 Flash
- Transcription: `youtube-transcript-api` for YouTube and AssemblyAI for local file uploads
- Frontend: React or Next.js with Video.js

**Architecture**:
1. Ingest transcripts from YouTube or local files.
2. Split transcript into timestamped chunks with overlap.
3. Embed chunks and store them in ChromaDB with metadata.
4. Retrieve the top matching chunks for Q&A.
5. Ground responses strictly in the retrieved context and return timestamps.
6. Generate overall summaries, topic summaries, and last-N-minutes summaries.

**Operating rules for AI assistants**:
- Keep logic modular across `ingest`, `rag`, `summarizer`, and route files.
- Always return timestamps for navigation in the video player.
- Prefer local embedding models to keep latency and cost low.
- Use `.env` for API keys, including `GOOGLE_API_KEY` and `ASSEMBLYAI_API_KEY`.
- Handle transcript failures, translation issues, and missing captions gracefully.
- Keep answers grounded in transcript context; do not invent video content.

**Backend references**:
- `backend/main.py`: API entry point and routes
- `backend/ingest.py`: transcript loading and storage
- `backend/rag.py`: retrieval and grounded answer generation
- `backend/summarizer.py`: summary generation
- `backend/data/`: static transcript assets and fixtures

**Standard setup**:
1. Create `.env` with `GOOGLE_API_KEY` and `ASSEMBLYAI_API_KEY`.
2. Install dependencies with `pip install -r backend/requirements.txt`.
3. Run the server with `uvicorn backend.main:app --reload`.
4. POST to `/ingest` with `video_url`.
5. POST to `/ask` with `video_id` and `question`.
6. POST to `/ingest-file` with a local audio or video file to use AssemblyAI transcription.
