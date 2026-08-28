"""
Shared test utilities: factory helpers, base test classes.
"""
import uuid
from datetime import timedelta

from django.utils import timezone

from apps.users.models import User
from apps.sessions.models import Session
from apps.bookings.models import Booking
from apps.users.jwt_utils import create_access_token


def make_user(role=User.Role.USER, suffix=None) -> User:
    """Create a test user without going through OAuth."""
    suffix = suffix or str(uuid.uuid4())[:8]
    user = User.objects.create(
        google_id=f'google_{suffix}',
        email=f'user_{suffix}@test.com',
        name=f'Test User {suffix}',
        role=role,
    )
    user.set_unusable_password()
    user.save()
    return user


def make_creator(suffix=None) -> User:
    return make_user(role=User.Role.CREATOR, suffix=suffix)


def make_session(creator: User, capacity: int = 10, minutes_from_now: int = 60) -> Session:
    """Create a future session."""
    start = timezone.now() + timedelta(minutes=minutes_from_now)
    end = start + timedelta(hours=1)
    return Session.objects.create(
        creator=creator,
        title=f'Test Session {uuid.uuid4().hex[:6]}',
        description='A test session for automated testing.',
        start_time=start,
        end_time=end,
        capacity=capacity,
    )


def make_past_session(creator: User, capacity: int = 10) -> Session:
    """Create a session that has already started."""
    start = timezone.now() - timedelta(hours=1)
    end = start + timedelta(hours=2)
    return Session.objects.create(
        creator=creator,
        title=f'Past Session {uuid.uuid4().hex[:6]}',
        description='A past session for testing.',
        start_time=start,
        end_time=end,
        capacity=capacity,
    )


def make_booking(user: User, session: Session, status=Booking.Status.ACTIVE) -> Booking:
    return Booking.objects.create(user=user, session=session, status=status)


def auth_client(client, user: User):
    """
    Authenticate a Django test client by setting the JWT cookie directly.
    This bypasses OAuth and lets us test API authorization cleanly.
    """
    from django.conf import settings
    token = create_access_token(str(user.id), user.role)
    client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = token
    return client
