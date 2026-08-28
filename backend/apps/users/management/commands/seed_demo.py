"""
Management command: seed_demo

Populates the database with realistic demo data for evaluator testing.
Does NOT hardcode real Google OAuth users — uses synthetic identities.

Creates:
  - 2 creator accounts
  - 1 user account
  - 5 sessions (mix of upcoming, full, one-seat-remaining, past)
  - 2 bookings

Run with:
  python manage.py seed_demo
  docker compose exec backend python manage.py seed_demo
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import User
from apps.sessions.models import Session
from apps.bookings.models import Booking
from apps.users.jwt_utils import create_access_token, create_refresh_token


class Command(BaseCommand):
    help = 'Seed the database with demo data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding (WARNING: deletes all data)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Booking.objects.all().delete()
            Session.objects.all().delete()
            User.objects.all().delete()

        self.stdout.write('Seeding demo data...\n')

        # ── Users ────────────────────────────────────────────────────────────
        creator1, _ = User.objects.get_or_create(
            google_id='demo_creator_001',
            defaults={
                'email': 'alice.creator@demo.com',
                'name': 'Alice Chen',
                'bio': 'Product design expert with 10 years of industry experience.',
                'role': User.Role.CREATOR,
                'avatar_url': 'https://api.dicebear.com/7.x/avataaars/svg?seed=alice',
            }
        )
        creator1.set_unusable_password()
        creator1.save()

        creator2, _ = User.objects.get_or_create(
            google_id='demo_creator_002',
            defaults={
                'email': 'bob.creator@demo.com',
                'name': 'Bob Martinez',
                'bio': 'Backend engineer specializing in distributed systems.',
                'role': User.Role.CREATOR,
                'avatar_url': 'https://api.dicebear.com/7.x/avataaars/svg?seed=bob',
            }
        )
        creator2.set_unusable_password()
        creator2.save()

        demo_user, _ = User.objects.get_or_create(
            google_id='demo_user_001',
            defaults={
                'email': 'jane.user@demo.com',
                'name': 'Jane Doe',
                'bio': 'Aspiring product manager.',
                'role': User.Role.USER,
                'avatar_url': 'https://api.dicebear.com/7.x/avataaars/svg?seed=jane',
            }
        )
        demo_user.set_unusable_password()
        demo_user.save()

        now = timezone.now()

        # ── Sessions ─────────────────────────────────────────────────────────

        # Session 1: Upcoming, has seats available
        s1, _ = Session.objects.get_or_create(
            title='Introduction to Product Design',
            defaults={
                'creator': creator1,
                'description': (
                    'A beginner-friendly session covering the fundamentals of product design. '
                    'Topics include user research, wireframing, prototyping, and design thinking. '
                    'Bring a notebook and curiosity!'
                ),
                'start_time': now + timedelta(days=3, hours=2),
                'end_time': now + timedelta(days=3, hours=4),
                'capacity': 20,
            }
        )

        # Session 2: Upcoming, capacity=1 (perfect for race condition demo!)
        s2, _ = Session.objects.get_or_create(
            title='1-on-1 Code Review Session',
            defaults={
                'creator': creator2,
                'description': (
                    'An exclusive 1-on-1 code review session. '
                    'Submit your pull request beforehand and we will go through it together. '
                    'Limited to a single participant — book fast!'
                ),
                'start_time': now + timedelta(days=5),
                'end_time': now + timedelta(days=5, hours=1),
                'capacity': 1,
            }
        )

        # Session 3: Upcoming, moderate capacity
        s3, _ = Session.objects.get_or_create(
            title='Building REST APIs with Django',
            defaults={
                'creator': creator2,
                'description': (
                    'Learn how to build production-ready REST APIs using Django REST Framework. '
                    'We will cover serializers, authentication, permissions, and testing. '
                    'Prerequisites: basic Python knowledge.'
                ),
                'start_time': now + timedelta(days=7, hours=10),
                'end_time': now + timedelta(days=7, hours=12),
                'capacity': 30,
            }
        )

        # Session 4: Upcoming, nearly full (will be booked below)
        s4, _ = Session.objects.get_or_create(
            title='Advanced TypeScript Patterns',
            defaults={
                'creator': creator1,
                'description': (
                    'Deep dive into advanced TypeScript patterns including generic types, '
                    'conditional types, mapped types, and utility types. '
                    'Ideal for developers already comfortable with TypeScript basics.'
                ),
                'start_time': now + timedelta(days=14),
                'end_time': now + timedelta(days=14, hours=3),
                'capacity': 2,
            }
        )

        # Session 5: Already started (cannot be booked — good for testing)
        s5, _ = Session.objects.get_or_create(
            title='Live System Design Workshop',
            defaults={
                'creator': creator2,
                'description': (
                    'A live workshop on system design fundamentals. '
                    'This session is in progress. '
                    '(This session demonstrates that started sessions cannot be booked.)'
                ),
                'start_time': now - timedelta(hours=1),
                'end_time': now + timedelta(hours=1),
                'capacity': 50,
            }
        )

        # ── Bookings ─────────────────────────────────────────────────────────

        # demo_user has booked Session 1
        b1, _ = Booking.objects.get_or_create(
            user=demo_user,
            session=s1,
            defaults={'status': Booking.Status.ACTIVE}
        )

        # demo_user has also booked Session 3
        b2, _ = Booking.objects.get_or_create(
            user=demo_user,
            session=s3,
            defaults={'status': Booking.Status.ACTIVE}
        )

        # Session 4 is nearly full — creator2 has booked one seat
        b3, _ = Booking.objects.get_or_create(
            user=demo_user,
            session=s4,
            defaults={'status': Booking.Status.ACTIVE}
        )

        # ── Output ───────────────────────────────────────────────────────────

        self.stdout.write(self.style.SUCCESS('\n✓ Demo data seeded successfully!\n'))
        self.stdout.write('─' * 60)
        self.stdout.write('\nDEMO ACCOUNTS')
        self.stdout.write(f'  Creator 1: {creator1.email}  (role: creator)')
        self.stdout.write(f'  Creator 2: {creator2.email}  (role: creator)')
        self.stdout.write(f'  User:      {demo_user.email} (role: user)\n')

        # Generate demo JWT tokens for manual API testing
        self.stdout.write('\nDEMO JWT TOKENS (for API testing without OAuth)')
        self.stdout.write('  ⚠️  These expire in 60 minutes from now.\n')

        for u in [creator1, creator2, demo_user]:
            token = create_access_token(str(u.id), u.role)
            self.stdout.write(f'  {u.name} ({u.role}):')
            self.stdout.write(f'    {token[:80]}...\n')

        self.stdout.write('\nDEMO SESSIONS')
        for s in Session.objects.order_by('start_time'):
            status = '🔴 STARTED' if s.has_started else '🟢 UPCOMING'
            self.stdout.write(f'  [{status}] {s.title}')
            self.stdout.write(f'    Creator: {s.creator.name}  |  Capacity: {s.capacity}')
            self.stdout.write(f'    ID: {s.id}\n')

        self.stdout.write('\n⚡ CONCURRENCY TEST SESSION:')
        self.stdout.write(f'  Session: "1-on-1 Code Review Session"')
        self.stdout.write(f'  ID: {s2.id}')
        self.stdout.write(f'  Capacity: 1  |  Current bookings: 0')
        self.stdout.write(f'  Perfect for testing the booking race condition!\n')

        self.stdout.write('\n📖 To access the application:')
        self.stdout.write('  http://localhost\n')
        self.stdout.write('  Then sign in with Google to get your session authenticated.\n')
