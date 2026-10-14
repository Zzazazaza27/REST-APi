"""Unit tests for the Deribit client."""

from unittest.mock import MagicMock
import pytest
import aiohttp

from app.clients.deribit import (
    DeribitClient,
    DeribitAPIError,
    DeribitConnectionError,
    DeribitInvalidResponseError,
)


class MockResponse:
    def __init__(self, status: int = 200, json_data: dict = None, text_data: str = ""):
        self.status = status
        self._json_data = json_data or {}
        self._text_data = text_data

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text_data


class MockContextManager:
    def __init__(self, response=None, exception=None):
        self.response = response
        self.exception = exception

    async def __aenter__(self):
        if self.exception:
            raise self.exception
        return self.response

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_deribit_client_success():
    """Test successful price extraction from valid Deribit JSON-RPC response."""
    mock_payload = {
        "jsonrpc": "2.0",
        "result": {
            "estimated_delivery_price": 83874.15,
            "index_price": 83874.15,
        },
        "testnet": False,
    }
    response = MockResponse(status=200, json_data=mock_payload)
    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.get.return_value = MockContextManager(response=response)

    client = DeribitClient(session=mock_session)
    price = await client.get_index_price("btc_usd")

    assert price == 83874.15
    mock_session.get.assert_called_once()
    _, call_kwargs = mock_session.get.call_args
    assert call_kwargs["params"] == {"index_name": "btc_usd"}


@pytest.mark.asyncio
async def test_deribit_client_normalizes_ticker():
    """Verify that ticker symbol is trimmed and converted to lowercase."""
    mock_payload = {
        "jsonrpc": "2.0",
        "result": {"index_price": 2500.50},
    }
    response = MockResponse(status=200, json_data=mock_payload)
    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.get.return_value = MockContextManager(response=response)

    client = DeribitClient(session=mock_session)
    price = await client.get_index_price("  ETH_USD  ")

    assert price == 2500.50
    _, call_kwargs = mock_session.get.call_args
    assert call_kwargs["params"] == {"index_name": "eth_usd"}


@pytest.mark.asyncio
async def test_deribit_client_api_error():
    """Verify that JSON-RPC error payload raises DeribitAPIError."""
    mock_payload = {
        "jsonrpc": "2.0",
        "error": {
            "code": -32602,
            "message": "Invalid params",
        },
    }
    response = MockResponse(status=200, json_data=mock_payload)
    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.get.return_value = MockContextManager(response=response)

    client = DeribitClient(session=mock_session)
    with pytest.raises(DeribitAPIError) as exc_info:
        await client.get_index_price("unknown_coin")

    assert "Invalid params" in str(exc_info.value)
    assert exc_info.value.error_code == -32602


@pytest.mark.asyncio
async def test_deribit_client_http_error():
    """Verify that non-200 HTTP response raises DeribitAPIError."""
    response = MockResponse(status=502, text_data="Bad Gateway")
    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.get.return_value = MockContextManager(response=response)

    client = DeribitClient(session=mock_session)
    with pytest.raises(DeribitAPIError) as exc_info:
        await client.get_index_price("btc_usd")

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_deribit_client_malformed_response():
    """Verify that response without index_price raises DeribitInvalidResponseError."""
    mock_payload = {
        "jsonrpc": "2.0",
        "result": {"other_field": 123},
    }
    response = MockResponse(status=200, json_data=mock_payload)
    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.get.return_value = MockContextManager(response=response)

    client = DeribitClient(session=mock_session)
    with pytest.raises(DeribitInvalidResponseError):
        await client.get_index_price("btc_usd")


@pytest.mark.asyncio
async def test_deribit_client_connection_retry_and_failure():
    """Verify retry logic on client network errors before raising DeribitConnectionError."""
    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.get.return_value = MockContextManager(
        exception=aiohttp.ClientConnectionError("Connection refused")
    )

    client = DeribitClient(session=mock_session, max_retries=2, retry_delay_seconds=0.01)

    with pytest.raises(DeribitConnectionError):
        await client.get_index_price("btc_usd")

    assert mock_session.get.call_count == 2
