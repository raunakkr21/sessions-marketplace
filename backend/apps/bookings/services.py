"""
Booking service: transactional capacity enforcement.

THIS IS THE MOST CRITICAL CODE IN THE APPLICATION.

The booking invariants that must hold even under concurrent load:
  A — No user can have two active bookings for the same session.
      → Enforced by PostgreSQL partial unique constraint (final safety net).
  B — Active bookings cannot exceed session capacity.
      → Enforced by select_for_update() + transaction.atomic() (primary mechanism).
  C — Sessions that have started cannot be booked.
      → Enforced by comparing UTC server time to session.start_time.

Why select_for_update() is necessary:
  Without it, two concurrent requests could both read active_count = 0,
  both conclude capacity > 0, and both INSERT a booking — oversubscribing.

  With select_for_update(), the second request blocks on the row lock
  until the first transaction commits. It then reads the updated count
  and correctly rejects the booking if capacity is exceeded.

  This is a standard PostgreSQL advisory locking pattern for reservation systems.
  It remains correct across multiple Gunicorn workers because the lock is held
  in the database, not in process memory.

Why the unique constraint is still needed:
  select_for_update prevents the capacity race, but two different users
  booking simultaneously wouldn't be caught by capacity alone if both users
  are the same user (duplicate booking race). The unique constraint catches
  that case at the INSERT level as a final safety net.
"""
from django.db import transaction, IntegrityError
from django.utils import timezone

from apps.sessions.models import Session
from .models import Booking


class BookingError(Exception):
    """Base class for booking-related business errors."""
    pass


class SessionNotFoundError(BookingError):
    pass


class SessionAlreadyStartedError(BookingError):
    pass


class SessionFullError(BookingError):
    pass


class AlreadyBookedError(BookingError):
    pass


def create_booking(user, session_id: str) -> Booking:
    """
    Attempt to book a session for a user.

    Uses select_for_update() to acquire a PostgreSQL row-level lock on the
    session row for the duration of the transaction. This serializes all
    concurrent booking attempts for the same session, making the
    active_count check + INSERT atomic from a database perspective.

    Args:
        user: The authenticated User attempting to book.
        session_id: UUID of the target session.

    Returns:
        The created Booking instance.

    Raises:
        SessionNotFoundError    — session doesn't exist
        SessionAlreadyStartedError — session start_time is in the past
        SessionFullError        — active bookings >= capacity
        AlreadyBookedError      — user already has an active booking
    """
    try:
        with transaction.atomic():
            # ----------------------------------------------------------------
            # Acquire exclusive row-level lock on the session row.
            # Any other transaction attempting select_for_update() on this
            # session will block here until we commit or roll back.
            # This makes the subsequent count check + INSERT atomic.
            # ----------------------------------------------------------------
            try:
                session = Session.objects.select_for_update().get(pk=session_id)
            except Session.DoesNotExist:
                raise SessionNotFoundError(f'Session {session_id} not found.')

            # ----------------------------------------------------------------
            # Invariant C: Check using server time (timezone.now() is UTC).
            # We do NOT trust the frontend's remainingSeats or time display.
            # ----------------------------------------------------------------
            if timezone.now() >= session.start_time:
                raise SessionAlreadyStartedError(
                    'This session has already started and cannot be booked.'
                )

            # ----------------------------------------------------------------
            # Invariant B: Count active bookings while holding the lock.
            # Because we hold select_for_update on the session row, no other
            # transaction can insert/count bookings for this session until
            # we finish. This count is therefore accurate.
            # ----------------------------------------------------------------
            active_count = Booking.objects.filter(
                session=session,
                status=Booking.Status.ACTIVE,
            ).count()

            if active_count >= session.capacity:
                raise SessionFullError(
                    f'This session is fully booked ({session.capacity}/{session.capacity} seats taken).'
                )

            # ----------------------------------------------------------------
            # Invariant A (primary check): Verify no existing active booking.
            # The unique constraint below is the final safety net, but we
            # provide a nicer error message here.
            # ----------------------------------------------------------------
            if Booking.objects.filter(
                user=user,
                session=session,
                status=Booking.Status.ACTIVE,
            ).exists():
                raise AlreadyBookedError('You already have an active booking for this session.')

            # ----------------------------------------------------------------
            # All checks passed — create the booking.
            # If two requests somehow both reach this point (e.g. different
            # users with the same ID — theoretically impossible, but as a
            # safety net), the unique constraint will cause IntegrityError
            # on the second INSERT, which we catch below.
            # ----------------------------------------------------------------
            booking = Booking.objects.create(
                user=user,
                session=session,
                status=Booking.Status.ACTIVE,
            )
            return booking

    except IntegrityError:
        # The partial unique constraint (unique_active_booking_per_user_session)
        # fired — this user already has an active booking for this session.
        # This is the database-level safety net for any race condition that
        # slips through the application-level check above.
        raise AlreadyBookedError('You already have an active booking for this session.')
