"""Event HTTP routes: /api/events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter
from openrange.api.auth.dependencies import CurrentUser, DbSession
from openrange.api.auth.service import AuthError
from openrange.api.events import service as eventsvc
from openrange.api.events.models import Event
from openrange.api.teams import service as teamsvc
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/events", tags=["events"])

SLUG_PATTERN = r"^[a-z0-9-]{3,64}$"


class EventCreateIn(BaseModel):
    slug: str = Field(pattern=SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=128)
    starts_at: datetime
    ends_at: datetime
    registration_close_at: datetime | None = None
    visibility: str = "public"
    scoring_model: Literal["dynamic", "static"] = "static"
    dynamic_weight: int = Field(default=100, ge=1, le=10_000)
    team_size_min: int = Field(default=1, ge=1)
    team_size_max: int = Field(default=4, ge=1, le=32)
    scoreboard_freeze_at: datetime | None = None
    content_pool: list[str] = Field(default_factory=list)


class EventUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    registration_close_at: datetime | None = None
    scoring_model: Literal["dynamic", "static"] | None = None
    dynamic_weight: int | None = Field(default=None, ge=1, le=10_000)
    team_size_min: int | None = Field(default=None, ge=1)
    team_size_max: int | None = Field(default=None, ge=1, le=32)
    scoreboard_freeze_at: datetime | None = None
    content_pool: list[str] | None = None


class RegistrationIn(BaseModel):
    kind: Literal["user", "team"]
    team_name: str | None = None


def public_event(event: Event) -> dict[str, Any]:
    return {
        "slug": event.slug,
        "name": event.name,
        "starts_at": event.starts_at.isoformat(),
        "ends_at": event.ends_at.isoformat(),
        "registration_close_at": (
            event.registration_close_at.isoformat() if event.registration_close_at else None
        ),
        "visibility": event.visibility,
        "scoring_model": event.scoring_model,
        "dynamic_weight": event.dynamic_weight,
        "team_size_min": event.team_size_min,
        "team_size_max": event.team_size_max,
        "scoreboard_freeze_at": (
            event.scoreboard_freeze_at.isoformat() if event.scoreboard_freeze_at else None
        ),
        "content_pool": list(event.content_pool),
        "created_by": str(event.created_by) if event.created_by else None,
    }


async def _event_or_404(db: DbSession, slug: str) -> Event:
    event = await eventsvc.get_event_by_slug(db, slug)
    if event is None:
        raise AuthError("unknown event", 404)
    return event


@router.post("", status_code=201)
async def create_event(payload: EventCreateIn, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    event = await eventsvc.create_event(
        db,
        creator=user,
        slug=payload.slug,
        name=payload.name,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        registration_close_at=payload.registration_close_at,
        visibility=payload.visibility,
        scoring_model=payload.scoring_model,
        dynamic_weight=payload.dynamic_weight,
        team_size_min=payload.team_size_min,
        team_size_max=payload.team_size_max,
        scoreboard_freeze_at=payload.scoreboard_freeze_at,
        content_pool=payload.content_pool,
    )
    return public_event(event)


@router.get("")
async def list_events(user: CurrentUser, db: DbSession) -> list[dict[str, Any]]:
    events = await eventsvc.list_visible_events(db, user)
    return [public_event(e) for e in events]


@router.patch("/{slug}")
async def update_event(
    slug: str, payload: EventUpdateIn, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    event = await _event_or_404(db, slug)
    await eventsvc.ensure_builder(db, user, visibility=event.visibility)
    updated = await eventsvc.update_event(
        db,
        event,
        name=payload.name,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        registration_close_at=payload.registration_close_at,
        scoring_model=payload.scoring_model,
        dynamic_weight=payload.dynamic_weight,
        team_size_min=payload.team_size_min,
        team_size_max=payload.team_size_max,
        scoreboard_freeze_at=payload.scoreboard_freeze_at,
        content_pool=payload.content_pool,
    )
    return public_event(updated)


@router.get("/{slug}")
async def get_event(slug: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    event = await _event_or_404(db, slug)
    if not await eventsvc.can_view_or_admin(db, event, user):
        raise AuthError("unknown event", 404)
    return public_event(event)


@router.post("/{slug}/registrations", status_code=201)
async def register(
    slug: str, payload: RegistrationIn, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    event = await _event_or_404(db, slug)
    if not await eventsvc.can_view_or_admin(db, event, user):
        raise AuthError("unknown event", 404)
    team = None
    if payload.team_name is not None:
        team = await teamsvc.get_team_by_name(db, payload.team_name)
        if team is None:
            raise AuthError("unknown team", 404)
    row = await eventsvc.register(db, event, user=user, kind=payload.kind, team=team)
    return {
        "slug": event.slug,
        "kind": row.kind,
        "registered_at": row.registered_at.isoformat(),
    }


@router.get("/{slug}/scoreboard")
async def scoreboard(slug: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    event = await _event_or_404(db, slug)
    if not await eventsvc.can_view_or_admin(db, event, user):
        raise AuthError("unknown event", 404)
    return await eventsvc.get_scoreboard(db, event)


@router.post("/{slug}/scoreboard/refresh")
async def refresh_scoreboard(slug: str, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    event = await _event_or_404(db, slug)
    await eventsvc.ensure_builder(db, user, visibility=event.visibility)
    return await eventsvc.refresh_scoreboard(db, event)


__all__ = ["router"]
