import logging
logger = logging.getLogger(__name__)
"""
Custom DRF Authentication class.

Reads JWT access token from HttpOnly cookie and authenticates the request.
This is the primary authentication mechanism for all API endpoints.
"""
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .jwt_utils import decode_token


class JWTCookieAuthentication(BaseAuthentication):
    """
    Authenticate requests using a JWT stored in an HttpOnly cookie.

    Returns (user, token_payload) on success.
    Returns None if no cookie is present (allows anonymous access).
    Raises AuthenticationFailed for invalid/expired tokens.
    """

    def authenticate(self, request):
        token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE_NAME)
        if not token:
            # No token → anonymous request (let permission classes decide)
            return None

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Access token has expired. Please refresh.')
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f'Invalid access token: {e}')

        if payload.get('type') != 'access':
            raise AuthenticationFailed('Token type must be access.')

        # Import here to avoid circular import
        from .models import User
        try:
            user = User.objects.get(id=payload['sub'])
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found.')

        if not user.is_active:
            raise AuthenticationFailed('User account is disabled.')

        return (user, payload)

    def authenticate_header(self, request) -> str:
        """Tell clients to use cookie-based auth (for 401 WWW-Authenticate header)."""
        return 'Cookie realm="api"'
