import { useState, useEffect, useCallback } from 'react';
import { creatorApi } from '../api';
import type { CreatorSession, SessionFormData } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

export default function CreatorDashboardPage() {
  const [sessions, setSessions] = useState<CreatorSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingSession, setEditingSession] = useState<CreatorSession | null>(null);

  const loadSessions = useCallback(async () => {
    try {
      const res = await creatorApi.dashboard();
      setSessions(res.data);
    } catch {
      setError('Could not load your sessions.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  const handleDelete = async (sessionId: string) => {
    if (!confirm('Delete this session? Active bookings will be cancelled.')) return;
    try {
      await creatorApi.deleteSession(sessionId);
      await loadSessions();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  if (loading) return <div className="page-loading"><div className="spinner" /></div>;

  return (
    <div className="page">
      <div className="container" style={{ paddingTop: 'var(--spacing-10)', paddingBottom: 'var(--spacing-16)' }}>
        <div className="section-header" style={{ marginBottom: 'var(--spacing-8)' }}>
          <div>
            <h1 className="page-title">Creator Dashboard</h1>
            <p className="page-subtitle">Manage your sessions and track bookings.</p>
          </div>
          <button
            id="create-session-btn"
            onClick={() => { setEditingSession(null); setShowForm(true); }}
            className="btn btn-primary"
          >
            + New Session
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {/* Session Form Modal */}
        {showForm && (
          <SessionFormModal
            existing={editingSession}
            onClose={() => { setShowForm(false); setEditingSession(null); }}
            onSaved={() => { setShowForm(false); setEditingSession(null); loadSessions(); }}
          />
        )}

        {/* Sessions List */}
        {sessions.length === 0 ? (
          <div className="empty-state">
            <h3>No sessions yet</h3>
            <p>Create your first session to start accepting bookings.</p>
            <button
              onClick={() => setShowForm(true)}
              className="btn btn-primary"
            >
              Create Session
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-4)' }}>
            {sessions.map(session => (
              <CreatorSessionCard
                key={session.id}
                session={session}
                onEdit={() => { setEditingSession(session); setShowForm(true); }}
                onDelete={() => handleDelete(session.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function CreatorSessionCard({
  session, onEdit, onDelete
}: {
  session: CreatorSession;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const fillPct = session.capacity > 0
    ? (session.booking_count / session.capacity) * 100 : 0;

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--spacing-4)' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: 'var(--spacing-2)', marginBottom: 'var(--spacing-2)' }}>
            {session.has_started
              ? <span className="badge badge-warning">In Progress</span>
              : <span className="badge badge-success">Upcoming</span>
            }
          </div>
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--color-text)' }}>
            {session.title}
          </h3>
          <p className="text-sm text-muted" style={{ marginTop: 4 }}>
            {formatDateTime(session.start_time)} → {formatDateTime(session.end_time)}
          </p>

          <div style={{ marginTop: 'var(--spacing-4)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginBottom: 4 }}>
              <span>{session.booking_count} / {session.capacity} booked</span>
              <span>{session.remaining_seats} seats remaining</span>
            </div>
            <div className="seats-bar">
              <div
                className="seats-bar-fill"
                style={{
                  width: `${fillPct}%`,
                  background: fillPct >= 100 ? 'var(--color-danger)' : fillPct >= 80 ? 'var(--color-warning)' : 'var(--color-success)',
                }}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 'var(--spacing-2)', flexShrink: 0 }}>
          <button
            id={`edit-session-${session.id}`}
            onClick={onEdit}
            className="btn btn-secondary btn-sm"
          >
            Edit
          </button>
          <button
            id={`delete-session-${session.id}`}
            onClick={onDelete}
            className="btn btn-danger btn-sm"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

function SessionFormModal({
  existing,
  onClose,
  onSaved,
}: {
  existing: CreatorSession | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!existing;
  const [form, setForm] = useState<SessionFormData>({
    title: existing?.title ?? '',
    description: existing?.description ?? '',
    start_time: existing?.start_time ? toLocalDateTimeInput(existing.start_time) : '',
    end_time: existing?.end_time ? toLocalDateTimeInput(existing.end_time) : '',
    capacity: existing?.capacity ?? 10,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        ...form,
        // Convert local datetime-local input to UTC ISO string
        start_time: new Date(form.start_time).toISOString(),
        end_time: new Date(form.end_time).toISOString(),
      };
      if (isEdit && existing) {
        await creatorApi.updateSession(existing.id, payload);
      } else {
        await creatorApi.createSession(payload);
      }
      onSaved();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h2 className="modal-title">{isEdit ? 'Edit Session' : 'Create Session'}</h2>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="session-title">Title *</label>
            <input
              id="session-title"
              className="form-input"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              required
              maxLength={255}
              placeholder="e.g. Introduction to Machine Learning"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="session-description">Description *</label>
            <textarea
              id="session-description"
              className="form-textarea"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              required
              rows={4}
              placeholder="What will attendees learn?"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-4)' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="session-start">Start Time *</label>
              <input
                id="session-start"
                type="datetime-local"
                className="form-input"
                value={form.start_time}
                onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="session-end">End Time *</label>
              <input
                id="session-end"
                type="datetime-local"
                className="form-input"
                value={form.end_time}
                onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="session-capacity">Capacity *</label>
            <input
              id="session-capacity"
              type="number"
              className="form-input"
              value={form.capacity}
              onChange={e => setForm(f => ({ ...f, capacity: parseInt(e.target.value) || 1 }))}
              min={1}
              max={10000}
              required
            />
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn btn-ghost">Cancel</button>
            <button
              id="save-session-btn"
              type="submit"
              disabled={saving}
              className="btn btn-primary"
            >
              {saving ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Saving...</> : isEdit ? 'Save Changes' : 'Create Session'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/** Convert UTC ISO string to value compatible with datetime-local input */
function toLocalDateTimeInput(isoString: string): string {
  const d = new Date(isoString);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
