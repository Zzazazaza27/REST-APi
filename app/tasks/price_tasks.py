"""Periodic Celery tasks for fetching and storing crypto prices."""

import asyncio
import logging
import time
from typing import Any, Dict, List

from app.clients.deribit import DeribitClient
from app.config import get_settings
from app.database import get_db_manager
from app.repositories.price_repository import PriceRepository
from app.services.price_service import PriceService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _async_fetch_and_store_prices(tickers: List[str]) -> Dict[str, Any]:
    """Asynchronous coroutine that fetches index prices via aiohttp and commits them to PostgreSQL.

    Args:
        tickers: List of currency pair tickers to poll (e.g. ['btc_usd', 'eth_usd']).

    Returns:
        Summary dictionary with successful and failed ticker updates.
    """
    settings = get_settings()
    results: Dict[str, Any] = {"success": {}, "errors": {}, "timestamp": int(time.time())}

    db_manager = get_db_manager()

    async with DeribitClient(
        base_url=settings.DERIBIT_BASE_URL,
        timeout_seconds=settings.DERIBIT_TIMEOUT_SECONDS,
    ) as client:
        async with db_manager.session() as session:
            repository = PriceRepository(session=session)
            service = PriceService(repository=repository)

            current_timestamp = int(time.time())

            for ticker in tickers:
                try:
                    price = await client.get_index_price(ticker)
                    record = await service.record_price(
                        ticker=ticker,
                        price=price,
                        timestamp=current_timestamp,
                    )
                    results["success"][ticker] = {
                        "id": record.id,
                        "price": price,
                        "timestamp": current_timestamp,
                    }
                    logger.info(
                        "Stored price observation: ticker=%s, price=%.4f, timestamp=%d",
                        ticker,
                        price,
                        current_timestamp,
                    )
                except Exception as exc:
                    logger.exception("Failed to fetch or store price for ticker '%s': %s", ticker, exc)
                    results["errors"][ticker] = str(exc)

    return results


@celery_app.task(name="app.tasks.price_tasks.fetch_and_store_prices", bind=True, max_retries=2)
def fetch_and_store_prices(self) -> Dict[str, Any]:
    """Periodic Celery task triggered every minute to poll Deribit and store prices."""
    settings = get_settings()
    tickers = settings.TRACKED_TICKERS
    logger.info("Executing periodic price update for tickers: %s", tickers)

    try:
        # Run asynchronous client & DB operations in event loop
        report = asyncio.run(_async_fetch_and_store_prices(tickers=tickers))
        logger.info("Periodic price update finished: %s", report)
        return report
    except Exception as task_err:
        logger.exception("Unexpected error in fetch_and_store_prices task: %s", task_err)
        raise self.retry(exc=task_err, countdown=5)
