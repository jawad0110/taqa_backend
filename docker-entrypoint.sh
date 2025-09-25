#!/bin/bash
set -e

# Run DB migrations on web startup
if [ "$PROCESS_TYPE" = "web" ]; then
    echo "Running migrations..."
    alembic upgrade head 2>/dev/null || python manage.py migrate 2>/dev/null || true
    echo "Starting Gunicorn..."
    gunicorn your_app.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120

elif [ "$PROCESS_TYPE" = "worker" ]; then
    echo "Starting Celery worker..."
    celery -A your_app worker -l info

elif [ "$PROCESS_TYPE" = "beat" ]; then
    echo "Starting Celery beat..."
    celery -A your_app beat -l info

else
    echo "No valid PROCESS_TYPE provided (web|worker|beat)."
    exit 1
fi
