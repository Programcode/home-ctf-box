"""Pure projection tests: replay determinism and documented tiebreaks.

No database: these run in the fast CI lane and prove that projections
are pure functions of the event multiset.
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from openrange.api.scoring.projection import (
    project_leaderboard,
    project_me,
)

BASE = datetime(2026, 8, 1, tzinfo=UTC)


@dataclass(slots=True)
class Ev:
    """Minimal stand-in for a score_events row."""

    user_id: uuid.UUID
    kind: str
    ref_slug: str | None
    points: int
    xp: int
    meta: dict[str, Any] | None
    created_at: datetime


def ev(
    user: int,
    kind: str,
    *,
    ref: str | None = None,
    points: int = 0,
    xp: int = 0,
    meta: dict[str, Any] | None = None,
    offset_seconds: float = 0,
) -> Ev:
    return Ev(
        user_id=_uid(user),
        kind=kind,
        ref_slug=ref,
        points=points,
        xp=xp,
        meta=meta,
        created_at=BASE + timedelta(seconds=offset_seconds),
    )


def _uid(n: int) -> uuid.UUID:
    return uuid.UUID(int=n)


def _freeze(payload: Any) -> str:
    return json.dumps(payload, default=str, sort_keys=True)


def _random_events(rng: random.Random) -> list[Ev]:
    """A mixed bag: ties everywhere, floors crossed, duplicate bloods."""
    kinds = ["room_solve", "xp_award", "hint_cost", "adjustment", "first_blood"]
    refs = ["room-a", "room-b", "room-c"]
    tracks = ["web", "crypto", None]
    users = [rng.randrange(6) for _ in range(60)]
    events: list[Ev] = []
    for i, user in enumerate(users):
        kind = rng.choice(kinds)
        if kind == "first_blood":
            events.append(ev(user, kind, ref=rng.choice(refs), points=25, offset_seconds=i % 3))
        elif kind == "room_solve":
            track = rng.choice(tracks)
            meta = {"track": track} if track else {}
            events.append(
                ev(
                    user,
                    kind,
                    ref=rng.choice(refs),
                    points=rng.randrange(-10, 120),
                    xp=rng.randrange(0, 60),
                    meta=meta or None,
                    offset_seconds=i % 5,
                )
            )
        elif kind == "xp_award":
            events.append(
                ev(user, kind, ref=rng.choice(refs), xp=rng.randrange(1, 80), offset_seconds=i % 4)
            )
        elif kind == "hint_cost":
            events.append(ev(user, kind, ref=None, xp=rng.randrange(1, 90), offset_seconds=i % 4))
        else:
            events.append(ev(user, kind, points=rng.randrange(-40, 40), offset_seconds=i % 4))
    return events


def _snapshot(events: list[Ev]) -> str:
    board = [asdict(r) for r in project_leaderboard(events)]
    mes = [_me_dict(project_me(events, _uid(u))) for u in range(6)]
    return _freeze({"board": board, "mes": mes})


def _me_dict(me: Any) -> dict[str, Any]:
    return {
        "user_id": str(me.user_id),
        "points": me.points,
        "xp": me.xp,
        "event_count": me.event_count,
        "tracks": me.tracks,
        "first_blood_refs": list(me.first_blood_refs),
        "last_event_at": me.last_event_at.isoformat() if me.last_event_at else None,
    }


def test_replay_determinism_under_shuffling() -> None:
    rng = random.Random(20260823)  # noqa: S311 - deterministic property test
    events = _random_events(rng)
    baseline = _snapshot(events)
    for iteration in range(100):
        shuffled = events[:]
        random.Random(iteration).shuffle(shuffled)  # noqa: S311 - deterministic property test
        assert _snapshot(shuffled) == baseline, f"iteration {iteration} diverged"


def test_leaderboard_ordering_and_tiebreaks() -> None:
    # Equal points: earlier last event ranks higher.
    events = [
        ev(1, "room_solve", ref="r", points=100, offset_seconds=10),
        ev(2, "room_solve", ref="r", points=100, offset_seconds=5),
    ]
    rows = project_leaderboard(events)
    assert [r.user_id for r in rows] == [_uid(2), _uid(1)]

    # Identical points and last-event time: lower user_id wins.
    events = [
        ev(9, "room_solve", ref="r", points=70, offset_seconds=5),
        ev(4, "room_solve", ref="r", points=70, offset_seconds=5),
    ]
    rows = project_leaderboard(events)
    assert [r.user_id for r in rows] == [_uid(4), _uid(9)]


def test_first_blood_precedence_ignores_input_order() -> None:
    early = ev(5, "first_blood", ref="room-x", points=25, offset_seconds=1)
    late = ev(7, "first_blood", ref="room-x", points=25, offset_seconds=9)
    tied = ev(3, "first_blood", ref="room-x", points=25, offset_seconds=1)

    # Earliest timestamp holds first blood regardless of input order.
    for ordering in ([early, late], [late, early]):
        assert project_me(ordering, _uid(5)).first_blood_refs == ("room-x",), ordering
        assert project_me(ordering, _uid(7)).first_blood_refs == (), ordering

    # Equal timestamps break on user_id ascending (3 beats 5).
    for ordering in ([tied, late, early], [late, early, tied], [tied, early]):
        assert project_me(ordering, _uid(3)).first_blood_refs == ("room-x",), ordering
        assert project_me(ordering, _uid(5)).first_blood_refs == (), ordering


def test_xp_and_competitive_score_stay_separated() -> None:
    events = [
        ev(1, "xp_award", ref="path-basics", xp=50),
        ev(1, "room_solve", ref="room-a", points=100, xp=10),
        ev(1, "hint_cost", xp=15),
    ]
    me = project_me(events, _uid(1))
    assert me.points == 100  # xp_award and hint_cost never touch points
    assert me.xp == 45  # 50 + 10 - 15


def test_hint_cost_floors_xp_at_zero() -> None:
    events = [
        ev(1, "room_solve", ref="room-a", points=100, xp=10),
        ev(1, "hint_cost", xp=999),
    ]
    me = project_me(events, _uid(1))
    assert me.points == 100
    assert me.xp == 0


def test_adjustment_events_change_points_arithmetically() -> None:
    events = [
        ev(2, "room_solve", ref="room-a", points=100),
        ev(2, "adjustment", points=-30),
        ev(2, "adjustment", points=5),
    ]
    me = project_me(events, _uid(2))
    assert me.points == 75


def test_track_breakdown_groups_point_events_only() -> None:
    events = [
        ev(1, "room_solve", ref="a", points=40, meta={"track": "web"}),
        ev(1, "room_solve", ref="b", points=60, meta={"track": "crypto"}),
        ev(1, "room_solve", ref="c", points=10),
        ev(1, "xp_award", xp=50, meta={"track": "web"}),
        ev(1, "hint_cost", xp=5, meta={"track": "web"}),
    ]
    me = project_me(events, _uid(1))
    assert me.tracks == {"crypto": 60, "general": 10, "web": 40}
