"""FastAPI dependency injection providers."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.price_repository import PriceRepository
from app.services.price_service import PriceService


def get_price_repository(db: AsyncSession = Depends(get_db)) -> PriceRepository:
    """Dependency provider for PriceRepository with injected database session."""
    return PriceRepository(session=db)


def get_price_service(
    repo: PriceRepository = Depends(get_price_repository),
) -> PriceService:
    """Dependency provider for PriceService with injected repository."""
    return PriceService(repository=repo)
