"""Health and readiness endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from openrange.api.db import get_session
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["system"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(db: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}
