from django.urls import path
from .views import BookSessionView, BookingListView

urlpatterns = [
    path('sessions/<uuid:session_id>/book/', BookSessionView.as_view(), name='book-session'),
    path('bookings/', BookingListView.as_view(), name='booking-list'),
]
