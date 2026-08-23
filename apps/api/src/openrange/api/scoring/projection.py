"""Deterministic score projections (plan Phase 9).

Pure functions: no database, no clock, no randomness. Feeding the same
set of events in any order always yields identical output, so scores can
be replayed from the ledger at any time.

Contract (do not change without a migration plan for snapshots):

- Competitive points come from ``room_solve``, ``first_blood``,
  ``achievement`` and ``adjustment`` events.
- ``xp_award`` events contribute XP only and never touch points.
- ``hint_cost`` events never touch points; they subtract their ``xp``
  amount from the user's XP total, which floors at zero.
- Leaderboard rows sort by points sum descending, then earliest
  last-event timestamp ascending (reaching a total sooner ranks
  higher), then user_id ascending.
- First blood per ``ref_slug`` is attributed to the earliest
  ``first_blood`` event; equal timestamps break on user_id ascending.
  Duplicate first_blood events for one ref still add their points to
  the ledger sums, but only the attributed holder counts as holder.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Protocol

POINTS_KINDS: Final[frozenset[str]] = frozenset(
    {"room_solve", "first_blood", "achievement", "adjustment"}
)
XP_KINDS: Final[frozenset[str]] = frozenset({"room_solve", "xp_award", "achievement"})
HINT_COST: Final[str] = "hint_cost"
FIRST_BLOOD: Final[str] = "first_blood"

# Sort floor for users with no events; aware to compare with timestamptz values.
_SORT_FLOOR: Final[datetime] = datetime.max.replace(tzinfo=UTC)


class ScoreEventLike(Protocol):
    """Structural type satisfied by ORM rows and test fixtures alike."""

    user_id: uuid.UUID
    kind: str
    ref_slug: str | None
    points: int
    xp: int
    created_at: datetime

    @property
    def meta(self) -> Mapping[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class MeScore:
    user_id: uuid.UUID
    points: int
    xp: int
    event_count: int
    tracks: dict[str, int]
    first_blood_refs: tuple[str, ...]
    last_event_at: datetime | None


@dataclass(frozen=True, slots=True)
class LeaderboardRow:
    rank: int
    user_id: uuid.UUID
    points: int
    xp: int
    event_count: int
    last_event_at: datetime | None
    first_bloods: int


@dataclass(slots=True)
class _UserAggregate:
    points: int = 0
    xp_raw: int = 0
    event_count: int = 0
    last_event_at: datetime | None = None
    tracks: dict[str, int] = field(default_factory=dict)
    first_blood_refs: set[str] = field(default_factory=set)

    @property
    def xp(self) -> int:
        return max(0, self.xp_raw)


def _track_of(event: ScoreEventLike) -> str:
    meta = event.meta or {}
    track = meta.get("track")
    return str(track) if track else "general"


def _aggregate(events: Iterable[ScoreEventLike]) -> dict[uuid.UUID, _UserAggregate]:
    users: dict[uuid.UUID, _UserAggregate] = {}
    holders: dict[str, tuple[datetime, uuid.UUID]] = {}

    for ev in events:
        agg = users.setdefault(ev.user_id, _UserAggregate())
        agg.event_count += 1
        if agg.last_event_at is None or ev.created_at > agg.last_event_at:
            agg.last_event_at = ev.created_at
        if ev.kind in POINTS_KINDS:
            agg.points += ev.points
            agg.tracks[_track_of(ev)] = agg.tracks.get(_track_of(ev), 0) + ev.points
        if ev.kind in XP_KINDS:
            agg.xp_raw += ev.xp
        elif ev.kind == HINT_COST:
            agg.xp_raw -= ev.xp
        if ev.kind == FIRST_BLOOD and ev.ref_slug is not None:
            key = (ev.created_at, ev.user_id)
            current = holders.get(ev.ref_slug)
            if current is None or key < (current[0], current[1]):
                holders[ev.ref_slug] = (ev.created_at, ev.user_id)

    for ref, (_at, user_id) in holders.items():
        users[user_id].first_blood_refs.add(ref)
    return users


def project_leaderboard(
    events: Iterable[ScoreEventLike], *, metric: str = "points"
) -> list[LeaderboardRow]:
    """Full leaderboard with documented tiebreaks applied.

    ``metric`` picks the ranking column: competitive ``points`` (default)
    or ``xp`` for learning-side boards such as paths. Tiebreaks are
    unchanged: metric sum desc, earliest last event asc, user_id asc.
    """
    if metric not in {"points", "xp"}:
        raise ValueError(f"unknown metric {metric}")

    def sort_key(user_id: uuid.UUID, agg: _UserAggregate) -> tuple[Any, ...]:
        value = -agg.points if metric == "points" else -agg.xp
        return (value, agg.last_event_at or _SORT_FLOOR, user_id)

    users = _aggregate(events)
    ordered = sorted(users.items(), key=lambda item: sort_key(item[0], item[1]))
    return [
        LeaderboardRow(
            rank=position,
            user_id=user_id,
            points=agg.points,
            xp=agg.xp,
            event_count=agg.event_count,
            last_event_at=agg.last_event_at,
            first_bloods=len(agg.first_blood_refs),
        )
        for position, (user_id, agg) in enumerate(ordered, start=1)
    ]


def project_me(events: Iterable[ScoreEventLike], user_id: uuid.UUID) -> MeScore:
    """Totals and per-track breakdown for one user.

    First-blood attribution is global: the full event set decides each
    ref's holder before we read off this user's slice.
    """
    users = _aggregate(events)
    agg = users.get(user_id, _UserAggregate())
    return MeScore(
        user_id=user_id,
        points=agg.points,
        xp=agg.xp,
        event_count=agg.event_count,
        tracks=dict(sorted(agg.tracks.items())),
        first_blood_refs=tuple(sorted(agg.first_blood_refs)),
        last_event_at=agg.last_event_at,
    )
