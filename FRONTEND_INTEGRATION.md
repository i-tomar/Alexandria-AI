# Frontend Integration Guide

How to build a frontend for the AI Learning Companion backend.

## Backend Setup

Start the backend before running the frontend:

```powershell
cd z:\AI-Learning-Companion
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open the live API docs:

```text
http://127.0.0.1:8000/docs
```

## Building the Frontend

The frontend is a client-side app that calls the FastAPI backend. You can use React, Vue, plain JavaScript, or any frontend framework.

### Recommended Architecture

```
┌─────────────────┐
│   Browser/App   │
└────────┬────────┘
         │
    HTTP Fetch
         │
┌────────▼────────────┐
│  FastAPI Backend    │
│  (localhost:8000)   │
└─────────────────────┘
```

All communication happens via HTTP requests. No authentication is required for the MVP.

## Core Implementation Flow

### 1. Ingest a Video

User pastes a YouTube URL and clicks "Load Video".

```javascript
async function ingestVideo(videoUrl) {
  const response = await fetch('http://127.0.0.1:8000/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_url: videoUrl })
  });
  const result = await response.json();
  if (response.ok) {
    return result.video_id;  // Save this for all future calls
  } else {
    throw new Error(result.detail);
  }
}
```

### 2. Ask a Question

User types a question and clicks "Ask".

```javascript
async function askQuestion(videoId, question, sessionId) {
  const response = await fetch('http://127.0.0.1:8000/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_id: videoId,
      question: question,
      session_id: sessionId
    })
  });
  const result = await response.json();
  if (response.ok) {
    return {
      answer: result.answer,
      timestamps: result.timestamps,  // [start_seconds, end_seconds]
      sessionId: result.session_id
    };
  } else {
    throw new Error(result.detail);
  }
}
```

### 3. Display Answer with Timestamps

Jump the video player to the returned timestamp.

```javascript
function displayAnswer(answer, timestamps) {
  // Show the answer text
  document.getElementById('answer-box').textContent = answer;
  
  // Jump video player to the start timestamp
  if (timestamps && timestamps.length > 0) {
    const startTime = timestamps[0];
    jumpVideoPlayerTo(startTime);
  }
}

function jumpVideoPlayerTo(seconds) {
  // For HTML5 video:
  document.querySelector('video').currentTime = seconds;
  
  // For YouTube embedded player, use the YouTube Player API
  // ytPlayer.seekTo(seconds, true);
}
```

### 4. Display Summaries

Get and display all summary types after ingesting a video.

```javascript
// Stream the response character by character
const streamResponse = await fetch('http://localhost:8000/ask/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_id,
    question: 'Explain the concept',
    session_id: 'session-123'
  })
});

const reader = streamResponse.body.getReader();
const decoder = new TextDecoder();
let fullAnswer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const line = decoder.decode(value);
  const json = JSON.parse(line);
  
  if (json.chunk) {
    fullAnswer += json.chunk;
    updateUIWithChunk(json.chunk); // Real-time display
  }
  if (json.done) {
    console.log('Timestamps:', json.timestamps);
  }
}
```

### Workflow 3: Display All Summary Types

```javascript
async function displaySummaries(videoId) {
  // Overall summary
  const summaryRes = await fetch(`http://127.0.0.1:8000/summary/${videoId}`);
  const summaryData = await summaryRes.json();
  document.getElementById('overall-summary').textContent = summaryData.summary;
  
  // Topic summaries
  const topicsRes = await fetch(`http://127.0.0.1:8000/topic-summaries/${videoId}`);
  const topicsData = await topicsRes.json();
  
  const topicsList = document.getElementById('topics-list');
  topicsList.innerHTML = '';
  topicsData.topics.forEach(topic => {
    const div = document.createElement('div');
    div.innerHTML = `<strong>${topic.topic}</strong><br>${topic.summary}<br><small>@ ${topic.timestamp}s</small>`;
    div.onclick = () => jumpVideoPlayerTo(topic.timestamp);
    topicsList.appendChild(div);
  });
  
  // Last N minutes
  const lastRes = await fetch(`http://127.0.0.1:8000/last-minutes/${videoId}?minutes=5`);
  const lastData = await lastRes.json();
  document.getElementById('last-summary').textContent = lastData.summary;
}
```

### 5. Build a Timeline

Create clickable chunk buttons for navigation.

```javascript
async function buildTimeline(videoId) {
  const response = await fetch(`http://127.0.0.1:8000/timestamps/${videoId}`);
  const data = await response.json();
  
  const timeline = document.getElementById('timeline');
  timeline.innerHTML = '';
  
  data.timestamps.forEach(chunk => {
    const button = document.createElement('button');
    button.textContent = `${chunk.label} (${formatTime(chunk.time)})`;
    button.onclick = () => jumpVideoPlayerTo(chunk.time);
    timeline.appendChild(button);
  });
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
```

## Optional: Streaming Answers

For real-time text streaming (progressive display):

```javascript
async function askQuestionStreaming(videoId, question, sessionId) {
  const response = await fetch('http://127.0.0.1:8000/ask/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_id: videoId,
      question: question,
      session_id: sessionId
    })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const answerBox = document.getElementById('answer-box');
  answerBox.textContent = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n').filter(l => l.trim());
    
    for (const line of lines) {
      try {
        const json = JSON.parse(line);
        if (json.chunk) {
          answerBox.textContent += json.chunk;
        }
        if (json.timestamps) {
          jumpVideoPlayerTo(json.timestamps[0]);
        }
      } catch (e) {
        // ignore parse errors
      }
    }
  }
}
```

## Error Handling

```javascript
async function safeFetch(endpoint, options) {
  try {
    const response = await fetch(`http://127.0.0.1:8000${endpoint}`, options);
    if (!response.ok) {
      const error = await response.json();
      console.error('API Error:', error.detail);
      return null;
    }
    return await response.json();
  } catch (err) {
    console.error('Network error:', err.message);
    return null;
  }
}
```

## Session Management

Keep sessions alive for multi-turn conversations:

```javascript
let currentSessionId = `session_${Date.now()}`;

