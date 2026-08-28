from django.urls import path
from .views import (
    GoogleOAuthInitView,
    GoogleOAuthCallbackView,
    TokenRefreshView,
    LogoutView,
    MeView,
    ProfileUpdateView,
)

urlpatterns = [
    # OAuth initiation — browser redirect to Google
    path('google/', GoogleOAuthInitView.as_view(), name='auth-google-init'),
    # OAuth callback — Google redirects here with authorization code
    path('google/callback/', GoogleOAuthCallbackView.as_view(), name='auth-google-callback'),
    # Token operations
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    # Current user
    path('me/', MeView.as_view(), name='auth-me'),
    # Profile — separate prefix for clarity
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
]
