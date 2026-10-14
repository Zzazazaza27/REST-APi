"""SQLAlchemy repository implementation for price records."""

import logging
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price import PriceRecord
from app.repositories.base import BasePriceRepository

logger = logging.getLogger(__name__)


class PriceRepository(BasePriceRepository):
    """Encapsulates database access operations for PriceRecord entities using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, ticker: str, price: float, timestamp: int) -> PriceRecord:
        """Create and persist a new PriceRecord.

        Args:
            ticker: Normalized ticker symbol (e.g., 'btc_usd').
            price: Index price float value.
            timestamp: UNIX epoch timestamp in seconds.

        Returns:
            The saved PriceRecord instance with generated ID and created_at.
        """
        record = PriceRecord(
            ticker=ticker,
            price=price,
            timestamp=timestamp,
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        logger.debug("Saved price record: %s", record)
        return record

    async def get_all_by_ticker(
        self,
        ticker: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[PriceRecord]:
        """Fetch all price records for a given ticker, ordered by timestamp descending."""
        query = (
            select(PriceRecord)
            .where(PriceRecord.ticker == ticker)
            .order_by(PriceRecord.timestamp.desc(), PriceRecord.id.desc())
        )
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_latest_by_ticker(self, ticker: str) -> Optional[PriceRecord]:
        """Retrieve the latest price record for a given ticker."""
        query = (
            select(PriceRecord)
            .where(PriceRecord.ticker == ticker)
            .order_by(PriceRecord.timestamp.desc(), PriceRecord.id.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        return result.scalars().first()

    async def get_by_date_range(
        self,
        ticker: str,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[PriceRecord]:
        """Fetch price records for a ticker within the specified UNIX timestamp boundaries."""
        query = select(PriceRecord).where(PriceRecord.ticker == ticker)

        if start_timestamp is not None:
            query = query.where(PriceRecord.timestamp >= start_timestamp)
        if end_timestamp is not None:
            query = query.where(PriceRecord.timestamp <= end_timestamp)

        query = query.order_by(PriceRecord.timestamp.desc(), PriceRecord.id.desc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count_by_ticker(self, ticker: str) -> int:
        """Count total price records for a ticker."""
        query = (
            select(func.count())
            .select_from(PriceRecord)
            .where(PriceRecord.ticker == ticker)
        )
        result = await self._session.execute(query)
        return result.scalar_one() or 0