async function askFollowUp(videoId, question) {
  const response = await fetch('http://127.0.0.1:8000/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_id: videoId,
      question: question,
      session_id: currentSessionId
    })
  });
  const result = await response.json();
  currentSessionId = result.session_id;  // Keep it updated
  return result;
}
```

## Example HTML Layout

```html
<!DOCTYPE html>
<html>
<head>
  <title>AI Learning Companion</title>
  <style>
    body { font-family: Arial; margin: 20px; }
    #video-container { width: 100%; max-width: 800px; margin-bottom: 20px; }
    #ingest-section, #ask-section, #summaries-section { margin: 20px 0; border: 1px solid #ccc; padding: 15px; }
    #answer-box { background: #f0f0f0; padding: 10px; border-radius: 5px; min-height: 50px; }
    #timeline { display: flex; flex-wrap: wrap; gap: 5px; }
    #timeline button { padding: 5px 10px; cursor: pointer; }
    #timeline button:hover { background: #ddd; }
  </style>
</head>
<body>
  <h1>AI Learning Companion</h1>
  
  <div id="video-container">
    <iframe width="100%" height="400" 
      src="https://www.youtube.com/embed/VIDEO_ID" 
      frameborder="0" allowfullscreen>
    </iframe>
  </div>
  
  <div id="ingest-section">
    <h2>1. Load Video</h2>
    <input id="video-url" type="text" placeholder="Paste YouTube URL here">
    <button onclick="loadVideo()">Load</button>
    <p id="status"></p>
  </div>
  
  <div id="ask-section">
    <h2>2. Ask a Question</h2>
    <input id="question" type="text" placeholder="Ask something about the video">
    <button onclick="askNow()">Ask</button>
    <div id="answer-box"></div>
    <div id="timestamps" style="margin-top: 10px; font-size: 12px; color: #666;"></div>
  </div>
  
  <div id="summaries-section">
    <h2>3. Video Summaries</h2>
    <div id="overall-summary"></div>
    <h3>Topics</h3>
    <div id="topics-list"></div>
    <h3>Last 5 Minutes</h3>
    <div id="last-summary"></div>
  </div>
  
  <div>
    <h2>Timeline Navigation</h2>
    <div id="timeline"></div>
  </div>
  
  <script src="app.js"></script>
</body>
</html>
```

## Frontend Integration Notes

- **Video Player**: Use HTML5 video or YouTube embed; both support `currentTime` seeking
- **Timestamps**: All timestamps from the API are in **seconds** as floats
- **Session ID**: Generate once per page load and reuse for all questions
- **CORS**: Backend allows all origins—no additional configuration needed
- **Streaming**: The `/ask/stream` endpoint returns NDJSON (one JSON object per line)
- **Cache**: Consider caching summaries locally to reduce API calls

## Production Deployment

For production, update in `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Also add authentication, rate limiting, and HTTPS before going live.

## Testing The Integration

1. Start the backend on `http://127.0.0.1:8000`.
2. Open `http://127.0.0.1:8000/docs` to test endpoints manually.
3. Ingest a test YouTube video and verify `video_id` is returned.
4. Ask a test question and verify `answer` and `timestamps` are returned.
5. Verify timestamps drive the video player seek correctly.

## Reference: All API Responses

**POST /ingest**
```json
{
  "video_id": "uuid",
  "status": "success",
  "message": "Video ingested successfully..."
}
```

**POST /ask**
```json
{
  "answer": "The answer to your question...",
  "timestamps": [100.0, 125.0],
  "session_id": "session_123",
  "status": "success"
}
```

**GET /summary/{video_id}**
```json
{
  "video_id": "uuid",
  "summary": "Overall summary...",
  "type": "overall",
  "status": "success"
}
```

**GET /topic-summaries/{video_id}**
```json
{
  "video_id": "uuid",
  "topics": [
    { "topic": "Topic title", "summary": "...", "timestamp": 45.0 }
  ],
  "count": 1,
  "status": "success"
}
```

**GET /timestamps/{video_id}**
```json
{
  "video_id": "uuid",
  "timestamps": [
    { "time": 0, "label": "Chunk 1", "duration": 25 }
  ],
  "count": 1,
  "status": "success"
}
```

---

Ready to build! Backend is running on `http://127.0.0.1:8000/docs` for live testing.

