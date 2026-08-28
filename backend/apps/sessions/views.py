"""
Session views.

Public:
  GET /api/sessions/         — catalog (no auth required)
  GET /api/sessions/{id}/    — session detail (no auth required)

Creator-only:
  GET    /api/creator/dashboard/       — sessions + booking counts
  POST   /api/creator/sessions/        — create session
  PATCH  /api/creator/sessions/{id}/   — update own session
  DELETE /api/creator/sessions/{id}/   — delete own session
"""
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsCreator
from .models import Session
from .serializers import SessionSerializer, SessionWriteSerializer, CreatorSessionSerializer


# ---------------------------------------------------------------------------
# Public Views
# ---------------------------------------------------------------------------

class SessionListView(APIView):
    """
    GET /api/sessions/
    Public session catalog. No authentication required.
    Returns upcoming sessions ordered by start_time.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        sessions = Session.objects.select_related('creator').annotate(
            # Annotate booking count to avoid N+1 on list page
            active_booking_count_annotated=Count(
                'bookings',
                filter=Q(bookings__status='active')
            )
        ).order_by('start_time')

        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)


class SessionDetailView(APIView):
    """
    GET /api/sessions/{id}/
    Session detail page. No authentication required.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, session_id):
        try:
            session = Session.objects.select_related('creator').annotate(
                active_booking_count_annotated=Count(
                    'bookings',
                    filter=Q(bookings__status='active')
                )
            ).get(pk=session_id)
        except Session.DoesNotExist:
            return Response(
                {'error': 'not_found', 'detail': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SessionSerializer(session)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Creator Views
# ---------------------------------------------------------------------------

class CreatorDashboardView(APIView):
    """
    GET /api/creator/dashboard/
    Return the authenticated creator's sessions with booking counts.
    Uses a single annotated query — avoids N+1.
    """
    permission_classes = [IsAuthenticated, IsCreator]

    def get(self, request):
        sessions = Session.objects.filter(creator=request.user).annotate(
            booking_count_annotated=Count(
                'bookings',
                filter=Q(bookings__status='active')
            )
        ).order_by('start_time')

        serializer = CreatorSessionSerializer(sessions, many=True)
        return Response(serializer.data)


class CreatorSessionCreateView(APIView):
    """
    POST /api/creator/sessions/
    Create a new session. Creator role required.
    """
    permission_classes = [IsAuthenticated, IsCreator]

    def post(self, request):
        serializer = SessionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(creator=request.user)
        return Response(
            SessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class CreatorSessionDetailView(APIView):
    """
    PATCH /api/creator/sessions/{id}/  — update own session
    DELETE /api/creator/sessions/{id}/ — delete own session

    Ownership check is enforced server-side: only the session's creator
    can modify or delete it. Returning 403 (not 404) to avoid leaking
    that the session exists but is owned by someone else.
    """
    permission_classes = [IsAuthenticated, IsCreator]

    def _get_own_session(self, request, session_id):
        try:
            session = Session.objects.get(pk=session_id)
        except Session.DoesNotExist:
            return None, Response(
                {'error': 'not_found', 'detail': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Ownership check — Creator A cannot modify Creator B's session
        if session.creator != request.user:
            return None, Response(
                {'error': 'forbidden', 'detail': 'You can only modify your own sessions.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return session, None

    def patch(self, request, session_id):
        session, error_response = self._get_own_session(request, session_id)
        if error_response:
            return error_response

        serializer = SessionWriteSerializer(
            session,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated_session = serializer.save()
        return Response(SessionSerializer(updated_session).data)

    def delete(self, request, session_id):
        session, error_response = self._get_own_session(request, session_id)
        if error_response:
            return error_response

        # Cancel all active bookings before deleting the session.
        # See DECISIONS.md: we don't delete bookings — we cancel them
        # so users retain their booking history.
        session.bookings.filter(status='active').update(status='cancelled')

        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
