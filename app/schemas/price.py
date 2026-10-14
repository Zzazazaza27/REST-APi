"""Pydantic schemas for price data serialization and validation."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PriceResponse(BaseModel):
    """Schema representing an individual price record."""

    id: int = Field(..., description="Unique record identifier")
    ticker: str = Field(..., description="Cryptocurrency ticker symbol (e.g., btc_usd)")
    price: float = Field(..., description="Index price value")
    timestamp: int = Field(..., description="Unix timestamp in seconds")
    created_at: datetime = Field(..., description="Timestamp when record was created in database")

    model_config = ConfigDict(from_attributes=True)


class PriceListResponse(BaseModel):
    """Schema representing a list of price records with count metadata."""

    ticker: str = Field(..., description="Cryptocurrency ticker symbol")
    count: int = Field(..., description="Number of items returned")
    items: List[PriceResponse] = Field(..., description="List of price records")


class PriceDateFilterQuery(BaseModel):
    """Schema for validating date range filter query parameters."""

    ticker: str = Field(..., min_length=1, description="Ticker name (e.g., btc_usd, eth_usd)")
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filter start datetime (ISO 8601 format, e.g. 2026-10-14 or 2026-10-14T00:00:00)",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filter end datetime (ISO 8601 format, e.g. 2026-10-14 or 2026-10-14T23:59:59)",
    )
    start_timestamp: Optional[int] = Field(
        default=None,
        ge=0,
        description="Filter start UNIX timestamp in seconds",
    )
    end_timestamp: Optional[int] = Field(
        default=None,
        ge=0,
        description="Filter end UNIX timestamp in seconds",
    )
    limit: Optional[int] = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum number of records to return",
    )
    offset: Optional[int] = Field(
        default=0,
        ge=0,
        description="Number of records to skip",
    )

    @model_validator(mode="after")
    def validate_range(self) -> "PriceDateFilterQuery":
        """Ensure start time is not after end time if both are provided."""
        # Normalize datetime to timestamp for comparison if provided
        start_ts = self.start_timestamp
        if self.start_date is not None and start_ts is None:
            start_ts = int(self.start_date.timestamp())

        end_ts = self.end_timestamp
        if self.end_date is not None and end_ts is None:
            end_ts = int(self.end_date.timestamp())

        if start_ts is not None and end_ts is not None and start_ts > end_ts:
            raise ValueError("Start date/timestamp cannot be greater than end date/timestamp")
        return self
