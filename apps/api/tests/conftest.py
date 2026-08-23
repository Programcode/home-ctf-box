"""Integration test fixtures: real Postgres, real app, no mocks."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

TEST_DB_URL = "postgresql+asyncpg://openrange:openrange@localhost:15432/openrange_test"

TABLES = [
    "certificates",
    "hint_events",
    "notes",
    "quiz_attempts",
    "section_progress",
    "enrollments",
    "user_roles",
    "roles",
    "sessions",
    "recovery_codes",
    "mfa_factors",
    "password_resets",
    "email_verifications",
    "login_attempts",
    "api_tokens",
    "users",
]


@pytest.fixture(scope="session", autouse=True)
def _env() -> None:
    os.environ["OPENRANGE_DATABASE_URL"] = TEST_DB_URL
    os.environ.setdefault("OPENRANGE_ENV", "dev")


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """A fresh engine per test: asyncpg connections bind to one event loop."""
    from openrange.api.db import dispose_engine, init_engine

    os.environ["OPENRANGE_DATABASE_URL"] = TEST_DB_URL
    init_engine(TEST_DB_URL)
    from openrange.api.db import engine

    assert engine is not None
    yield engine
    await dispose_engine()


@pytest.fixture(autouse=True)
async def _reset_db(db_engine: AsyncEngine) -> AsyncIterator[None]:
    yield
    async with db_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(TABLES)} CASCADE"))
    # Rate-limit counters must not leak between tests.
    from openrange.api.auth import ratelimit

    try:
        await ratelimit._redis().flushdb()
        await ratelimit._redis().aclose()
    except Exception as exc:  # pragma: no cover - redis optional in unit runs
        print(f"note: could not flush redis between tests ({exc.__class__.__name__})")
    ratelimit._client = None


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
