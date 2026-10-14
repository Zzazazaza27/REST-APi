"""Tasks package."""

from app.tasks.celery_app import celery_app
from app.tasks.price_tasks import fetch_and_store_prices

__all__ = ["celery_app", "fetch_and_store_prices"]
