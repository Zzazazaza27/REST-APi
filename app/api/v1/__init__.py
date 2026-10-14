"""API v1 router."""

from fastapi import APIRouter
from app.api.v1.endpoints import router as prices_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(prices_router)

__all__ = ["api_v1_router"]
