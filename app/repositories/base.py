"""Abstract base repository for price data operations."""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.price import PriceRecord


class BasePriceRepository(ABC):
    """Interface defining database operations for cryptocurrency price records."""

    @abstractmethod
    async def save(self, ticker: str, price: float, timestamp: int) -> PriceRecord:
        """Persist a new price record in the database."""
        pass

    @abstractmethod
    async def get_all_by_ticker(
        self,
        ticker: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[PriceRecord]:
        """Fetch all price records for a specific ticker."""
        pass

    @abstractmethod
    async def get_latest_by_ticker(self, ticker: str) -> Optional[PriceRecord]:
        """Retrieve the most recent price record for a specific ticker."""
        pass

    @abstractmethod
    async def get_by_date_range(
        self,
        ticker: str,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[PriceRecord]:
        """Fetch price records for a ticker filtered by UNIX timestamp boundaries."""
        pass

    @abstractmethod
    async def count_by_ticker(self, ticker: str) -> int:
        """Get the total count of stored price records for a ticker."""
        pass
