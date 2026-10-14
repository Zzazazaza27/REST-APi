"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.price_repository import PriceRepository


@pytest.mark.asyncio
async def test_get_all_prices_missing_ticker_fails(client: AsyncClient):
    """Verify that calling /api/v1/prices without mandatory 'ticker' parameter returns 422."""
    response = await client.get("/api/v1/prices")
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Verify the error is specifically for the 'ticker' query parameter
    errors = data["detail"]
    assert any("ticker" in err.get("loc", []) for err in errors)


@pytest.mark.asyncio
async def test_get_latest_price_missing_ticker_fails(client: AsyncClient):
    """Verify that calling /api/v1/prices/latest without mandatory 'ticker' returns 422."""
    response = await client.get("/api/v1/prices/latest")
    assert response.status_code == 422
    data = response.json()
    assert any("ticker" in err.get("loc", []) for err in data["detail"])


@pytest.mark.asyncio
async def test_get_filter_price_missing_ticker_fails(client: AsyncClient):
    """Verify that calling /api/v1/prices/filter without mandatory 'ticker' returns 422."""
    response = await client.get("/api/v1/prices/filter")
    assert response.status_code == 422
    data = response.json()
    assert any("ticker" in err.get("loc", []) for err in data["detail"])


@pytest.mark.asyncio
async def test_get_all_prices_empty(client: AsyncClient):
    """Verify that querying an empty database returns 200 with an empty list."""
    response = await client.get("/api/v1/prices?ticker=btc_usd")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_prices_success(client: AsyncClient, db_session: AsyncSession):
    """Verify fetching all prices for a ticker."""
    repo = PriceRepository(db_session)
    await repo.save("btc_usd", 60000.0, 1700000001)
    await repo.save("btc_usd", 60100.0, 1700000060)
    await repo.save("eth_usd", 3000.0, 1700000060)

    response = await client.get("/api/v1/prices?ticker=btc_usd")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert items[0]["price"] == 60100.0
    assert items[0]["timestamp"] == 1700000060
    assert items[0]["ticker"] == "btc_usd"
    assert items[1]["price"] == 60000.0


@pytest.mark.asyncio
async def test_get_latest_price_success(client: AsyncClient, db_session: AsyncSession):
    """Verify fetching the single latest price for a ticker."""
    repo = PriceRepository(db_session)
    await repo.save("eth_usd", 3100.0, 1700000010)
    await repo.save("eth_usd", 3200.0, 1700000070)

    response = await client.get("/api/v1/prices/latest?ticker=eth_usd")
    assert response.status_code == 200
    item = response.json()
    assert item["ticker"] == "eth_usd"
    assert item["price"] == 3200.0
    assert item["timestamp"] == 1700000070


@pytest.mark.asyncio
async def test_get_latest_price_not_found(client: AsyncClient):
    """Verify 404 is returned when no records exist for the ticker."""
    response = await client.get("/api/v1/prices/latest?ticker=non_existent_usd")
    assert response.status_code == 404
    data = response.json()
    assert "No price records found" in data["detail"]


@pytest.mark.asyncio
async def test_get_prices_by_date_filter_timestamps(client: AsyncClient, db_session: AsyncSession):
    """Verify filtering prices by UNIX timestamp boundaries."""
    repo = PriceRepository(db_session)
    await repo.save("btc_usd", 100.0, 1000)
    await repo.save("btc_usd", 200.0, 2000)
    await repo.save("btc_usd", 300.0, 3000)
    await repo.save("btc_usd", 400.0, 4000)

    response = await client.get(
        "/api/v1/prices/filter?ticker=btc_usd&start_timestamp=1500&end_timestamp=3500"
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert [i["timestamp"] for i in items] == [3000, 2000]


@pytest.mark.asyncio
async def test_get_prices_by_date_filter_iso_dates(client: AsyncClient, db_session: AsyncSession):
    """Verify filtering prices using ISO 8601 datetime strings."""
    repo = PriceRepository(db_session)
    # 2026-10-14 10:00:00 UTC = 1791972000
    # 2026-10-14 12:00:00 UTC = 1791979200
    # 2026-10-14 14:00:00 UTC = 1791986400
    await repo.save("btc_usd", 1000.0, 1791972000)
    await repo.save("btc_usd", 1100.0, 1791979200)
    await repo.save("btc_usd", 1200.0, 1791986400)

    response = await client.get(
        "/api/v1/prices/filter?ticker=btc_usd&start_date=2026-10-14T11:00:00Z&end_date=2026-10-14T13:00:00Z"
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["timestamp"] == 1791979200
    assert items[0]["price"] == 1100.0


@pytest.mark.asyncio
async def test_get_prices_by_date_invalid_range_fails(client: AsyncClient):
    """Verify that specifying start date/timestamp greater than end returns 400."""
    response = await client.get(
        "/api/v1/prices/filter?ticker=btc_usd&start_timestamp=5000&end_timestamp=2000"
    )
    assert response.status_code == 400
    data = response.json()
    assert "cannot be greater than" in data["detail"]


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Verify the /health endpoint responds with 200 and healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
