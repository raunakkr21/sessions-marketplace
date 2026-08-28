"""
Booking serializers.
"""
from rest_framework import serializers
from apps.sessions.serializers import SessionSerializer
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    """Full booking representation for user dashboard."""
    session = SessionSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'session', 'status', 'created_at', 'updated_at']
        read_only_fields = fields
