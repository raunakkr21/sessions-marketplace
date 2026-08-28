"""
Serializers for the sessions app.
"""
from django.utils import timezone
from rest_framework import serializers

from apps.users.serializers import UserSerializer
from .models import Session


class SessionSerializer(serializers.ModelSerializer):
    """
    Full session representation including creator info and computed fields.
    Used for public catalog and detail views.
    """
    creator = UserSerializer(read_only=True)
    has_started = serializers.BooleanField(read_only=True)
    active_booking_count = serializers.SerializerMethodField()
    remaining_seats = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'title', 'description',
            'creator', 'start_time', 'end_time', 'capacity',
            'active_booking_count', 'remaining_seats',
            'has_started', 'created_at', 'updated_at',
        ]

    def get_active_booking_count(self, obj) -> int:
        # Use annotated value if present (avoids N+1), else fall back to property
        return getattr(obj, 'active_booking_count_annotated', obj.active_booking_count)

    def get_remaining_seats(self, obj) -> int:
        count = self.get_active_booking_count(obj)
        return max(0, obj.capacity - count)


class SessionWriteSerializer(serializers.ModelSerializer):
    """
    Used for session creation and updates by creators.
    Validates business rules server-side.
    """

    class Meta:
        model = Session
        fields = ['title', 'description', 'start_time', 'end_time', 'capacity']

    def validate_capacity(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError('Capacity must be at least 1.')
        if value > 10000:
            raise serializers.ValidationError('Capacity cannot exceed 10,000.')
        return value

    def validate_start_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('Start time must be in the future.')
        return value

    def validate(self, data):
        start = data.get('start_time') or (self.instance.start_time if self.instance else None)
        end = data.get('end_time') or (self.instance.end_time if self.instance else None)

        if start and end:
            if end <= start:
                raise serializers.ValidationError(
                    {'end_time': 'End time must be after start time.'}
                )
            duration = end - start
            if duration.total_seconds() < 300:  # minimum 5 minutes
                raise serializers.ValidationError(
                    {'end_time': 'Session must be at least 5 minutes long.'}
                )

        return data


class CreatorSessionSerializer(serializers.ModelSerializer):
    """
    Creator dashboard view of their own session, including booking counts.
    Used to avoid N+1 queries — booking_count should be annotated at query time.
    """
    booking_count = serializers.SerializerMethodField()
    remaining_seats = serializers.SerializerMethodField()
    has_started = serializers.BooleanField(read_only=True)

    class Meta:
        model = Session
        fields = [
            'id', 'title', 'description',
            'start_time', 'end_time', 'capacity',
            'booking_count', 'remaining_seats',
            'has_started', 'created_at', 'updated_at',
        ]

    def get_booking_count(self, obj) -> int:
        return getattr(obj, 'booking_count_annotated', obj.active_booking_count)

    def get_remaining_seats(self, obj) -> int:
        count = self.get_booking_count(obj)
        return max(0, obj.capacity - count)
