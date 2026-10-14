"""FastAPI main application entrypoint."""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import get_settings
from app.database import Base, get_db_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    logger.info("Initializing application resources...")
    db_manager = get_db_manager()

    # Automatically create database tables if they do not exist
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema verified/created.")

    yield

    logger.info("Closing application resources...")
    await db_manager.close()
    logger.info("Application shutdown complete.")


def create_application() -> FastAPI:
    """Application factory for FastAPI app instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "REST API for retrieving cryptocurrency index prices (BTC/USD, ETH/USD) "
            "polled periodically from Deribit exchange."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get(
        "/health",
        tags=["System"],
        summary="Service healthcheck",
        status_code=status.HTTP_200_OK,
    )
    async def health_check() -> JSONResponse:
        return JSONResponse(
            content={
                "status": "healthy",
                "service": settings.PROJECT_NAME,
                "version": settings.VERSION,
            }
        )

    # Include root API router
    app.include_router(api_router)

    return app


app = create_application()
