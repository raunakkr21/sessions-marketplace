"""
Management command: wait_for_db

Polls the database connection until it is available.
Used in entrypoint.sh before running migrations.
Prevents startup failures when the backend container starts before PostgreSQL is ready.
"""
import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Wait for database to be available'

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database...')
        db_conn = None
        max_retries = 30
        for attempt in range(max_retries):
            try:
                db_conn = connections['default']
                db_conn.ensure_connection()
                self.stdout.write(self.style.SUCCESS('Database available!'))
                return
            except OperationalError:
                self.stdout.write(f'  Database unavailable (attempt {attempt + 1}/{max_retries}), retrying in 1s...')
                time.sleep(1)

        self.stderr.write(self.style.ERROR('Database not available after maximum retries. Exiting.'))
        raise SystemExit(1)
