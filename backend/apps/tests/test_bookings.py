"""
Booking business logic tests.

Tests:
  1. Valid booking succeeds
  2. Duplicate booking is rejected (Invariant A)
  3. Full session is rejected (Invariant B)
  4. Session that has started cannot be booked (Invariant C)
  5. Nonexistent session returns 404
  6. Creator deleting a session cancels active bookings
"""
from django.test import TestCase

from apps.bookings.models import Booking
from apps.bookings.services import (
    create_booking,
    AlreadyBookedError,
    SessionFullError,
    SessionAlreadyStartedError,
    SessionNotFoundError,
)
from .utils import make_user, make_creator, make_session, make_past_session, auth_client


class ValidBookingTest(TestCase):
    def test_valid_booking_creates_active_booking(self):
        creator = make_creator()
        user = make_user()
        session = make_session(creator, capacity=5)

        booking = create_booking(user, session.id)

        self.assertEqual(booking.status, Booking.Status.ACTIVE)
        self.assertEqual(booking.user, user)
        self.assertEqual(booking.session, session)


class DuplicateBookingTest(TestCase):
    """Invariant A: A user cannot have two active bookings for the same session."""

    def test_duplicate_booking_is_rejected(self):
        creator = make_creator()
        user = make_user()
        session = make_session(creator, capacity=10)

        # First booking succeeds
        create_booking(user, session.id)

        # Second booking raises AlreadyBookedError
        with self.assertRaises(AlreadyBookedError):
            create_booking(user, session.id)

        # Only one active booking exists
        active_count = Booking.objects.filter(
            user=user, session=session, status=Booking.Status.ACTIVE
        ).count()
        self.assertEqual(active_count, 1)

    def test_duplicate_booking_via_api_returns_409(self):
        creator = make_creator()
        user = make_user()
        session = make_session(creator, capacity=10)
        auth_client(self.client, user)

        # First booking
        response1 = self.client.post(f'/api/sessions/{session.id}/book/')
        self.assertEqual(response1.status_code, 201)

        # Second booking
        response2 = self.client.post(f'/api/sessions/{session.id}/book/')
        self.assertEqual(response2.status_code, 409)
        self.assertEqual(response2.json()['error'], 'conflict')


class FullSessionTest(TestCase):
    """Invariant B: Active bookings cannot exceed session capacity."""

    def test_booking_full_session_is_rejected(self):
        creator = make_creator()
        user1 = make_user(suffix='u1')
        user2 = make_user(suffix='u2')
        session = make_session(creator, capacity=1)

        # First booking fills the session
        create_booking(user1, session.id)

        # Second booking is rejected
        with self.assertRaises(SessionFullError):
            create_booking(user2, session.id)

        # Confirm only 1 active booking
        active_count = Booking.objects.filter(
            session=session, status=Booking.Status.ACTIVE
        ).count()
        self.assertEqual(active_count, 1)

    def test_full_session_via_api_returns_409(self):
        creator = make_creator()
        user1 = make_user(suffix='a1')
        user2 = make_user(suffix='a2')
        session = make_session(creator, capacity=1)

        auth_client(self.client, user1)
        r1 = self.client.post(f'/api/sessions/{session.id}/book/')
        self.assertEqual(r1.status_code, 201)

        auth_client(self.client, user2)
        r2 = self.client.post(f'/api/sessions/{session.id}/book/')
        self.assertEqual(r2.status_code, 409)


class StartedSessionTest(TestCase):
    """Invariant C: Sessions that have already started cannot be booked."""

    def test_booking_started_session_is_rejected(self):
        creator = make_creator()
        user = make_user()
        past_session = make_past_session(creator)

        with self.assertRaises(SessionAlreadyStartedError):
            create_booking(user, past_session.id)

    def test_started_session_via_api_returns_409(self):
        creator = make_creator()
        user = make_user()
        past_session = make_past_session(creator)
        auth_client(self.client, user)

        response = self.client.post(f'/api/sessions/{past_session.id}/book/')
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertIn('started', data['detail'].lower())


class NonexistentSessionTest(TestCase):
    def test_booking_nonexistent_session_returns_404(self):
        user = make_user()
        auth_client(self.client, user)

        import uuid
        fake_id = uuid.uuid4()
        response = self.client.post(f'/api/sessions/{fake_id}/book/')
        self.assertEqual(response.status_code, 404)


class SessionDeletionTest(TestCase):
    """When a creator deletes a session, active bookings are cancelled."""

    def test_deleting_session_cancels_bookings(self):
        creator = make_creator()
        user = make_user()
        session = make_session(creator, capacity=5)

        # Create a booking
        booking = create_booking(user, session.id)
        self.assertEqual(booking.status, Booking.Status.ACTIVE)

        # Creator deletes the session via API
        auth_client(self.client, creator)
        response = self.client.delete(f'/api/creator/sessions/{session.id}/')
        self.assertEqual(response.status_code, 204)

        # Booking is cascade-deleted because Session is deleted
        with self.assertRaises(Booking.DoesNotExist):
            booking.refresh_from_db()
