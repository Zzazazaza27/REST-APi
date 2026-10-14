"""Unit tests for PriceRepository."""

import pytest
from app.repositories.price_repository import PriceRepository


@pytest.mark.asyncio
async def test_repository_save_and_retrieve(price_repository: PriceRepository):
    """Test saving a price record and retrieving it."""
    record = await price_repository.save(
        ticker="btc_usd",
        price=60000.5,
        timestamp=1700000000,
    )

    assert record.id is not None
    assert record.ticker == "btc_usd"
    assert record.price == 60000.5
    assert record.timestamp == 1700000000

    latest = await price_repository.get_latest_by_ticker("btc_usd")
    assert latest is not None
    assert latest.id == record.id
    assert latest.price == 60000.5


@pytest.mark.asyncio
async def test_repository_get_all_ordered(price_repository: PriceRepository):
    """Test that get_all_by_ticker returns records ordered by timestamp descending."""
    await price_repository.save(ticker="eth_usd", price=2000.0, timestamp=100)
    await price_repository.save(ticker="eth_usd", price=2100.0, timestamp=300)
    await price_repository.save(ticker="eth_usd", price=2050.0, timestamp=200)

    # Save record for another ticker to ensure isolation
    await price_repository.save(ticker="btc_usd", price=50000.0, timestamp=250)

    records = await price_repository.get_all_by_ticker("eth_usd")
    assert len(records) == 3
    assert [r.timestamp for r in records] == [300, 200, 100]
    assert [r.price for r in records] == [2100.0, 2050.0, 2000.0]


@pytest.mark.asyncio
async def test_repository_get_latest_none(price_repository: PriceRepository):
    """Test get_latest_by_ticker returns None for empty table/unknown ticker."""
    latest = await price_repository.get_latest_by_ticker("non_existent")
    assert latest is None


@pytest.mark.asyncio
async def test_repository_date_range_filtering(price_repository: PriceRepository):
    """Test date range boundary filtering."""
    await price_repository.save(ticker="btc_usd", price=100.0, timestamp=1000)
    await price_repository.save(ticker="btc_usd", price=200.0, timestamp=2000)
    await price_repository.save(ticker="btc_usd", price=300.0, timestamp=3000)
    await price_repository.save(ticker="btc_usd", price=400.0, timestamp=4000)

    # Filter with both start and end
    ranged = await price_repository.get_by_date_range(
        ticker="btc_usd",
        start_timestamp=1500,
        end_timestamp=3500,
    )
    assert len(ranged) == 2
    assert [r.timestamp for r in ranged] == [3000, 2000]

    # Filter with start only
    start_only = await price_repository.get_by_date_range(
        ticker="btc_usd",
        start_timestamp=3000,
    )
    assert len(start_only) == 2
    assert [r.timestamp for r in start_only] == [4000, 3000]

    # Filter with end only
    end_only = await price_repository.get_by_date_range(
        ticker="btc_usd",
        end_timestamp=2000,
    )
    assert len(end_only) == 2
    assert [r.timestamp for r in end_only] == [2000, 1000]


@pytest.mark.asyncio
async def test_repository_count(price_repository: PriceRepository):
    """Test count_by_ticker returns accurate count."""
    await price_repository.save(ticker="btc_usd", price=1.0, timestamp=1)
    await price_repository.save(ticker="btc_usd", price=2.0, timestamp=2)
    await price_repository.save(ticker="eth_usd", price=3.0, timestamp=3)

    assert await price_repository.count_by_ticker("btc_usd") == 2
    assert await price_repository.count_by_ticker("eth_usd") == 1
    assert await price_repository.count_by_ticker("sol_usd") == 0
