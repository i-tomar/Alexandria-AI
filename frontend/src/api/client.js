const API_BASE = 'http://127.0.0.1:8000';

export async function ingestVideo(videoUrl) {
  const response = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_url: videoUrl })
  });
  const result = await response.json();
  if (response.ok) {
    return result.video_id;
  } else {
    throw new Error(result.detail || result.message || 'Failed to ingest video');
  }
}

export async function getOverallSummary(videoId) {
  const response = await fetch(`${API_BASE}/summary/${videoId}`);
  if (!response.ok) throw new Error('Failed to get summary');
  return await response.json();
}

export async function getTopicSummaries(videoId) {
  const response = await fetch(`${API_BASE}/topic-summaries/${videoId}`);
  if (!response.ok) throw new Error('Failed to get topic summaries');
  return await response.json();
}

export async function getLastMinutesSummary(videoId, minutes = 5) {
  const response = await fetch(`${API_BASE}/last-minutes/${videoId}?minutes=${minutes}`);
  if (!response.ok) throw new Error('Failed to get recent summary');
  return await response.json();
}

export async function getTimestamps(videoId) {
  const response = await fetch(`${API_BASE}/timestamps/${videoId}`);
  if (!response.ok) throw new Error('Failed to get timestamps');
  return await response.json();
}

// Helper to handle the NDJSON streaming response from /ask/stream
export async function askQuestionStream(videoId, question, sessionId, onChunk, onTimestamps, onDone, onError) {
  try {
    const response = await fetch(`${API_BASE}/ask/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: videoId,
        question: question,
        session_id: sessionId
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Streaming failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(l => l.trim());

      for (const line of lines) {
        try {
          const json = JSON.parse(line);
          if (json.chunk) {
            onChunk(json.chunk);
          }
          if (json.timestamps && json.timestamps.length > 0) {
            onTimestamps(json.timestamps);
          }
        } catch (e) {
          console.warn('Failed to parse NDJSON line:', line);
        }
      }
    }
    onDone();
  } catch (error) {
    onError(error);
  }
}
