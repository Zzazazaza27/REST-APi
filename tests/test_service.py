"""Unit tests for PriceService."""

from datetime import datetime, timezone
import pytest

from app.services.price_service import (
    PriceService,
    PriceNotFoundError,
    InvalidDateRangeError,
)


@pytest.mark.asyncio
async def test_service_normalize_ticker():
    """Verify ticker sanitization."""
    assert PriceService.normalize_ticker("BTC_USD") == "btc_usd"
    assert PriceService.normalize_ticker("  eth_usd  ") == "eth_usd"

    with pytest.raises(ValueError):
        PriceService.normalize_ticker("")

    with pytest.raises(ValueError):
        PriceService.normalize_ticker("   ")


@pytest.mark.asyncio
async def test_service_record_and_get_all(price_service: PriceService):
    """Test price recording and querying all prices via service."""
    record = await price_service.record_price(
        ticker="BTC_USD",
        price=70000.0,
        timestamp=1700000010,
    )
    assert record.ticker == "btc_usd"
    assert record.price == 70000.0

    all_records = await price_service.get_all_prices("btc_usd")
    assert len(all_records) == 1
    assert all_records[0].price == 70000.0


@pytest.mark.asyncio
async def test_service_get_latest_not_found(price_service: PriceService):
    """Verify PriceNotFoundError is raised when no records exist."""
    with pytest.raises(PriceNotFoundError):
        await price_service.get_latest_price("btc_usd")


@pytest.mark.asyncio
async def test_service_get_latest_success(price_service: PriceService):
    """Verify latest price returns newest observation."""
    await price_service.record_price(ticker="btc_usd", price=100.0, timestamp=1000)
    await price_service.record_price(ticker="btc_usd", price=200.0, timestamp=2000)

    latest = await price_service.get_latest_price("btc_usd")
    assert latest.price == 200.0
    assert latest.timestamp == 2000


@pytest.mark.asyncio
async def test_service_date_filter_validation(price_service: PriceService):
    """Verify that start > end raises InvalidDateRangeError."""
    with pytest.raises(InvalidDateRangeError):
        await price_service.get_prices_by_date(
            ticker="btc_usd",
            start_timestamp=2000,
            end_timestamp=1000,
        )

    with pytest.raises(InvalidDateRangeError):
        dt_start = datetime(2026, 1, 2, tzinfo=timezone.utc)
        dt_end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        await price_service.get_prices_by_date(
            ticker="btc_usd",
            start_date=dt_start,
            end_date=dt_end,
        )
