"""
JWT utilities for token creation and validation.

Tokens are stored in HttpOnly cookies to prevent XSS theft.
See DECISIONS.md for the full security rationale.
"""
import uuid
from datetime import datetime, timezone

import jwt
from django.conf import settings


def _utcnow() -> datetime:
    """Return current time in UTC. Always use this — never datetime.now()."""
    return datetime.now(tz=timezone.utc)


def create_access_token(user_id: str, role: str) -> str:
    """Create a short-lived JWT access token."""
    now = _utcnow()
    payload = {
        'sub': str(user_id),
        'role': role,
        'type': 'access',
        'iat': now,
        'exp': now + settings.JWT_ACCESS_TOKEN_LIFETIME,
        'jti': str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived JWT refresh token."""
    now = _utcnow()
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'iat': now,
        'exp': now + settings.JWT_REFRESH_TOKEN_LIFETIME,
        'jti': str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Raises:
        jwt.ExpiredSignatureError  — token has expired
        jwt.InvalidTokenError      — token is malformed or signature invalid
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={'require': ['sub', 'type', 'exp', 'iat']},
    )


def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    """
    Attach JWT tokens as HttpOnly cookies to the response.

    HttpOnly: prevents JavaScript access — protects against XSS.
    SameSite: configured per environment.
    Secure: True in production (HTTPS only).
    """
    samesite = getattr(settings, 'JWT_COOKIE_SAMESITE', 'Lax')
    secure = getattr(settings, 'JWT_COOKIE_SECURE', False)
    httponly = getattr(settings, 'JWT_COOKIE_HTTPONLY', True)

    access_max_age = int(settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds())
    refresh_max_age = int(settings.JWT_REFRESH_TOKEN_LIFETIME.total_seconds())

    response.set_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        access_token,
        max_age=access_max_age,
        httponly=httponly,
        samesite=samesite,
        secure=secure,
        path='/',
    )
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=refresh_max_age,
        httponly=httponly,
        samesite=samesite,
        secure=secure,
        path='/api/auth/',  # Restrict refresh cookie to auth endpoints
    )


def clear_auth_cookies(response) -> None:
    """Remove JWT cookies on logout."""
    response.delete_cookie(settings.JWT_ACCESS_COOKIE_NAME, path='/')
    response.delete_cookie(settings.JWT_REFRESH_COOKIE_NAME, path='/api/auth/')
