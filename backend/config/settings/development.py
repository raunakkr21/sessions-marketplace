"""Development settings."""
from decouple import config, Csv
from .base import *  # noqa: F401, F403

SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-insecure-key-change-in-production')
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1,backend', cast=Csv())

# In development, allow the frontend origin to make credentialed requests.
# Nginx eliminates CORS in production by proxying everything through :80.
CORS_ALLOWED_ORIGINS = [
    'http://localhost',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True  # Required for cookies

# CSRF exemption for DRF APIs that use JWT cookies
# We still enforce authentication via JWT — CSRF is relevant for session-auth flows
CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://localhost:5173',
]

# Cookie SameSite: 'Lax' works for same-origin dev; switch to 'Strict' in production
JWT_COOKIE_SAMESITE = 'Lax'
JWT_COOKIE_HTTPONLY = True
JWT_COOKIE_SECURE = False  # Set True in production with HTTPS
