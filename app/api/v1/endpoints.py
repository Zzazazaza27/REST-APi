"""FastAPI v1 price query endpoints."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_price_service
from app.schemas.price import PriceResponse
from app.services.price_service import (
    InvalidDateRangeError,
    PriceNotFoundError,
    PriceService,
)

router = APIRouter(prefix="/prices", tags=["Prices"])


@router.get(
    "",
    response_model=List[PriceResponse],
    summary="Get all stored price records for a currency",
    description="Fetches all historic price records for the specified ticker, ordered newest to oldest.",
)
@router.get(
    "/all",
    response_model=List[PriceResponse],
    include_in_schema=False,
)
async def get_all_prices(
    ticker: str = Query(
        ...,
        min_length=1,
        description="Mandatory ticker symbol (e.g. btc_usd, eth_usd)",
        examples=["btc_usd", "eth_usd"],
    ),
    limit: Optional[int] = Query(
        1000,
        ge=1,
        le=10000,
        description="Maximum number of records to return",
    ),
    offset: Optional[int] = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
    service: PriceService = Depends(get_price_service),
) -> List[PriceResponse]:
    """Retrieve all price records for the specified currency ticker."""
    try:
        records = await service.get_all_prices(
            ticker=ticker,
            limit=limit,
            offset=offset,
        )
        return [PriceResponse.model_validate(r) for r in records]
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err


@router.get(
    "/latest",
    response_model=PriceResponse,
    summary="Get the latest price for a currency",
    description="Retrieves the single most recent price record recorded for the specified ticker.",
)
async def get_latest_price(
    ticker: str = Query(
        ...,
        min_length=1,
        description="Mandatory ticker symbol (e.g. btc_usd, eth_usd)",
        examples=["btc_usd", "eth_usd"],
    ),
    service: PriceService = Depends(get_price_service),
) -> PriceResponse:
    """Retrieve the single latest recorded price for the given ticker."""
    try:
        record = await service.get_latest_price(ticker=ticker)
        return PriceResponse.model_validate(record)
    except PriceNotFoundError as not_found_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(not_found_err),
        ) from not_found_err
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err


@router.get(
    "/filter",
    response_model=List[PriceResponse],
    summary="Get prices for a currency with date filter",
    description="Fetches price records for the specified ticker filtered by date range or UNIX timestamp boundaries.",
)
@router.get(
    "/date-range",
    response_model=List[PriceResponse],
    include_in_schema=False,
)
@router.get(
    "/by-date",
    response_model=List[PriceResponse],
    include_in_schema=False,
)
async def get_prices_by_date(
    ticker: str = Query(
        ...,
        min_length=1,
        description="Mandatory ticker symbol (e.g. btc_usd, eth_usd)",
        examples=["btc_usd", "eth_usd"],
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter start date/time (ISO 8601, e.g., '2026-10-14T00:00:00' or '2026-10-14')",
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter end date/time (ISO 8601, e.g., '2026-10-14T23:59:59' or '2026-10-14')",
    ),
    start_timestamp: Optional[int] = Query(
        None,
        ge=0,
        description="Filter start UNIX timestamp in seconds (e.g., 1791965000)",
    ),
    end_timestamp: Optional[int] = Query(
        None,
        ge=0,
        description="Filter end UNIX timestamp in seconds (e.g., 1791966000)",
    ),
    limit: Optional[int] = Query(
        1000,
        ge=1,
        le=10000,
        description="Maximum number of records to return",
    ),
    offset: Optional[int] = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
    service: PriceService = Depends(get_price_service),
) -> List[PriceResponse]:
    """Retrieve prices for a currency ticker filtered by start/end date or timestamps."""
    try:
        records = await service.get_prices_by_date(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            limit=limit,
            offset=offset,
        )
        return [PriceResponse.model_validate(r) for r in records]
    except InvalidDateRangeError as range_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(range_err),
        ) from range_err
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
