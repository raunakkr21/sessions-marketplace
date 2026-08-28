"""
Authorization tests — REQUIRED by assignment spec.

Tests:
  1. A regular USER cannot call creator-only endpoints → 403
  2. Creator A cannot edit or delete Creator B's session → 403
  3. Unauthenticated user gets 401 on protected endpoints
  4. Invalid JWT token is rejected with 401

These tests use real PostgreSQL (via Django test runner with test database).
They do not mock authorization — they test the actual enforcement.
"""
from django.test import TestCase
from django.urls import reverse

from apps.users.models import User
from .utils import make_user, make_creator, make_session, auth_client


class UserCannotAccessCreatorEndpointsTest(TestCase):
    """
    Assignment requirement:
    'A User cannot call Creator-only endpoints → 403'
    """

    def setUp(self):
        self.user = make_user()
        self.creator = make_creator()
        self.session = make_session(self.creator)

    def test_user_cannot_create_session(self):
        """Regular user hitting POST /api/creator/sessions/ gets 403."""
        auth_client(self.client, self.user)
        response = self.client.post('/api/creator/sessions/', {
            'title': 'Unauthorized Session',
            'description': 'This should fail.',
            'start_time': '2099-01-01T10:00:00Z',
            'end_time': '2099-01-01T11:00:00Z',
            'capacity': 10,
        }, content_type='application/json')

        self.assertEqual(response.status_code, 403,
            f"Expected 403, got {response.status_code}. Body: {response.json()}")

    def test_user_cannot_access_creator_dashboard(self):
        """Regular user hitting GET /api/creator/dashboard/ gets 403."""
        auth_client(self.client, self.user)
        response = self.client.get('/api/creator/dashboard/')
        self.assertEqual(response.status_code, 403)

    def test_user_cannot_update_session(self):
        """Regular user hitting PATCH /api/creator/sessions/{id}/ gets 403."""
        auth_client(self.client, self.user)
        response = self.client.patch(
            f'/api/creator/sessions/{self.session.id}/',
            {'title': 'Hijacked'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_user_cannot_delete_session(self):
        """Regular user hitting DELETE /api/creator/sessions/{id}/ gets 403."""
        auth_client(self.client, self.user)
        response = self.client.delete(f'/api/creator/sessions/{self.session.id}/')
        self.assertEqual(response.status_code, 403)


class CreatorOwnershipEnforcementTest(TestCase):
    """
    Assignment requirement:
    'Creator A cannot edit or delete Creator B's session → rejected'
    """

    def setUp(self):
        self.creator_a = make_creator(suffix='a')
        self.creator_b = make_creator(suffix='b')
        # session_b is owned by creator_b
        self.session_b = make_session(self.creator_b)

    def test_creator_a_cannot_edit_creator_b_session(self):
        """Creator A PATCHing Creator B's session must receive 403."""
        auth_client(self.client, self.creator_a)
        response = self.client.patch(
            f'/api/creator/sessions/{self.session_b.id}/',
            {'title': 'Stolen Title'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403,
            f"Expected 403, got {response.status_code}. Body: {response.json()}")

        # Confirm session was NOT modified
        self.session_b.refresh_from_db()
        self.assertNotEqual(self.session_b.title, 'Stolen Title')

    def test_creator_a_cannot_delete_creator_b_session(self):
        """Creator A DELETEing Creator B's session must receive 403."""
        auth_client(self.client, self.creator_a)
        response = self.client.delete(f'/api/creator/sessions/{self.session_b.id}/')
        self.assertEqual(response.status_code, 403,
            f"Expected 403, got {response.status_code}. Body: {response.json()}")

        # Confirm session still exists
        from apps.sessions.models import Session
        self.assertTrue(Session.objects.filter(pk=self.session_b.id).exists())


class UnauthenticatedAccessTest(TestCase):
    """Unauthenticated requests to protected endpoints return 401."""

    def setUp(self):
        self.creator = make_creator()
        self.session = make_session(self.creator)

    def test_unauthenticated_cannot_book(self):
        response = self.client.post(f'/api/sessions/{self.session.id}/book/')
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_cannot_view_bookings(self):
        response = self.client.get('/api/bookings/')
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_cannot_access_me(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)

    def test_public_session_list_is_accessible(self):
        """Public catalog requires no authentication."""
        response = self.client.get('/api/sessions/')
        self.assertEqual(response.status_code, 200)


class InvalidTokenTest(TestCase):
    """Invalid or expired JWT tokens receive 401."""

    def test_invalid_jwt_returns_401(self):
        """A malformed or tampered token is rejected."""
        self.client.cookies['access_token'] = 'not.a.valid.jwt.token'
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)

    def test_expired_jwt_returns_401(self):
        """An expired JWT is rejected with a descriptive error."""
        from datetime import timedelta
        import jwt
        from django.conf import settings
        from django.utils import timezone

        # Manually craft an already-expired token
        now = timezone.now()
        payload = {
            'sub': str(make_user().id),
            'role': 'user',
            'type': 'access',
            'iat': now - timedelta(hours=2),
            'exp': now - timedelta(hours=1),  # expired 1 hour ago
            'jti': 'test-jti',
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')

        self.client.cookies['access_token'] = expired_token
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('expired', data['detail'].lower())
