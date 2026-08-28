import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { sessionsApi } from '../api';
import type { Session } from '../types';
import { formatDateTime, formatRelativeTime, seatsBarColor } from '../utils';

export default function CatalogPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    sessionsApi.list()
      .then(res => setSessions(res.data))
      .catch(() => setError('Could not load sessions. Please refresh.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading"><div className="spinner" /></div>;

  return (
    <div className="page">
      <div className="container" style={{ paddingTop: 'var(--spacing-10)', paddingBottom: 'var(--spacing-16)' }}>
        <div style={{ marginBottom: 'var(--spacing-10)' }}>
          <h1 className="page-title">Browse Sessions</h1>
          <p className="page-subtitle">Discover and book expert-led sessions.</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {!error && sessions.length === 0 && (
          <div className="empty-state">
            <h3>No sessions available yet</h3>
            <p>Check back soon — creators are building their sessions.</p>
          </div>
        )}

        <div className="session-grid">
          {sessions.map(session => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>
      </div>
    </div>
  );
}

function SessionCard({ session }: { session: Session }) {
  const fillPct = session.capacity > 0
    ? ((session.capacity - session.remaining_seats) / session.capacity) * 100
    : 100;

  return (
    <Link to={`/sessions/${session.id}`} className="session-card" id={`session-card-${session.id}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          {session.has_started && (
            <span className="badge badge-warning" style={{ marginBottom: 'var(--spacing-2)', display: 'inline-flex' }}>
              In Progress
            </span>
          )}
          {!session.has_started && session.remaining_seats === 0 && (
            <span className="badge badge-danger" style={{ marginBottom: 'var(--spacing-2)', display: 'inline-flex' }}>
              Full
            </span>
          )}
          {!session.has_started && session.remaining_seats > 0 && (
            <span className="badge badge-success" style={{ marginBottom: 'var(--spacing-2)', display: 'inline-flex' }}>
              {session.remaining_seats} {session.remaining_seats === 1 ? 'seat' : 'seats'} left
            </span>
          )}
        </div>
      </div>

      <h2 className="session-card-title">{session.title}</h2>
      <p className="session-card-creator">by {session.creator.name}</p>

      <p style={{
        fontSize: 'var(--font-size-sm)',
        color: 'var(--color-text-muted)',
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {session.description}
      </p>

      <div className="session-card-meta">
        <span className="session-card-meta-item">
          📅 {formatDateTime(session.start_time)}
        </span>
        <span className="session-card-meta-item">
          ⏱ {formatRelativeTime(session.start_time)}
        </span>
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-dim)', marginBottom: 4 }}>
          <span>{session.active_booking_count} / {session.capacity} booked</span>
          <span>{session.remaining_seats} remaining</span>
        </div>
        <div className="seats-bar">
          <div
            className="seats-bar-fill"
            style={{
              width: `${fillPct}%`,
              background: seatsBarColor(session.remaining_seats, session.capacity),
            }}
          />
        </div>
      </div>
    </Link>
  );
}
