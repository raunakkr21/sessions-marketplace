"""
Booking views.

POST /api/sessions/{id}/book/  — book a session
GET  /api/bookings/            — list user's bookings (active + past)
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking
from .serializers import BookingSerializer
from .services import (
    create_booking,
    SessionNotFoundError,
    SessionAlreadyStartedError,
    SessionFullError,
    AlreadyBookedError,
)


class BookSessionView(APIView):
    """
    POST /api/sessions/{session_id}/book/

    Attempt to book the given session for the authenticated user.
    All capacity and duplicate checks happen transactionally in the service layer.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            booking = create_booking(user=request.user, session_id=session_id)
        except SessionNotFoundError as e:
            return Response(
                {'error': 'not_found', 'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except SessionAlreadyStartedError as e:
            return Response(
                {'error': 'conflict', 'detail': str(e)},
                status=status.HTTP_409_CONFLICT,
            )
        except SessionFullError as e:
            return Response(
                {'error': 'conflict', 'detail': str(e)},
                status=status.HTTP_409_CONFLICT,
            )
        except AlreadyBookedError as e:
            return Response(
                {'error': 'conflict', 'detail': str(e)},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = BookingSerializer(booking)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookingListView(APIView):
    """
    GET /api/bookings/

    Return the authenticated user's bookings, split by status.
    Active bookings = upcoming confirmed bookings.
    Past/cancelled bookings = completed or cancelled.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user).select_related(
            'session', 'session__creator'
        ).order_by('-created_at')

        active = BookingSerializer(
            bookings.filter(status=Booking.Status.ACTIVE),
            many=True,
        ).data
        past = BookingSerializer(
            bookings.filter(status=Booking.Status.CANCELLED),
            many=True,
        ).data

        return Response({
            'active': active,
            'past': past,
        })
