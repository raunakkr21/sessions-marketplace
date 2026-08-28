"""
Session model.

A session is a bookable event created by a creator.
All datetimes are UTC (canonical timezone strategy — see DECISIONS.md).
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Session(models.Model):
    """
    A bookable session created by a creator.

    The capacity field represents the maximum number of active bookings allowed.
    Capacity enforcement is done transactionally in the booking service.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_sessions',
        db_index=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField()
    capacity = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sessions_session'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
        ]

    def __str__(self) -> str:
        return f'{self.title} by {self.creator.name}'

    @property
    def has_started(self) -> bool:
        """
        Returns True if the session has already started.
        Uses server/database time — never browser time.
        This is the authoritative check for 'can this session be booked?'
        """
        return timezone.now() >= self.start_time

    @property
    def is_upcoming(self) -> bool:
        return not self.has_started

    @property
    def active_booking_count(self) -> int:
        """Current count of active bookings. Avoid calling in loops — use annotations."""
        return self.bookings.filter(status='active').count()
