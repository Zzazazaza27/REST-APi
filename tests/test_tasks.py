"""Tests for periodic Celery tasks."""

from unittest.mock import AsyncMock, patch
import pytest

from app.database import Base, DatabaseSessionManager
from app.repositories.price_repository import PriceRepository
from app.tasks.price_tasks import _async_fetch_and_store_prices, fetch_and_store_prices


@pytest.mark.asyncio
async def test_async_fetch_and_store_prices():
    """Verify that _async_fetch_and_store_prices polls tickers and saves prices."""
    # Create isolated in-memory DB for this task test
    test_manager = DatabaseSessionManager(db_url="sqlite+aiosqlite:///:memory:")
    async with test_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Mock DeribitClient
    mock_client = AsyncMock()
    mock_client.get_index_price.side_effect = lambda ticker: 80000.0 if "btc" in ticker else 2500.0

    with patch("app.tasks.price_tasks.get_db_manager", return_value=test_manager):
        with patch("app.tasks.price_tasks.DeribitClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await _async_fetch_and_store_prices(["btc_usd", "eth_usd"])

            assert "btc_usd" in result["success"]
            assert "eth_usd" in result["success"]
            assert result["success"]["btc_usd"]["price"] == 80000.0
            assert result["success"]["eth_usd"]["price"] == 2500.0
            assert len(result["errors"]) == 0

            # Verify in DB
            async with test_manager.session() as session:
                repo = PriceRepository(session)
                btc = await repo.get_latest_by_ticker("btc_usd")
                eth = await repo.get_latest_by_ticker("eth_usd")
                assert btc is not None and btc.price == 80000.0
                assert eth is not None and eth.price == 2500.0

    await test_manager.close()


@pytest.mark.asyncio
async def test_async_fetch_and_store_prices_handles_individual_errors():
    """Verify that an error on one ticker does not halt processing of other tickers."""
    test_manager = DatabaseSessionManager(db_url="sqlite+aiosqlite:///:memory:")
    async with test_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    mock_client = AsyncMock()

    async def mock_get_price(ticker):
        if "btc" in ticker:
            return 82000.0
        raise RuntimeError("Deribit timeout for ETH")

    mock_client.get_index_price.side_effect = mock_get_price

    with patch("app.tasks.price_tasks.get_db_manager", return_value=test_manager):
        with patch("app.tasks.price_tasks.DeribitClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await _async_fetch_and_store_prices(["btc_usd", "eth_usd"])

            assert "btc_usd" in result["success"]
            assert "eth_usd" in result["errors"]
            assert "Deribit timeout for ETH" in result["errors"]["eth_usd"]

    await test_manager.close()


def test_celery_task_wrapper():
    """Verify Celery task entrypoint calls the async pipeline."""
    with patch(
        "app.tasks.price_tasks._async_fetch_and_store_prices",
        new=AsyncMock(return_value={"success": {"btc_usd": {"price": 80000.0}}, "errors": {}}),
    ) as mock_async_fetch:
        result = fetch_and_store_prices()
        assert "btc_usd" in result["success"]
        mock_async_fetch.assert_called_once()
