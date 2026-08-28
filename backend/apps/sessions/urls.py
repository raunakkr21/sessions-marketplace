from django.urls import path
from .views import (
    SessionListView,
    SessionDetailView,
    CreatorDashboardView,
    CreatorSessionCreateView,
    CreatorSessionDetailView,
)

urlpatterns = [
    # Public
    path('sessions/', SessionListView.as_view(), name='session-list'),
    path('sessions/<uuid:session_id>/', SessionDetailView.as_view(), name='session-detail'),

    # Creator
    path('creator/dashboard/', CreatorDashboardView.as_view(), name='creator-dashboard'),
    path('creator/sessions/', CreatorSessionCreateView.as_view(), name='creator-session-create'),
    path('creator/sessions/<uuid:session_id>/', CreatorSessionDetailView.as_view(), name='creator-session-detail'),
]
