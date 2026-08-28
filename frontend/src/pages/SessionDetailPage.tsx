import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { sessionsApi, bookingsApi } from '../api';
import { bookingsApi as bApi } from '../api';
import type { Session, Booking } from '../types';
import { formatDateTime, getErrorMessage, seatsBarColor } from '../utils';

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [myBooking, setMyBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [bookingSuccess, setBookingSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!id) return;
    try {
      const [sessionRes, bookingsRes] = await Promise.all([
        sessionsApi.detail(id),
        bApi.myBookings(),
      ]);
      setSession(sessionRes.data);
      // Check if the user already has an active booking for this session
      const existing = bookingsRes.data.active.find(b => b.session.id === id);
      setMyBooking(existing ?? null);
    } catch {
      setError('Could not load session details.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleBook = async () => {
    if (!session) return;
    setBooking(true);
    setBookingError(null);
    try {
      await bookingsApi.book(session.id);
      setBookingSuccess(true);
      await loadData(); // Refresh to get updated counts + booking
    } catch (err) {
      setBookingError(getErrorMessage(err));
    } finally {
      setBooking(false);
    }
  };

  if (loading) return <div className="page-loading"><div className="spinner" /></div>;
  if (error || !session) return (
    <div className="page">
      <div className="container" style={{ paddingTop: 'var(--spacing-10)' }}>
        <div className="alert alert-error">{error ?? 'Session not found.'}</div>
        <Link to="/" className="btn btn-secondary">← Back to Catalog</Link>
      </div>
    </div>
  );

  const isFull = session.remaining_seats === 0 && !session.has_started;
  const fillPct = session.capacity > 0
    ? ((session.capacity - session.remaining_seats) / session.capacity) * 100 : 100;

  const bookingDisabledReason = myBooking
    ? 'You have already booked this session.'
    : session.has_started
      ? 'This session has already started.'
      : isFull
        ? 'This session is fully booked.'
        : null;

  return (
    <div className="page">
      <div className="container" style={{ paddingTop: 'var(--spacing-10)', paddingBottom: 'var(--spacing-16)', maxWidth: 720 }}>

        <Link to="/" className="btn btn-ghost btn-sm" style={{ marginBottom: 'var(--spacing-6)' }}>
          ← Back to Catalog
        </Link>

        {/* Status badges */}
        <div style={{ display: 'flex', gap: 'var(--spacing-2)', marginBottom: 'var(--spacing-4)' }}>
          {session.has_started && <span className="badge badge-warning">In Progress</span>}
          {!session.has_started && isFull && <span className="badge badge-danger">Fully Booked</span>}
          {!session.has_started && !isFull && (
            <span className="badge badge-success">{session.remaining_seats} seats available</span>
          )}
          {myBooking && <span className="badge badge-primary">✓ Booked</span>}
        </div>

        <h1 style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 700, marginBottom: 'var(--spacing-2)' }}>
          {session.title}
        </h1>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-8)' }}>
          by <strong style={{ color: 'var(--color-text)' }}>{session.creator.name}</strong>
        </p>

        <div className="card" style={{ marginBottom: 'var(--spacing-6)' }}>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, marginBottom: 'var(--spacing-4)' }}>
            About this session
          </h2>
          <p style={{ color: 'var(--color-text-muted)', lineHeight: 1.8 }}>{session.description}</p>
        </div>

        <div className="card" style={{ marginBottom: 'var(--spacing-6)' }}>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, marginBottom: 'var(--spacing-4)' }}>
            Details
          </h2>
          <div style={{ display: 'grid', gap: 'var(--spacing-4)' }}>
            <DetailRow label="Start time" value={formatDateTime(session.start_time)} />
            <DetailRow label="End time" value={formatDateTime(session.end_time)} />
            <DetailRow label="Capacity" value={`${session.capacity} seats`} />
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)', marginBottom: 4 }}>
                <span style={{ color: 'var(--color-text-muted)' }}>
                  {session.active_booking_count} / {session.capacity} booked
                </span>
                <span style={{ color: 'var(--color-text-muted)' }}>
                  {session.remaining_seats} remaining
                </span>
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
          </div>
        </div>

        {/* Booking Action */}
        <div className="card">
          {bookingSuccess && (
            <div className="alert alert-success">
              ✓ You're booked! See your confirmed booking in your dashboard.
            </div>
          )}
          {bookingError && (
            <div className="alert alert-error">{bookingError}</div>
          )}
          {bookingDisabledReason && !bookingSuccess && (
            <div className="alert alert-info">{bookingDisabledReason}</div>
          )}
          <button
            id="book-session-btn"
            onClick={handleBook}
            disabled={!!bookingDisabledReason || booking || bookingSuccess}
            className="btn btn-primary btn-lg"
            style={{ width: '100%' }}
            title={bookingDisabledReason ?? undefined}
          >
            {booking ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Booking...</> :
             myBooking ? '✓ Already Booked' :
             bookingSuccess ? '✓ Booked!' :
             session.has_started ? 'Session Has Started' :
             isFull ? 'Session Full' :
             'Book This Session'}
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)' }}>
      <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ color: 'var(--color-text)', fontWeight: 500 }}>{value}</span>
    </div>
  );
}
