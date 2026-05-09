import React, { useState } from 'react';
import { Video, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { ingestVideo } from '../api/client';

export default function IngestPanel({ onIngestSuccess }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!url) return;
    
    setLoading(true);
    setError('');
    setSuccess(false);
    
    try {
      const videoId = await ingestVideo(url);
      setSuccess(true);
      
      // Extract YouTube ID from URL
      let ytId = null;
      try {
        const urlObj = new URL(url);
        if (urlObj.hostname.includes('youtube.com')) {
          ytId = urlObj.searchParams.get('v');
        } else if (urlObj.hostname === 'youtu.be') {
          ytId = urlObj.pathname.slice(1);
        }
      } catch (e) {
        console.warn('Could not parse YouTube ID');
      }
      
      onIngestSuccess(videoId, ytId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ marginBottom: '1.5rem' }}>
      <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.25rem' }}>
        <Video color="var(--accent-color)" /> Load Video
      </h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
        Paste a YouTube URL to begin analyzing and summarizing its contents.
      </p>
      
      <form onSubmit={handleIngest} style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <input 
          type="text" 
          value={url} 
          onChange={(e) => setUrl(e.target.value)} 
          placeholder="https://www.youtube.com/watch?v=..." 
          disabled={loading}
          style={{ flex: 1 }}
        />
        <button type="submit" disabled={loading || !url} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {loading ? (
            <><Loader2 className="animate-spin" size={18} /> Processing...</>
          ) : (
            'Analyze'
          )}
        </button>
      </form>

      {error && (
        <div className="fade-in" style={{ marginTop: '1rem', color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
          <AlertCircle size={16} /> {error}
        </div>
      )}
      
      {success && (
        <div className="fade-in" style={{ marginTop: '1rem', color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
          <CheckCircle size={16} /> Video processed successfully!
        </div>
      )}
    </div>
  );
}
