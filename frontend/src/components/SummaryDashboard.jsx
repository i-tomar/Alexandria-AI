import React, { useEffect, useState } from 'react';
import { AlignLeft, List, History, Loader2, PlayCircle } from 'lucide-react';
import { getOverallSummary, getTopicSummaries, getLastMinutesSummary } from '../api/client';

export default function SummaryDashboard({ videoId, onTimestampClick }) {
  const [overall, setOverall] = useState(null);
  const [topics, setTopics] = useState(null);
  const [recent, setRecent] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!videoId) return;

    const fetchSummaries = async () => {
      setLoading(true);
      try {
        const [overallData, topicsData, recentData] = await Promise.all([
          getOverallSummary(videoId).catch(() => null),
          getTopicSummaries(videoId).catch(() => null),
          getLastMinutesSummary(videoId, 5).catch(() => null)
        ]);
        
        if (overallData) setOverall(overallData.summary);
        if (topicsData) setTopics(topicsData.topics);
        if (recentData) setRecent(recentData.summary);
      } catch (err) {
        console.error("Failed to fetch summaries", err);
      } finally {
        setLoading(false);
      }
    };

    fetchSummaries();
  }, [videoId]);

  if (!videoId) {
    return (
      <div className="glass-panel" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>Summaries will appear here</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass-panel" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem' }}>
        <Loader2 className="animate-spin" size={32} color="var(--accent-color)" />
        <p style={{ color: 'var(--text-secondary)' }}>Generating comprehensive summaries...</p>
      </div>
    );
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', height: '100%', overflowY: 'auto' }}>
      
      {/* Overall Summary */}
      <section className="fade-in">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem', color: 'var(--accent-hover)' }}>
          <AlignLeft size={18} /> Overall Summary
        </h3>
        <p style={{ color: 'var(--text-primary)', lineHeight: 1.6, background: 'rgba(0,0,0,0.1)', padding: '1rem', borderRadius: '8px' }}>
          {overall || "No overall summary available."}
        </p>
      </section>

      {/* Topic Summaries */}
      <section className="fade-in" style={{ animationDelay: '0.1s' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem', color: 'var(--accent-hover)' }}>
          <List size={18} /> Key Topics
        </h3>
        {topics && topics.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {topics.map((t, i) => (
              <div 
                key={i} 
                style={{ 
                  background: 'rgba(255,255,255,0.03)', 
                  border: '1px solid var(--glass-border)',
                  padding: '1rem', 
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'background 0.2s ease'
                }}
                onClick={() => onTimestampClick && onTimestampClick(t.timestamp)}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <h4 style={{ margin: 0, fontSize: '1rem', color: '#fff' }}>{t.topic}</h4>
                  <span style={{ 
                    display: 'flex', alignItems: 'center', gap: '0.25rem', 
                    fontSize: '0.8rem', color: 'var(--accent-color)', background: 'rgba(139,92,246,0.1)',
                    padding: '0.2rem 0.5rem', borderRadius: '12px'
                  }}>
                    <PlayCircle size={12} /> {formatTime(t.timestamp)}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{t.summary}</p>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-secondary)' }}>No topics detected.</p>
        )}
      </section>

      {/* Last N Minutes */}
      <section className="fade-in" style={{ animationDelay: '0.2s' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem', color: 'var(--accent-hover)' }}>
          <History size={18} /> Last 5 Minutes
        </h3>
        <p style={{ color: 'var(--text-primary)', lineHeight: 1.6, background: 'rgba(0,0,0,0.1)', padding: '1rem', borderRadius: '8px' }}>
          {recent || "No recent summary available."}
        </p>
      </section>

    </div>
  );
}
