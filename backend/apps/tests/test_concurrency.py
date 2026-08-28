"""
Concurrency test — MANDATORY per assignment spec.

Creates a race condition:
  - Session with capacity = 1
  - Two authenticated users attempt to book simultaneously using threads
  - Verifies: exactly 1 succeeds, exactly 1 fails, DB has exactly 1 active booking

This test MUST run against PostgreSQL.
SQLite does not support the row-level locking used in the booking service.

Why this proves correctness:
  The threads use a threading.Barrier to synchronize their starts, making the
  booking attempts as genuinely concurrent as possible from the application layer.
  PostgreSQL's select_for_update() serializes them at the database level.

  Result: one transaction acquires the lock and commits, the other waits,
  then reads active_count = 1 >= capacity = 1 and raises SessionFullError.
  Final DB state: exactly 1 active booking.
"""
import threading
from django.test import TestCase, TransactionTestCase

from apps.bookings.models import Booking
from apps.bookings.services import create_booking
from .utils import make_user, make_creator, make_session


class ConcurrentBookingRaceTest(TransactionTestCase):
    """
    Use TransactionTestCase (not TestCase) because:
      - TransactionTestCase flushes between tests via TRUNCATE (not rollback)
      - Threads can each hold their own real database transactions
      - TestCase wraps everything in a single transaction, which causes
        deadlock when inner threads try to commit inside an outer transaction

    This test genuinely exercises the PostgreSQL locking behavior.
    """

    def test_concurrent_booking_capacity_one(self):
        """
        Scenario: session capacity = 1, two users book simultaneously.
        Expected: exactly 1 succeeds, exactly 1 fails, DB has 1 active booking.
        """
        creator = make_creator()
        user1 = make_user(suffix='concurrent_1')
        user2 = make_user(suffix='concurrent_2')
        session = make_session(creator, capacity=1)

        results = []
        errors = []

        # Barrier ensures both threads reach the create_booking call simultaneously
        barrier = threading.Barrier(2, timeout=10)

        def attempt_booking(user):
            try:
                barrier.wait()  # Synchronize: both threads start at the same moment
                booking = create_booking(user, session.id)
                results.append(('success', booking.id))
            except Exception as e:
                results.append(('failure', type(e).__name__, str(e)))
            finally:
                from django.db import connection
                connection.close()

        thread1 = threading.Thread(target=attempt_booking, args=(user1,))
        thread2 = threading.Thread(target=attempt_booking, args=(user2,))

        thread1.start()
        thread2.start()
        thread1.join(timeout=15)
        thread2.join(timeout=15)

        # ── Assertions ──────────────────────────────────────────────────────

        self.assertEqual(
            len(results), 2,
            f"Expected 2 results, got {len(results)}. Threads may have timed out."
        )

        successes = [r for r in results if r[0] == 'success']
        failures = [r for r in results if r[0] == 'failure']

        self.assertEqual(
            len(successes), 1,
            f"Expected exactly 1 successful booking. Results: {results}"
        )
        self.assertEqual(
            len(failures), 1,
            f"Expected exactly 1 failed booking. Results: {results}"
        )

        # Verify failure was SessionFullError or AlreadyBookedError (both valid)
        failure_type = failures[0][1]
        self.assertIn(
            failure_type,
            ['SessionFullError', 'AlreadyBookedError'],
            f"Expected SessionFullError or AlreadyBookedError, got {failure_type}"
        )

        # ── Database State Verification ──────────────────────────────────────
        active_count = Booking.objects.filter(
            session=session,
            status=Booking.Status.ACTIVE,
        ).count()

        self.assertEqual(
            active_count, 1,
            f"Expected exactly 1 active booking in DB, found {active_count}. "
            f"CONCURRENCY BUG: capacity was exceeded!"
        )

        total_count = Booking.objects.filter(session=session).count()
        self.assertEqual(
            total_count, 1,
            f"Expected exactly 1 booking total in DB, found {total_count}. "
            f"CONCURRENCY BUG: duplicate booking created!"
        )

    def test_concurrent_duplicate_booking_same_user(self):
        """
        Edge case: same user sends two booking requests simultaneously.
        Expected: exactly 1 succeeds, 1 fails with AlreadyBookedError.
        The PostgreSQL partial unique index is the final safety net here.
        """
        creator = make_creator()
        user = make_user(suffix='dup_concurrent')
        session = make_session(creator, capacity=10)  # capacity is not the constraint

        results = []
        barrier = threading.Barrier(2, timeout=10)

        def attempt_booking():
            try:
                barrier.wait()
                booking = create_booking(user, session.id)
                results.append(('success', booking.id))
            except Exception as e:
                results.append(('failure', type(e).__name__))
            finally:
                from django.db import connection
                connection.close()

        t1 = threading.Thread(target=attempt_booking)
        t2 = threading.Thread(target=attempt_booking)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        successes = [r for r in results if r[0] == 'success']
        self.assertEqual(
            len(successes), 1,
            f"Expected exactly 1 success for duplicate booking race. Results: {results}"
        )

        active_count = Booking.objects.filter(
            user=user, session=session, status=Booking.Status.ACTIVE
        ).count()
        self.assertEqual(active_count, 1,
            f"Expected exactly 1 active booking, found {active_count}. "
            f"CONCURRENCY BUG: duplicate booking was created!")
