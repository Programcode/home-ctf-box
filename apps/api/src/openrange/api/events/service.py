"""Event domain logic: builder, registration, solve ingestion, scoreboards.

Scoring contract (do not change without migrating stored points):

- ``static`` model: points_awarded = task.points exactly.
- ``dynamic`` model decays with the global solve order n of the task
  inside the event. n counts every earlier solve of the same
  (room, task) by any subject:

      f(n) = round(base * start / (start + n * decay))

  start = event.dynamic_weight (default 100), decay = DYNAMIC_DECAY = 1.
  The first solver (n=0) earns the full base value.
- First blood: the first solver of a task earns a flat +10% bonus,
  rounded: bonus = round(points * FIRST_BLOOD_BONUS_PCT). It is folded
  into points_awarded and flagged first_blood=True. Exactly one subject
  per (event, room, task) can hold first blood.
- Ingestion is idempotent per (event, subject, room, task); replaying
  returns the stored row unchanged.

Fair attribution: record_event_solve attributes an individual user's
solve to their current team only while that team has an active
event_team_sessions row whose started_at is not after the solve time.
Rows are immutable: switching teams mid-event leaves earlier solves
with the old team and sends later solves to the new team.

Scoreboards rank by points desc, then earliest cumulative solve time
asc (each subject's last solve moment; reaching a total sooner ranks
higher), then name asc. After scoreboard_freeze_at the frozen snapshot
in event_scoreboards is served untouched until an explicit refresh.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from openrange.api.auth.service import AuthError
from openrange.api.events.models import (
    Event,
    EventRegistration,
    EventScoreboard,
    EventSolve,
    EventTeamSession,
)
from openrange.api.orgs import service as orgsvc
from openrange.api.teams import service as teamsvc
from openrange.api.teams.models import Team, TeamMember
from openrange.api.users.models import User
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

PUBLIC_VISIBILITY = "public"
ORG_PREFIX = "org:"
DYNAMIC_DECAY = 1
FIRST_BLOOD_BONUS_PCT = 0.10

# Sort floor for subjects without solves; aware so it compares against
# timestamptz values.
_SORT_FLOOR = datetime.max.replace(tzinfo=UTC)


def _now() -> datetime:
    return datetime.now(UTC)


def dynamic_points(base: int, start: int, order: int) -> int:
    """f(n) = round(base * start / (start + n * decay)); n >= 0."""
    return round(base * start / (start + order * DYNAMIC_DECAY))


def first_blood_bonus(points: int) -> int:
    return round(points * FIRST_BLOOD_BONUS_PCT)


def org_of_visibility(visibility: str) -> str | None:
    """Org name for 'org:<name>' visibility, else None."""
    if visibility.startswith(ORG_PREFIX):
        return visibility[len(ORG_PREFIX) :]
    return None


async def get_event_by_slug(db: AsyncSession, slug: str) -> Event | None:
    return (await db.execute(select(Event).where(Event.slug == slug))).scalar_one_or_none()


async def ensure_builder(db: AsyncSession, user: User, *, visibility: str) -> None:
    """Admin passes always; otherwise org owners may build their own events."""
    if user.has_permission("settings:write"):
        return
    org_name = org_of_visibility(visibility)
    if org_name is None:
        raise AuthError("requires the settings:write permission", 403)
    # Raises 404 for non-members and 403 for non-owner members.
    await orgsvc.require_role(db, user.id, org_name, orgsvc.OWNER)


async def create_event(
    db: AsyncSession,
    *,
    creator: User,
    slug: str,
    name: str,
    starts_at: datetime,
    ends_at: datetime,
    registration_close_at: datetime | None = None,
    visibility: str = PUBLIC_VISIBILITY,
    scoring_model: str = "static",
    dynamic_weight: int = 100,
    team_size_min: int = 1,
    team_size_max: int = 4,
    scoreboard_freeze_at: datetime | None = None,
    content_pool: list[str] | None = None,
) -> Event:
    if scoring_model not in ("dynamic", "static"):
        raise AuthError("scoring_model must be dynamic or static", 422)
    if visibility != PUBLIC_VISIBILITY and org_of_visibility(visibility) is None:
        raise AuthError("visibility must be 'public' or 'org:<name>'", 422)
    if ends_at <= starts_at:
        raise AuthError("ends_at must be after starts_at", 422)
    if team_size_max < team_size_min:
        raise AuthError("team_size_max must be >= team_size_min", 422)
    if await get_event_by_slug(db, slug) is not None:
        raise AuthError("event slug already taken", 409)
    await ensure_builder(db, creator, visibility=visibility)
    event = Event(
        slug=slug,
        name=name,
        starts_at=starts_at,
        ends_at=ends_at,
        registration_close_at=registration_close_at,
        visibility=visibility,
        scoring_model=scoring_model,
        dynamic_weight=dynamic_weight,
        team_size_min=team_size_min,
        team_size_max=team_size_max,
        scoreboard_freeze_at=scoreboard_freeze_at,
        content_pool=content_pool or [],
        created_by=creator.id,
    )
    db.add(event)
    await db.flush()
    return event


async def update_event(db: AsyncSession, event: Event, **fields: Any) -> Event:
    """Apply non-None fields; revalidates cross-field invariants."""

    def pick(key: str, current: Any) -> Any:
        value = fields.get(key)
        return current if value is None else value

    merged = {
        "starts_at": pick("starts_at", event.starts_at),
        "ends_at": pick("ends_at", event.ends_at),
        "team_size_min": pick("team_size_min", event.team_size_min),
        "team_size_max": pick("team_size_max", event.team_size_max),
    }
    if merged["ends_at"] <= merged["starts_at"]:
        raise AuthError("ends_at must be after starts_at", 422)
    if merged["team_size_max"] < merged["team_size_min"]:
        raise AuthError("team_size_max must be >= team_size_min", 422)
    for field_name in (
        "name",
        "starts_at",
        "ends_at",
        "registration_close_at",
        "scoring_model",
        "dynamic_weight",
        "team_size_min",
        "team_size_max",
        "scoreboard_freeze_at",
        "content_pool",
    ):
        value = fields.get(field_name)
        if value is not None:
            setattr(event, field_name, value)
    await db.flush()
    return event


async def can_view(db: AsyncSession, event: Event, user_id: uuid.UUID) -> bool:
    org_name = org_of_visibility(event.visibility)
    if org_name is None:
        return True
    org = await orgsvc.get_org_by_slug(db, org_name)
    if org is None:
        return False
    return await orgsvc.get_membership(db, org.id, user_id) is not None


async def can_view_or_admin(db: AsyncSession, event: Event, user: User) -> bool:
    """Site admins bypass visibility; everyone else needs membership."""
    if user.has_permission("settings:write"):
        return True
    return await can_view(db, event, user.id)


async def list_visible_events(db: AsyncSession, user: User | None) -> list[Event]:
    """Public plus viewer-visible org events that have not ended yet."""
    stmt = select(Event).where(Event.ends_at > _now()).order_by(Event.starts_at.asc())
    events = list((await db.execute(stmt)).scalars().all())
    if user is None:
        return [e for e in events if e.visibility == PUBLIC_VISIBILITY]
    visible: list[Event] = []
    for event in events:
        if await can_view_or_admin(db, event, user):
            visible.append(event)
    return visible


# --- Registration ------------------------------------------------------------


async def register(
    db: AsyncSession,
    event: Event,
    *,
    user: User,
    kind: str,
    team: Team | None = None,
) -> EventRegistration:
    """Register the caller themself or (captains only) their team."""
    close_at = event.registration_close_at or event.ends_at
    if _now() >= close_at:
        raise AuthError("registration is closed", 409)
    if kind == "user":
        existing = (
            await db.execute(
                select(EventRegistration).where(
                    EventRegistration.event_id == event.id,
                    EventRegistration.kind == "user",
                    EventRegistration.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise AuthError("already registered", 409)
        row = EventRegistration(event_id=event.id, kind="user", user_id=user.id)
        db.add(row)
        await db.flush()
        return row
    if kind != "team" or team is None:
        raise AuthError("kind must be 'user' or 'team'", 422)
    membership = await teamsvc.get_membership(db, team.id, user.id)
    if membership is None:
        raise AuthError("unknown team", 404)
    if membership.capability != teamsvc.CAPTAIN:
        raise AuthError("requires the team captain capability", 403)
    size = await teamsvc.member_count(db, team.id)
    if size < event.team_size_min:
        raise AuthError(f"team needs at least {event.team_size_min} members", 409)
    if size > event.team_size_max:
        raise AuthError(f"team allows at most {event.team_size_max} members", 409)
    existing = (
        await db.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event.id,
                EventRegistration.kind == "team",
                EventRegistration.team_id == team.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AuthError("already registered", 409)
    row = EventRegistration(event_id=event.id, kind="team", team_id=team.id)
    db.add(row)
    await db.flush()
    return row


# --- Shared event sessions ---------------------------------------------------


async def start_team_session(
    db: AsyncSession, event: Event, team_id: uuid.UUID
) -> EventTeamSession:
    """Activate (or reactivate) the team's shared session for the event.

    Reactivation preserves the original started_at: every solve accepted
    afterwards was necessarily made after that start, so attribution
    stays monotonic even across leave/rejoin churn.
    """
    session = (
        await db.execute(
            select(EventTeamSession).where(
                EventTeamSession.event_id == event.id,
                EventTeamSession.team_id == team_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        session = EventTeamSession(event_id=event.id, team_id=team_id, active=True)
        db.add(session)
    else:
        session.active = True
        session.ended_at = None
    await db.flush()
    return session


async def end_team_session(db: AsyncSession, event: Event, team_id: uuid.UUID) -> None:
    session = (
        await db.execute(
            select(EventTeamSession).where(
                EventTeamSession.event_id == event.id,
                EventTeamSession.team_id == team_id,
            )
        )
    ).scalar_one_or_none()
    if session is not None and session.active:
        session.active = False
        session.ended_at = _now()
        await db.flush()


async def resolve_subject(
    db: AsyncSession, event: Event, user_id: uuid.UUID, at: datetime
) -> tuple[str, uuid.UUID]:
    """(kind, id) a solve at time ``at`` attributes to.

    Picks the most recently started active team session containing the
    user; falls back to the individual user. Sessions that started after
    the solve never apply, which is what keeps retroactive reattribution
    impossible.
    """
    session = (
        await db.execute(
            select(EventTeamSession)
            .join(TeamMember, TeamMember.team_id == EventTeamSession.team_id)
            .where(
                EventTeamSession.event_id == event.id,
                EventTeamSession.active,
                EventTeamSession.started_at <= at,
                TeamMember.user_id == user_id,
            )
            .order_by(EventTeamSession.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if session is not None:
        return "team", session.team_id
    return "user", user_id


# --- Solve ingestion ---------------------------------------------------------


async def record_event_solve(
    db: AsyncSession,
    *,
    event: Event,
    actor_user_id: uuid.UUID,
    room_slug: str,
    task_slug: str,
    task_points: int,
    solved_at: datetime | None = None,
) -> tuple[EventSolve, bool]:
    """Internal ingestion API. Returns ``(solve, created)``.

    Points are computed at insert time from the event's scoring model
    and never recomputed. Idempotent per (event, subject, room, task):
    replaying returns the stored row with created=False.
    """
    at = solved_at or _now()
    if event.scoreboard_freeze_at is not None and at >= event.scoreboard_freeze_at:
        raise AuthError("event scoreboard is frozen", 409)
    subject_kind, subject_id = await resolve_subject(db, event, actor_user_id, at)
    order = int(
        (
            await db.execute(
                select(func.count())
                .select_from(EventSolve)
                .where(
                    EventSolve.event_id == event.id,
                    EventSolve.room_slug == room_slug,
                    EventSolve.task_slug == task_slug,
                )
            )
        ).scalar_one()
    )
    first = order == 0
    if event.scoring_model == "dynamic":
        value = dynamic_points(task_points, event.dynamic_weight, order)
    else:
        value = task_points
    points = value + first_blood_bonus(value) if first else value
    stmt = (
        pg_insert(EventSolve)
        .values(
            event_id=event.id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            room_slug=room_slug,
            task_slug=task_slug,
            points_awarded=points,
            first_blood=first,
            solved_at=at,
        )
        .on_conflict_do_nothing(
            index_elements=[
                EventSolve.__table__.c.event_id,
                EventSolve.__table__.c.subject_kind,
                EventSolve.__table__.c.subject_id,
                EventSolve.__table__.c.room_slug,
                EventSolve.__table__.c.task_slug,
            ]
        )
        .returning(EventSolve.id)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        existing = (
            await db.execute(
                select(EventSolve).where(
                    EventSolve.event_id == event.id,
                    EventSolve.subject_kind == subject_kind,
                    EventSolve.subject_id == subject_id,
                    EventSolve.room_slug == room_slug,
                    EventSolve.task_slug == task_slug,
                )
            )
        ).scalar_one()
        return existing, False
    await db.flush()
    solve = await db.get(EventSolve, row)
    assert solve is not None
    return solve, True


# --- Scoreboards ---------------------------------------------------------------


async def compute_rows(db: AsyncSession, event: Event) -> list[dict[str, Any]]:
    """Live ranked rows; pure function of stored solves plus names."""
    solves = list(
        (
            await db.execute(
                select(EventSolve)
                .where(EventSolve.event_id == event.id)
                .order_by(EventSolve.solved_at.asc(), EventSolve.id.asc())
            )
        ).scalars()
    )
    aggregates: dict[tuple[str, uuid.UUID], dict[str, Any]] = {}
    for solve in solves:
        key = (solve.subject_kind, solve.subject_id)
        agg = aggregates.setdefault(key, {"points": 0, "solve_count": 0, "last_solve_at": None})
        agg["points"] += solve.points_awarded
        agg["solve_count"] += 1
        if agg["last_solve_at"] is None or solve.solved_at > agg["last_solve_at"]:
            agg["last_solve_at"] = solve.solved_at

    user_ids = [sid for kind, sid in aggregates if kind == "user"]
    team_ids = [sid for kind, sid in aggregates if kind == "team"]
    names: dict[uuid.UUID, str] = {}
    if user_ids:
        for user_row in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars():
            names[user_row.id] = user_row.username
    if team_ids:
        for team_row in (await db.execute(select(Team).where(Team.id.in_(team_ids)))).scalars():
            names[team_row.id] = team_row.display_name or team_row.name

    def sort_key(kind: str, subject_id: uuid.UUID, agg: dict[str, Any]) -> tuple[Any, ...]:
        name = names.get(subject_id, str(subject_id))
        return (-agg["points"], agg["last_solve_at"] or _SORT_FLOOR, name)

    ordered = sorted(aggregates.items(), key=lambda item: sort_key(item[0][0], item[0][1], item[1]))
    return [
        {
            "rank": position,
            "subject_kind": kind,
            "subject_id": str(subject_id),
            "name": names.get(subject_id, str(subject_id)),
            "points": agg["points"],
            "solve_count": agg["solve_count"],
            "last_solve_at": (agg["last_solve_at"].isoformat() if agg["last_solve_at"] else None),
        }
        for position, ((kind, subject_id), agg) in enumerate(ordered, start=1)
    ]


def _is_frozen(event: Event, at: datetime | None = None) -> bool:
    freeze = event.scoreboard_freeze_at
    if freeze is None:
        return False
    return (at or _now()) >= freeze


async def get_scoreboard(db: AsyncSession, event: Event) -> dict[str, Any]:
    """Serve live rows pre-freeze, the frozen snapshot post-freeze.

    The snapshot is written once by the first post-freeze request and is
    never updated by reads; only refresh_scoreboard replaces it.
    """
    if not _is_frozen(event):
        return {"frozen": False, "computed_at": None, "rows": await compute_rows(db, event)}
    existing = (
        await db.execute(select(EventScoreboard).where(EventScoreboard.event_id == event.id))
    ).scalar_one_or_none()
    if existing is None:
        rows = await compute_rows(db, event)
        stmt = (
            pg_insert(EventScoreboard)
            .values(event_id=event.id, payload=rows, computed_at=_now())
            .on_conflict_do_nothing(index_elements=[EventScoreboard.__table__.c.event_id])
        )
        await db.execute(stmt)
        await db.flush()
        existing = (
            await db.execute(select(EventScoreboard).where(EventScoreboard.event_id == event.id))
        ).scalar_one()
    return {
        "frozen": True,
        "computed_at": existing.computed_at.isoformat(),
        "rows": list(existing.payload),
    }


async def refresh_scoreboard(db: AsyncSession, event: Event) -> dict[str, Any]:
    """Recompute and overwrite the snapshot (admin/org-owner action)."""
    rows = await compute_rows(db, event)
    computed_at = _now()
    stmt = (
        pg_insert(EventScoreboard)
        .values(event_id=event.id, payload=rows, computed_at=computed_at)
        .on_conflict_do_update(
            index_elements=[EventScoreboard.__table__.c.event_id],
            set_={"payload": rows, "computed_at": computed_at},
        )
    )
    await db.execute(stmt)
    await db.flush()
    return {
        "frozen": _is_frozen(event),
        "computed_at": computed_at.isoformat(),
        "rows": rows,
    }
