"""Celery application configuration and periodic schedule."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "deribit_tracker",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.tasks.price_tasks"],
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "fetch-deribit-prices-every-minute": {
            "task": "app.tasks.price_tasks.fetch_and_store_prices",
            "schedule": settings.FETCH_INTERVAL_SECONDS,  # Every 60.0 seconds
            "options": {"expires": 50},  # Drop if delayed more than 50s
        },
    },
)
