#!/bin/sh
set -e

echo "==> Waiting for PostgreSQL..."
# Wait until Django can connect (settings already have correct host)
python manage.py wait_for_db

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
