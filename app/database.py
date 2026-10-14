"""Database configuration and session management module."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


class DatabaseSessionManager:
    """Encapsulates async SQLAlchemy engine and session factory lifecycle."""

    def __init__(self, db_url: str, echo: bool = False):
        engine_kwargs = {
            "echo": echo,
            "future": True,
        }
        if "sqlite" not in db_url:
            engine_kwargs.update({
                "pool_pre_ping": True,
                "pool_size": 10,
                "max_overflow": 20,
            })
        self._engine: AsyncEngine = create_async_engine(
            db_url,
            **engine_kwargs,
        )
        self._session_maker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession]:
        return self._session_maker

    async def close(self) -> None:
        """Dispose of the database engine connection pool."""
        await self._engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager providing an isolated async session with automatic rollback on error."""
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Lazy-initialized database session manager factory function (to avoid global side-effects at import time)
_db_manager: DatabaseSessionManager = None


def get_db_manager() -> DatabaseSessionManager:
    """Retrieve or initialize the database session manager instance."""
    global _db_manager
    if _db_manager is None:
        settings = get_settings()
        _db_manager = DatabaseSessionManager(
            db_url=settings.async_database_url,
            echo=settings.DEBUG,
        )
    return _db_manager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding database sessions."""
    manager = get_db_manager()
    async with manager.session() as session:
        yield session
