from .utils.env_loader import load_project_env
load_project_env()

from fastapi import FastAPI, HTTPException
from fastapi import UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
import json
from .ingest import ingest_video, ingest_assemblyai_file
from .rag import ask_question
from .summarizer import get_summary, get_topic_summaries, get_last_minutes_summary
from .session import get_session_history, add_to_session
from .utils.transcript_store import get_chunks

app = FastAPI(
    title="AI Learning Companion",
    description="RAG-based video learning assistant for LMS",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestRequest(BaseModel):
    video_url: str


class LocalUploadRequest(BaseModel):
    title: str | None = None

class AskRequest(BaseModel):
    video_id: str
    question: str
    session_id: str = None

@app.get("/")
def root():
    return {
        "message": "AI Learning Companion backend is running",
        "docs": "http://localhost:8000/docs",
        "features": [
            "Contextual Q&A from video transcripts",
            "Smart summaries (overall, topic-wise, last 5 minutes)",
            "Jump-to-moment navigation via timestamps",
            "Session memory for multi-turn conversations"
        ]
    }

@app.get("/ping")
def ping():
    return {"message": "working", "status": "ok"}

@app.post("/ingest")
def ingest(request: IngestRequest):
    try:
        video_id = str(uuid.uuid4())
        print(f"Ingest request received for video_url={request.video_url} assign video_id={video_id}")
        ingest_video(request.video_url, video_id)
        return {
            "video_id": video_id,
            "status": "success",
            "message": f"Video ingested successfully. Use video_id '{video_id}' for queries."
        }
    except Exception as e:
        print(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")


@app.post("/ingest-file")
async def ingest_file(file: UploadFile = File(...), title: str | None = Form(None)):
    try:
        video_id = str(uuid.uuid4())
        file_bytes = await file.read()
        print(f"File ingest request received for file={file.filename} assign video_id={video_id}")
        ingest_assemblyai_file(file_bytes, file.filename or title or "upload", video_id)
        return {
            "video_id": video_id,
            "status": "success",
            "message": f"File ingested successfully. Use video_id '{video_id}' for queries.",
        }
    except Exception as e:
        print(f"File ingest failed: {e}")
        raise HTTPException(status_code=500, detail=f"File ingest failed: {str(e)}")

@app.post("/ask")
def ask(request: AskRequest):
    try:
        print(f"Ask request received for video_id={request.video_id} question={request.question}")
        history = get_session_history(request.session_id) if request.session_id else []
        answer, timestamps = ask_question(request.video_id, request.question, history)
        if request.session_id:
            add_to_session(request.session_id, request.question, answer)
        return {
            "answer": answer,
            "timestamps": timestamps,
            "session_id": request.session_id or str(uuid.uuid4()),
            "status": "success"
        }
    except Exception as e:
        print(f"Ask failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ask failed: {str(e)}")

@app.post("/ask/stream")
def ask_stream(request: AskRequest):
    try:
        print(f"Stream ask request for video_id={request.video_id}")
        history = get_session_history(request.session_id) if request.session_id else []
        answer, timestamps = ask_question(request.video_id, request.question, history)
        
        def generate():
            for char in answer:
                yield json.dumps({"chunk": char}) + "\n"
            yield json.dumps({"timestamps": timestamps, "done": True}) + "\n"
        
        if request.session_id:
            add_to_session(request.session_id, request.question, answer)
        
        return StreamingResponse(generate(), media_type="application/x-ndjson")
    except Exception as e:
        print(f"Stream ask failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stream ask failed: {str(e)}")

@app.get("/summary/{video_id}")
def summary(video_id: str):
    try:
        summary_text = get_summary(video_id)
        return {
            "video_id": video_id,
            "summary": summary_text,
            "type": "overall",
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/topic-summaries/{video_id}")
def topic_summaries(video_id: str):
    try:
        topics = get_topic_summaries(video_id)
        if not topics:
            return {
                "video_id": video_id,
                "topics": [],
                "status": "no_data",
                "message": "No topics found. Please ingest a video first."
            }
        return {
            "video_id": video_id,
            "topics": topics,
            "count": len(topics),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/last-minutes/{video_id}")
def last_minutes(video_id: str, minutes: int = 5):
    try:
        if minutes < 1 or minutes > 60:
            raise ValueError("Minutes must be between 1 and 60")
        result = get_last_minutes_summary(video_id, minutes)
        return {
            "video_id": video_id,
            "minutes": minutes,
            "summary": result.get("summary"),
            "timestamp": result.get("timestamp"),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/timestamps/{video_id}")
def timestamps(video_id: str):
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get(where={"video_id": video_id})
        if not results['ids']:
            raise Exception("No timestamps found")
        ts = [
            {
                "time": int(metadata.get('start_time', 0)),
                "label": f"Chunk {i + 1}",
                "duration": int(metadata.get('end_time', 0) - metadata.get('start_time', 0))
            }
            for i, metadata in enumerate(results['metadatas'])
        ]
        return {
            "video_id": video_id,
            "timestamps": ts,
            "count": len(ts),
            "status": "success"
        }
    except Exception as e:
        print(f"Timestamps failed: {e}")
        fs = get_chunks(video_id)
        if fs:
            return {
                "video_id": video_id,
                "timestamps": [{"time": int(c.get('start_time', 0)), "label": f"Chunk {i + 1}"} for i, c in enumerate(fs)],
                "count": len(fs),
                "status": "fallback"
            }
        return {
            "video_id": video_id,
            "timestamps": [{"time": 0, "label": "Start"}],
            "status": "no_data"
        }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AI Learning Companion Backend",
        "version": "1.0.0"
    }
