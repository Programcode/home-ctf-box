"""Streaks HTTP routes: /api/streaks."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from openrange.api.auth.dependencies import CurrentUser, DbSession, require_permission
from openrange.api.auth.service import AuthError
from openrange.api.streaks import service
from openrange.api.users.models import User
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/streaks", tags=["streaks"])

# Admin freeze days ride settings:write, same as scoring admin ops:
# admins hold every permission, no other role does.
AdminUser = Annotated[User, Depends(require_permission("settings:write"))]


class PreferencesIn(BaseModel):
    tz: str | None = Field(default=None, min_length=1, max_length=64)
    weekly_anchor: int | None = Field(default=None, ge=0, le=6)
    reminders_enabled: bool | None = None
    freeze_date: date | None = None  # one self-service freeze; null clears it


class FreezeIn(BaseModel):
    date: date


@router.get("/me")
async def my_streaks(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    try:
        _profile, _state, view = await service.refresh(db, user_id=user.id)
    except service.StreakServiceError as exc:
        raise AuthError(exc.code, exc.status) from exc
    return view


@router.post("/me/preferences")
async def update_preferences(
    payload: PreferencesIn, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    try:
        profile = await service.set_preferences(
            db,
            user_id=user.id,
            tz=payload.tz,
            weekly_anchor=payload.weekly_anchor,
            reminders_enabled=payload.reminders_enabled,
            freeze_date_provided="freeze_date" in payload.model_fields_set,
            freeze_date=payload.freeze_date,
        )
    except service.StreakServiceError as exc:
        raise AuthError(exc.code, exc.status) from exc
    return {
        "user_id": str(profile.user_id),
        "tz": profile.tz,
        "weekly_anchor": profile.weekly_anchor,
        "freeze_date": profile.freeze_date.isoformat() if profile.freeze_date else None,
        "reminders_enabled": profile.reminders_enabled,
    }


@router.post("/freeze")
async def create_freeze(payload: FreezeIn, admin: AdminUser, db: DbSession) -> dict[str, Any]:
    freeze, created = await service.add_freeze(db, day=payload.date, admin_user_id=admin.id)
    return {
        "freeze_date": freeze.freeze_date.isoformat(),
        "created_by": str(freeze.created_by) if freeze.created_by else None,
        "created": created,
    }
