"""
Authentication views: Google OAuth flow, token refresh, logout, profile.

Flow:
  1. GET /api/auth/google/           → redirect to Google
  2. GET /api/auth/google/callback/  → receive code, exchange for tokens,
                                       create/get user, issue JWT cookies,
                                       redirect to frontend
  3. POST /api/auth/token/refresh/   → verify refresh cookie, issue new access token
  4. POST /api/auth/logout/          → clear both cookies
  5. GET  /api/auth/me/              → return authenticated user data
  6. PATCH /api/profile/             → update profile fields
"""
import secrets
import urllib.parse

import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    set_auth_cookies,
    clear_auth_cookies,
)
from .models import User
from .serializers import UserSerializer, ProfileUpdateSerializer

import jwt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_google_auth_url(state: str) -> str:
    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'state': state,
        'prompt': 'select_account',
    }
    return f"{settings.GOOGLE_OAUTH_AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"


def _exchange_code_for_tokens(code: str) -> dict:
    """Exchange OAuth authorization code for Google access/id tokens."""
    resp = requests.post(settings.GOOGLE_OAUTH_TOKEN_URL, data={
        'code': code,
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_google_user_info(access_token: str) -> dict:
    """Fetch user profile from Google userinfo endpoint."""
    resp = requests.get(
        settings.GOOGLE_OAUTH_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _get_or_create_user(google_info: dict) -> User:
    """
    Look up user by google_id, creating them if first-time sign-in.

    We match on google_id (not email) as the primary identity key.
    Email can change; google_id is stable for the lifetime of a Google account.
    """
    google_id = google_info['sub']
    email = google_info.get('email', '')
    name = google_info.get('name', '') or email.split('@')[0]
    avatar_url = google_info.get('picture', '')

    user, created = User.objects.get_or_create(
        google_id=google_id,
        defaults={
            'email': email,
            'name': name,
            'avatar_url': avatar_url,
        }
    )

    if not created:
        # Update avatar (may change) but don't overwrite email/name (user may have edited)
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            user.save(update_fields=['avatar_url', 'updated_at'])

    return user


# ---------------------------------------------------------------------------
# OAuth Views
# ---------------------------------------------------------------------------

class GoogleOAuthInitView(APIView):
    """
    Initiate Google OAuth flow.

    Generates a CSRF state token stored in the session and redirects
    the browser to Google's authorization endpoint.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        # State token prevents CSRF attacks on the OAuth callback
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state

        auth_url = _build_google_auth_url(state)
        return redirect(auth_url)


class GoogleOAuthCallbackView(APIView):
    """
    Handle the OAuth callback from Google.

    Validates state, exchanges code for tokens, fetches user info,
    creates/retrieves the user, issues JWT cookies, redirects to frontend.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        error = request.query_params.get('error')
        if error:
            # User cancelled or OAuth provider returned an error
            error_url = f"{settings.FRONTEND_URL}/login?error=oauth_cancelled"
            return redirect(error_url)

        code = request.query_params.get('code')
        state = request.query_params.get('state')

        if not code:
            return redirect(f"{settings.FRONTEND_URL}/login?error=no_code")

        # Validate CSRF state
        expected_state = request.session.get('oauth_state')
        if not state or state != expected_state:
            return redirect(f"{settings.FRONTEND_URL}/login?error=invalid_state")

        # Clear the one-time state token
        request.session.pop('oauth_state', None)

        try:
            token_data = _exchange_code_for_tokens(code)
        except requests.RequestException:
            return redirect(f"{settings.FRONTEND_URL}/login?error=token_exchange_failed")

        try:
            google_info = _get_google_user_info(token_data['access_token'])
        except requests.RequestException:
            return redirect(f"{settings.FRONTEND_URL}/login?error=userinfo_failed")

        if not google_info.get('email_verified', False):
            return redirect(f"{settings.FRONTEND_URL}/login?error=email_not_verified")

        user = _get_or_create_user(google_info)

        access_token = create_access_token(str(user.id), user.role)
        refresh_token = create_refresh_token(str(user.id))

        # Redirect to frontend with tokens in HttpOnly cookies
        response = redirect(f"{settings.FRONTEND_URL}/auth/callback")
        set_auth_cookies(response, access_token, refresh_token)
        return response


class TokenRefreshView(APIView):
    """
    Issue a new access token using the refresh token cookie.

    POST /api/auth/token/refresh/
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)

        if not refresh_token:
            return Response(
                {'error': 'unauthorized', 'detail': 'No refresh token provided.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = decode_token(refresh_token)
        except jwt.ExpiredSignatureError:
            response = Response(
                {'error': 'unauthorized', 'detail': 'Refresh token has expired. Please sign in again.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_auth_cookies(response)
            return response
        except jwt.InvalidTokenError:
            response = Response(
                {'error': 'unauthorized', 'detail': 'Invalid refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_auth_cookies(response)
            return response

        if payload.get('type') != 'refresh':
            return Response(
                {'error': 'unauthorized', 'detail': 'Token type must be refresh.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = User.objects.get(id=payload['sub'])
        except User.DoesNotExist:
            return Response(
                {'error': 'unauthorized', 'detail': 'User not found.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        new_access_token = create_access_token(str(user.id), user.role)
        new_refresh_token = create_refresh_token(str(user.id))

        response = Response({'detail': 'Tokens refreshed.'}, status=status.HTTP_200_OK)
        set_auth_cookies(response, new_access_token, new_refresh_token)
        return response


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Clear JWT cookies to sign out the user.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        response = Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response


class MeView(APIView):
    """
    GET /api/auth/me/
    Return the currently authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ProfileUpdateView(APIView):
    """
    PATCH /api/profile/
    Update the authenticated user's display name and bio.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)
