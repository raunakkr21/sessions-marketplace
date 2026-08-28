"""
Serializers for the users app.
"""
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Read-only user representation returned by /api/auth/me/."""

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'bio', 'avatar_url', 'role', 'created_at']
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Allows authenticated users to update their display name and bio.

    Explicitly limits updatable fields — no role escalation possible.
    """
    name = serializers.CharField(min_length=1, max_length=255)
    bio = serializers.CharField(max_length=2000, allow_blank=True, required=False)

    class Meta:
        model = User
        fields = ['name', 'bio']

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Name cannot be blank.')
        return value
