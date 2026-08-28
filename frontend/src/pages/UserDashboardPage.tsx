import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { bookingsApi, authApi } from '../api';
import { useAuth } from '../hooks/useAuth';
import type { BookingList } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

export default function UserDashboardPage() {
  const { user, refreshUser } = useAuth();
  const [bookings, setBookings] = useState<BookingList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Profile editing
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.name ?? '');
  const [bio, setBio] = useState(user?.bio ?? '');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    bookingsApi.myBookings()
      .then(res => setBookings(res.data))
      .catch(() => setError('Could not load bookings.'))
      .finally(() => setLoading(false));
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await authApi.updateProfile({ name, bio });
      await refreshUser();
      setEditing(false);
    } catch (err) {
      setSaveError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="page-loading"><div className="spinner" /></div>;

  return (
    <div className="page">
      <div className="container" style={{ paddingTop: 'var(--spacing-10)', paddingBottom: 'var(--spacing-16)' }}>
        <h1 className="page-title" style={{ marginBottom: 'var(--spacing-10)' }}>My Dashboard</h1>

        {/* Profile */}
        <div className="card" style={{ marginBottom: 'var(--spacing-8)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-4)', marginBottom: 'var(--spacing-4)' }}>
            {user?.avatar_url && (
              <img src={user.avatar_url} alt={user.name} style={{ width: 60, height: 60, borderRadius: '50%', objectFit: 'cover' }} />
            )}
            <div>
              <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600 }}>{user?.name}</h2>
              <p className="text-sm text-muted">{user?.email}</p>
              <span className="badge badge-primary" style={{ marginTop: 4 }}>{user?.role}</span>
            </div>
            <button
              id="edit-profile-btn"
              onClick={() => { setEditing(!editing); setName(user?.name ?? ''); setBio(user?.bio ?? ''); }}
              className="btn btn-ghost btn-sm"
              style={{ marginLeft: 'auto' }}
            >
              {editing ? 'Cancel' : 'Edit Profile'}
            </button>
          </div>

          {editing && (
            <div>
              {saveError && <div className="alert alert-error">{saveError}</div>}
              <div className="form-group">
                <label className="form-label" htmlFor="profile-name">Display Name</label>
                <input
                  id="profile-name"
                  className="form-input"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  maxLength={255}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="profile-bio">Bio</label>
                <textarea
                  id="profile-bio"
                  className="form-textarea"
                  value={bio}
                  onChange={e => setBio(e.target.value)}
                  maxLength={2000}
                  rows={3}
                />
              </div>
              <button
                id="save-profile-btn"
                onClick={handleSaveProfile}
                disabled={saving || !name.trim()}
                className="btn btn-primary"
              >
                {saving ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Saving...</> : 'Save Changes'}
              </button>
            </div>
          )}

          {!editing && user?.bio && (
            <p className="text-sm text-muted">{user.bio}</p>
          )}
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {/* Active Bookings */}
        <div style={{ marginBottom: 'var(--spacing-8)' }}>
          <h2 className="section-title" style={{ marginBottom: 'var(--spacing-4)' }}>
            Active Bookings
            {bookings && <span style={{ fontSize: 'var(--font-size-base)', color: 'var(--color-text-muted)', fontWeight: 400, marginLeft: 'var(--spacing-2)' }}>
              ({bookings.active.length})
            </span>}
          </h2>

          {bookings?.active.length === 0 ? (
            <div className="empty-state" style={{ padding: 'var(--spacing-8)' }}>
              <h3>No active bookings</h3>
              <p>Browse sessions and book one to get started.</p>
              <Link to="/" className="btn btn-primary">Browse Sessions</Link>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-4)' }}>
              {bookings?.active.map(booking => (
                <BookingCard key={booking.id} booking={booking} isActive />
              ))}
            </div>
          )}
        </div>

        {/* Past Bookings */}
        {(bookings?.past.length ?? 0) > 0 && (
          <div>
            <h2 className="section-title" style={{ marginBottom: 'var(--spacing-4)' }}>
              Past / Cancelled
              <span style={{ fontSize: 'var(--font-size-base)', color: 'var(--color-text-muted)', fontWeight: 400, marginLeft: 'var(--spacing-2)' }}>
                ({bookings?.past.length})
              </span>
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-4)' }}>
              {bookings?.past.map(booking => (
                <BookingCard key={booking.id} booking={booking} isActive={false} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function BookingCard({ booking, isActive }: { booking: any; isActive: boolean }) {
  return (
    <Link
      to={`/sessions/${booking.session.id}`}
      className="card"
      style={{ textDecoration: 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
    >
      <div>
        <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 600, color: 'var(--color-text)' }}>
          {booking.session.title}
        </h3>
        <p className="text-sm text-muted">by {booking.session.creator.name}</p>
        <p className="text-sm text-muted">{formatDateTime(booking.session.start_time)}</p>
      </div>
      <span className={`badge ${isActive ? 'badge-success' : 'badge-danger'}`}>
        {isActive ? 'Confirmed' : 'Cancelled'}
      </span>
    </Link>
  );
}
