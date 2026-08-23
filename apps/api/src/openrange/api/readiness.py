"""Deep readiness probe with component checks and 200/503 semantics.

/api/readyz answers one question: can this process serve real traffic
right now? Every component check reports individually so operators can
see which dependency is unhappy instead of a bare failure.

Check outcomes are fail-closed except for two documented cases:
- an unreachable Redis fails the probe (sessions/rate limits depend on
  it in cluster mode), but a missing Redis *client config* degrades to
  "unknown" because dev editions legitimately run without Redis;
- missing Alembic sources (packaged images ship without migration
  scripts) cannot be verified, so the head-match check reports ok=True
  with a note rather than bricking readiness.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Annotated, Any

from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, Response
from openrange.api.db import get_session
from openrange.api.learning.content import content_root
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

_CHECK_TIMEOUT_SECONDS = 2.0


async def _check_database(db: AsyncSession) -> dict[str, Any]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        return {"ok": False, "detail": f"{exc.__class__.__name__}"}
    return {"ok": True}


async def _check_redis() -> dict[str, Any]:
    try:
        from openrange.api.auth.ratelimit import _redis

        client = _redis()
        await asyncio.wait_for(client.ping(), timeout=_CHECK_TIMEOUT_SECONDS)
    except ImportError:
        # Dev editions may run without Redis configured at all.
        return {"ok": True, "detail": "redis not configured; skipped"}
    except Exception as exc:
        return {"ok": False, "detail": f"{exc.__class__.__name__}"}
    return {"ok": True}


def _check_content_dir() -> dict[str, Any]:
    root = content_root()
    if not root.is_dir() or not os.access(root, os.R_OK):
        return {"ok": False, "detail": f"{root} is not a readable directory"}
    return {"ok": True, "detail": str(root)}


def _alembic_dir() -> Path:
    # apps/api/src/openrange/api/readiness.py -> apps/api/alembic in a checkout.
    return Path(__file__).resolve().parents[3] / "alembic"


async def _check_migrations(db: AsyncSession) -> dict[str, Any]:
    directory = _alembic_dir()
    if not (directory / "versions").is_dir():
        return {
            "ok": True,
            "detail": f"alembic sources unavailable at {directory}; head match skipped",
        }
    try:
        heads = sorted(set(ScriptDirectory(str(directory)).get_heads()))
        rows = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalars().all()
    except Exception as exc:
        return {"ok": False, "detail": f"{exc.__class__.__name__}"}
    applied = sorted(set(rows))
    return {
        "ok": applied == heads,
        "head": heads,
        "applied": applied,
    }


@router.get("/readyz")
async def readyz(db: Annotated[AsyncSession, Depends(get_session)]) -> Response:
    checks = {
        "database": await _check_database(db),
        "redis": await _check_redis(),
        "content_dir": _check_content_dir(),
        "migrations": await _check_migrations(db),
    }
    ready = all(bool(check["ok"]) for check in checks.values())
    body = {"status": "ready" if ready else "unavailable", "checks": checks}
    return Response(
        content=json.dumps(body),
        status_code=200 if ready else 503,
        media_type="application/json",
    )


__all__ = ["readyz", "router"]
