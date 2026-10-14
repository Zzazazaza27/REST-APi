"""Price record database model."""

from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceRecord(Base):
    """SQLAlchemy model representing an index price observation for a cryptocurrency ticker."""

    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_price_records_ticker_timestamp", "ticker", "timestamp"),
        Index("ix_price_records_ticker_timestamp_desc", "ticker", timestamp.desc()),
    )

    def __repr__(self) -> str:
        return (
            f"<PriceRecord(id={self.id}, ticker='{self.ticker}', "
            f"price={self.price}, timestamp={self.timestamp})>"
        )
