import React, { useState, useRef } from 'react';
import { BrainCircuit } from 'lucide-react';
import IngestPanel from './components/IngestPanel';
import VideoPlayer from './components/VideoPlayer';
import ChatPanel from './components/ChatPanel';
import SummaryDashboard from './components/SummaryDashboard';
import Timeline from './components/Timeline';
import './index.css';

function App() {
  const [videoId, setVideoId] = useState(null);
  const [youtubeId, setYoutubeId] = useState(null);
  const playerRef = useRef(null);

  const handleIngestSuccess = (id, ytId) => {
    setVideoId(id);
    setYoutubeId(ytId);
  };

  const handleTimestampClick = (seconds) => {
    if (playerRef.current) {
      playerRef.current.seekTo(seconds);
    }
  };

  return (
    <div>
      <header style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ 
          background: 'var(--accent-color)', 
          padding: '1rem', 
          borderRadius: '12px',
          boxShadow: '0 0 20px var(--accent-glow)'
        }}>
          <BrainCircuit size={32} color="#fff" />
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: '2rem', letterSpacing: '-0.05em' }}>AI Learning Companion</h1>
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Master any video with AI-powered insights</p>
        </div>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Left Column: Video & Chat */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <IngestPanel onIngestSuccess={handleIngestSuccess} />
          
          <div style={{ position: 'relative' }}>
            <VideoPlayer videoId={youtubeId} ref={playerRef} />
          </div>
          
          <Timeline videoId={videoId} onTimestampClick={handleTimestampClick} />
        </div>

        {/* Right Column: Summaries & Chat */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', height: 'calc(100vh - 120px)' }}>
          <div style={{ flex: '1 1 50%', overflowY: 'hidden' }}>
            <SummaryDashboard videoId={videoId} onTimestampClick={handleTimestampClick} />
          </div>
          <div style={{ flex: '1 1 50%', overflowY: 'hidden' }}>
            <ChatPanel videoId={videoId} onTimestampClick={handleTimestampClick} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
