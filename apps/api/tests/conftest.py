"""Integration test fixtures: real Postgres, real app, no mocks."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

TEST_DB_URL = os.environ.get(
    "OPENRANGE_TEST_DATABASE_URL",
    "postgresql+asyncpg://openrange:openrange@localhost:15432/openrange_test",
)
_TEST_DB_DSN = TEST_DB_URL.replace("+asyncpg", "")

TABLES = [
    "event_registrations",
    "event_solves",
    "event_team_sessions",
    "event_scoreboards",
    "events",
    "team_members",
    "teams",
    "vpn_leases",
    "vpn_devices",
    "publish_events",
    "draft_reviews",
    "drafts",
    "announcements",
    "notification_prefs",
    "notifications",
    "email_outbox",
    "certificates",
    "hint_events",
    "notes",
    "quiz_attempts",
    "section_progress",
    "enrollments",
    "assignment_progress_cache",
    "assignments",
    "cohort_members",
    "cohorts",
    "org_invites",
    "org_members",
    "organizations",
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
    "score_adjustments",
    "score_events",
    "user_achievements",
    "achievements_catalog",
    "leaderboard_snapshots",
    "anti_cheat_signals",
]


@pytest.fixture(scope="session", autouse=True)
def _env() -> None:
    os.environ["OPENRANGE_DATABASE_URL"] = TEST_DB_URL
    os.environ.setdefault("OPENRANGE_ENV", "dev")


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Engine for tests that run raw SQL; disposal happens in _reset_db."""
    from openrange.api.db import init_engine

    os.environ["OPENRANGE_DATABASE_URL"] = TEST_DB_URL
    init_engine(TEST_DB_URL)
    from openrange.api.db import engine

    assert engine is not None
    yield engine


async def _db_reachable() -> bool:
    """Cheap probe so unit-only runs (no Postgres service) skip resets."""
    import asyncpg

    try:
        conn = await asyncio.wait_for(asyncpg.connect(_TEST_DB_DSN, timeout=2), timeout=3)
    except Exception:
        return False
    await conn.close()
    return True


@pytest.fixture(autouse=True)
async def _reset_db() -> AsyncIterator[None]:
    yield
    if await _db_reachable():
        from openrange.api.db import dispose_engine, init_engine

        init_engine(TEST_DB_URL)
        from openrange.api.db import engine

        assert engine is not None
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {', '.join(TABLES)} CASCADE"))
        await dispose_engine()
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
