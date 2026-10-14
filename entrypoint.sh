#!/bin/bash
set -e

echo "==================================================="
echo " Starting Deribit Price Tracker Application Service"
echo "==================================================="

# Wait for PostgreSQL database if configured
if [ -n "$POSTGRES_HOST" ]; then
    PORT="${POSTGRES_PORT:-5432}"
    echo "Waiting for PostgreSQL database at $POSTGRES_HOST:$PORT..."
    while ! nc -z "$POSTGRES_HOST" "$PORT"; do
        sleep 0.5
    done
    echo "PostgreSQL is reachable and accepting connections!"
fi

# Apply database migrations with Alembic
echo "Applying database schema migrations..."
if alembic upgrade head; then
    echo "Alembic migrations completed successfully."
else
    echo "Alembic migration command failed or already initialized, continuing..."
fi

# Check run mode: defaults to 2-container mode ("all-in-one")
MODE="${APP_MODE:-all-in-one}"

if [ "$MODE" = "all-in-one" ]; then
    echo "Running in 2-container mode (Web API + Celery Worker + Celery Beat)..."

    # Start embedded Redis if REDIS_HOST is localhost or 127.0.0.1
    if [ "$REDIS_HOST" = "localhost" ] || [ "$REDIS_HOST" = "127.0.0.1" ] || [ -z "$REDIS_HOST" ]; then
        echo "Starting embedded Redis service..."
        redis-server --daemonize yes
        echo "Embedded Redis started."
    fi

    # Start Celery worker in background
    echo "Starting Celery worker in background..."
    celery -A app.tasks.celery_app.celery_app worker --loglevel=info --concurrency=2 &

    # Start Celery beat scheduler in background
    echo "Starting Celery beat scheduler in background..."
    celery -A app.tasks.celery_app.celery_app beat --loglevel=info &

    # Run FastAPI via Uvicorn in foreground
    echo "Starting FastAPI server on http://0.0.0.0:8000..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000

elif [ "$MODE" = "web" ]; then
    echo "Starting FastAPI web service..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000

elif [ "$MODE" = "worker" ]; then
    echo "Starting Celery worker service..."
    exec celery -A app.tasks.celery_app.celery_app worker --loglevel=info --concurrency=2

elif [ "$MODE" = "beat" ]; then
    echo "Starting Celery beat scheduler service..."
    exec celery -A app.tasks.celery_app.celery_app beat --loglevel=info

else
    echo "Executing custom command: $@"
    exec "$@"
fi
