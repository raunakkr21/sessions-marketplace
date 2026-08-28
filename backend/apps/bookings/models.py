"""
Booking model.

Critical invariants (see DECISIONS.md):
  A — A user cannot have two active bookings for the same session.
      Enforced by a partial unique index at the PostgreSQL level.
  B — Active bookings cannot exceed session capacity.
      Enforced transactionally in the booking service (select_for_update).
  C — Sessions that have already started cannot be booked.
      Enforced using server time in the booking service.
"""
import uuid

from django.conf import settings
from django.db import models


class Booking(models.Model):
    """
    A booking linking a user to a session.

    status choices:
      'active'    — confirmed booking, counts against capacity
      'cancelled' — cancelled by user or when creator deletes session
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        'marketplace_sessions.Session',
        on_delete=models.CASCADE,
        related_name='bookings',
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings_booking'
        ordering = ['-created_at']
        constraints = [
            # Invariant A: Partial unique constraint prevents a user from
            # having two active bookings for the same session.
            #
            # WHY a partial index (not a simple unique_together):
            #   A user can cancel a booking and rebook later.
            #   unique_together would block that permanently.
            #   The constraint only applies to status='active' rows.
            #
            # WHY this must be at the database level:
            #   Two concurrent requests can both pass an application-level check,
            #   but only one can win the unique constraint insertion race.
            #   The database serializes this guarantee — application logic cannot.
            models.UniqueConstraint(
                fields=['user', 'session'],
                condition=models.Q(status='active'),
                name='unique_active_booking_per_user_session',
            )
        ]

    def __str__(self) -> str:
        return f'{self.user.name} → {self.session.title} [{self.status}]'
