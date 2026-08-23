"""Database engine and session wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator

from openrange.api.config import get_settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str | None = None, echo: bool = False) -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        database_url or settings.database_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None, echo: bool = False) -> None:
    global engine, session_factory
    engine = build_engine(database_url, echo)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def dispose_engine() -> None:
    if engine is not None:
        await engine.dispose()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional session."""
    if session_factory is None:
        init_engine()
    assert session_factory is not None
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
