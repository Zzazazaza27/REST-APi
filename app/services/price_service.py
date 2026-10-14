"""Business logic service for cryptocurrency price operations."""

from datetime import datetime, timezone
import logging
import time
from typing import List, Optional

from app.models.price import PriceRecord
from app.repositories.base import BasePriceRepository

logger = logging.getLogger(__name__)


class PriceServiceError(Exception):
    """Base exception for price service errors."""
    pass


class InvalidDateRangeError(PriceServiceError):
    """Raised when the specified date/time range is invalid (e.g. start > end)."""
    pass


class PriceNotFoundError(PriceServiceError):
    """Raised when no price record is found for a given ticker."""
    pass


class PriceService:
    """Service encapsulating domain logic and business operations for price records."""

    def __init__(self, repository: BasePriceRepository):
        self._repository = repository

    @staticmethod
    def normalize_ticker(ticker: str) -> str:
        """Sanitize and normalize ticker string to lowercase with standard formatting.

        Args:
            ticker: Input ticker (e.g., 'BTC_USD', '  eth_usd  ').

        Returns:
            Normalized ticker (e.g., 'btc_usd').

        Raises:
            ValueError: If ticker is empty or invalid.
        """
        if not ticker or not ticker.strip():
            raise ValueError("Ticker cannot be empty")
        return ticker.strip().lower()

    @staticmethod
    def datetime_to_unix(dt: Optional[datetime]) -> Optional[int]:
        """Convert a datetime instance to UNIX epoch timestamp in seconds."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            # Assume UTC if naive
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())

    async def record_price(
        self,
        ticker: str,
        price: float,
        timestamp: Optional[int] = None,
    ) -> PriceRecord:
        """Record a new price point for a ticker.

        Args:
            ticker: Cryptocurrency ticker symbol.
            price: Index price.
            timestamp: Optional UNIX epoch timestamp; defaults to current time.

        Returns:
            The saved PriceRecord.
        """
        norm_ticker = self.normalize_ticker(ticker)
        if timestamp is None:
            timestamp = int(time.time())
        return await self._repository.save(
            ticker=norm_ticker,
            price=price,
            timestamp=timestamp,
        )

    async def get_all_prices(
        self,
        ticker: str,
        limit: Optional[int] = 1000,
        offset: Optional[int] = 0,
    ) -> List[PriceRecord]:
        """Retrieve all price records for a given ticker with optional pagination."""
        norm_ticker = self.normalize_ticker(ticker)
        return await self._repository.get_all_by_ticker(
            ticker=norm_ticker,
            limit=limit,
            offset=offset,
        )

    async def get_latest_price(self, ticker: str) -> PriceRecord:
        """Retrieve the most recent price record for a given ticker.

        Raises:
            PriceNotFoundError: If no price record exists for the ticker.
        """
        norm_ticker = self.normalize_ticker(ticker)
        record = await self._repository.get_latest_by_ticker(norm_ticker)
        if record is None:
            raise PriceNotFoundError(f"No price records found for ticker '{norm_ticker}'")
        return record

    async def get_prices_by_date(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        limit: Optional[int] = 1000,
        offset: Optional[int] = 0,
    ) -> List[PriceRecord]:
        """Retrieve price records for a ticker within a date/time range.

        Supports ISO datetime filters or UNIX timestamp filters.
        """
        norm_ticker = self.normalize_ticker(ticker)

        # Resolve start and end timestamps
        effective_start = start_timestamp
        if effective_start is None and start_date is not None:
            effective_start = self.datetime_to_unix(start_date)

        effective_end = end_timestamp
        if effective_end is None and end_date is not None:
            effective_end = self.datetime_to_unix(end_date)

        if effective_start is not None and effective_end is not None and effective_start > effective_end:
            raise InvalidDateRangeError(
                f"Start date ({effective_start}) cannot be greater than end date ({effective_end})"
            )

        return await self._repository.get_by_date_range(
            ticker=norm_ticker,
            start_timestamp=effective_start,
            end_timestamp=effective_end,
            limit=limit,
            offset=offset,
        )
