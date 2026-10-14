"""Deribit exchange API client using aiohttp."""

import asyncio
import logging
from typing import Any, Dict, Optional
import aiohttp

from app.clients.base import (
    BaseCryptoClient,
    DeribitAPIError,
    DeribitConnectionError,
    DeribitInvalidResponseError,
)

logger = logging.getLogger(__name__)


class DeribitClient(BaseCryptoClient):
    """Asynchronous client for interacting with the Deribit Public API.

    Implements BaseCryptoClient interface and utilizes aiohttp for async HTTP operations.
    Supports dependency injection of custom aiohttp.ClientSession or creates its own.
    """

    def __init__(
        self,
        base_url: str = "https://www.deribit.com/api/v2",
        timeout_seconds: float = 10.0,
        session: Optional[aiohttp.ClientSession] = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session = session
        self._owns_session = session is None
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds

    async def _get_session(self) -> aiohttp.ClientSession:
        """Retrieve existing active session or lazily create a new one."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close session if owned by this client instance."""
        if self._session is not None and not self._session.closed and self._owns_session:
            await self._session.close()

    async def __aenter__(self) -> "DeribitClient":
        await self._get_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def get_index_price(self, ticker: str) -> float:
        """Fetch current index price for the given ticker (e.g., 'btc_usd', 'eth_usd').

        Args:
            ticker: The currency pair ticker symbol.

        Returns:
            The current index price as float.

        Raises:
            DeribitAPIError: When Deribit API returns an error response.
            DeribitConnectionError: When network connection fails after retries.
            DeribitInvalidResponseError: When response payload lacks expected fields.
        """
        normalized_ticker = ticker.strip().lower()
        endpoint = f"{self._base_url}/public/get_index_price"
        params = {"index_name": normalized_ticker}

        last_exception: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                session = await self._get_session()
                async with session.get(endpoint, params=params) as response:
                    if response.status != 200:
                        body_text = await response.text()
                        logger.error(
                            "Deribit API HTTP error: %s for ticker %s, response: %s",
                            response.status,
                            normalized_ticker,
                            body_text,
                        )
                        raise DeribitAPIError(
                            f"Deribit HTTP error: {response.status}",
                            status_code=response.status,
                        )

                    data: Dict[str, Any] = await response.json()

                    # Check for JSON-RPC error
                    if "error" in data and data["error"]:
                        err = data["error"]
                        err_msg = err.get("message", "Unknown error")
                        err_code = err.get("code")
                        logger.warning(
                            "Deribit returned JSON-RPC error for %s: %s (code=%s)",
                            normalized_ticker,
                            err_msg,
                            err_code,
                        )
                        raise DeribitAPIError(
                            f"Deribit API error for {normalized_ticker}: {err_msg}",
                            error_code=err_code,
                        )

                    result = data.get("result")
                    if not isinstance(result, dict) or "index_price" not in result:
                        logger.error(
                            "Malformed Deribit response for %s: %s",
                            normalized_ticker,
                            data,
                        )
                        raise DeribitInvalidResponseError(
                            f"Missing 'index_price' in Deribit response for {normalized_ticker}"
                        )

                    try:
                        price = float(result["index_price"])
                    except (ValueError, TypeError) as conv_err:
                        raise DeribitInvalidResponseError(
                            f"Invalid 'index_price' format: {result['index_price']}"
                        ) from conv_err

                    logger.debug(
                        "Successfully fetched Deribit index price for %s: %s",
                        normalized_ticker,
                        price,
                    )
                    return price

            except (aiohttp.ClientError, asyncio.TimeoutError) as net_err:
                last_exception = net_err
                logger.warning(
                    "Network error fetching price for %s (attempt %d/%d): %s",
                    normalized_ticker,
                    attempt,
                    self._max_retries,
                    net_err,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay * attempt)
            except (DeribitAPIError, DeribitInvalidResponseError):
                # Application/API errors should not be retried blind
                raise

        raise DeribitConnectionError(
            f"Failed to fetch price for {normalized_ticker} after {self._max_retries} attempts: {last_exception}"
        ) from last_exception
