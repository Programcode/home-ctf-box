"""Events integration gate (plan Phase 9 items 3, 4, 7, 8).

Real Postgres: builder RBAC, registration windows and team bounds,
static/dynamic scoring with hand-computed decay, first blood once,
frozen scoreboard snapshots with explicit refresh, fair attribution
across mid-event team switches, and privacy for org-scoped events.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from openrange.api.events.models import Event, EventSolve
from openrange.api.events.service import (
    dynamic_points,
    first_blood_bonus,
    record_event_solve,
)
from sqlalchemy import func, select

pytestmark = pytest.mark.integration

STRONG = "correct-horse-battery"

_clients: list[AsyncClient] = []


@pytest.fixture(autouse=True)
async def _close_clients() -> AsyncIterator[None]:
    yield
    while _clients:
        await _clients.pop().aclose()


async def _make_user(username: str) -> tuple[AsyncClient, dict[str, str], uuid.UUID]:
    from httpx import ASGITransport
    from openrange.api.main import create_app

    app = create_app()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=120)
    _clients.append(client)
    res = await client.post("/api/auth/register", json={"username": username, "password": STRONG})
    assert res.status_code == 201, res.text
    me = await client.get("/api/users/me")
    return client, {"x-csrf-token": res.json()["csrf_token"]}, uuid.UUID(me.json()["id"])


async def _make_admin(username: str) -> tuple[AsyncClient, dict[str, str], uuid.UUID]:
    from openrange.api.auth.service import grant_role
    from openrange.api.users.models import User

    client, headers, user_id = await _make_user(username)
    async with _db() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        await grant_role(db, user, "admin")
        await db.commit()
    return client, headers, user_id


@asynccontextmanager
async def _db() -> AsyncIterator[Any]:
    from openrange.api.db import session_factory as sf

    assert sf is not None
    async with sf() as session:
        yield session


def _window(start_offset: float, end_offset: float) -> dict[str, str]:
    now = datetime.now(UTC)
    return {
        "starts_at": (now + timedelta(seconds=start_offset)).isoformat(),
        "ends_at": (now + timedelta(seconds=end_offset)).isoformat(),
    }


async def _create_event(
    admin: AsyncClient, admin_h: dict[str, str] | None, slug: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"slug": slug, "name": f"Event {slug}"}
    payload.update(_window(-3600, 7 * 86400))
    payload.update(overrides)
    headers = admin_h or {"x-csrf-token": "unused"}
    res = await admin.post("/api/events", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def _event_id(db: Any, slug: str) -> uuid.UUID:
    event = (await db.execute(select(Event).where(Event.slug == slug))).scalar_one()
    return event.id


async def _solve(
    db: Any,
    slug: str,
    *,
    actor_user_id: uuid.UUID,
    room_slug: str,
    task_slug: str,
    task_points: int,
    solved_at: datetime | None = None,
) -> tuple[EventSolve, bool]:
    event = (await db.execute(select(Event).where(Event.slug == slug))).scalar_one()
    return await record_event_solve(
        db,
        event=event,
        actor_user_id=actor_user_id,
        room_slug=room_slug,
        task_slug=task_slug,
        task_points=task_points,
        solved_at=solved_at,
    )


async def test_dynamic_decay_math_matches_hand_table(db_engine: Any) -> None:
    # Hand-computed table: f(n) = round(100 * 100 / (100 + n * 1)).
    expected = {0: 100, 1: 99, 2: 98, 3: 97, 4: 96, 9: 92, 19: 84, 49: 67, 99: 50}
    for order, value in expected.items():
        assert dynamic_points(100, 100, order) == value
    # A different weight rescales the curve.
    assert dynamic_points(100, 50, 0) == 100
    assert dynamic_points(100, 50, 1) == round(100 * 50 / 51)  # 98
    assert first_blood_bonus(100) == 10
    assert first_blood_bonus(33) == 3  # round(3.3)

    admin, admin_h, _auid = await _make_admin("decay-admin")
    await _create_event(admin, admin_h, "decay-cup", scoring_model="dynamic")

    solver_ids: list[uuid.UUID] = []
    for i in range(5):
        c, h, uid = await _make_user(f"decayer-{i}")
        reg = await c.post("/api/events/decay-cup/registrations", json={"kind": "user"}, headers=h)
        assert reg.status_code == 201, reg.text
        solver_ids.append(uid)

    base = datetime.now(UTC) - timedelta(hours=1)
    async with _db() as db:
        for i, uid in enumerate(solver_ids):
            _row, created = await _solve(
                db,
                "decay-cup",
                actor_user_id=uid,
                room_slug="room-x",
                task_slug="task-1",
                task_points=100,
                solved_at=base + timedelta(minutes=i),
            )
            await db.commit()
            assert created

    async with _db() as db:
        rows = list(
            (
                await db.execute(
                    select(EventSolve)
                    .where(EventSolve.event_id == await _event_id(db, "decay-cup"))
                    .order_by(EventSolve.solved_at.asc())
                )
            ).scalars()
        )
    # First solver takes full base plus the flat +10% bonus; the rest
    # walk the decayed table.
    assert [r.points_awarded for r in rows] == [110, 99, 98, 97, 96]
    assert [r.first_blood for r in rows] == [True, False, False, False, False]


async def test_static_lifecycle_scoreboard_order_and_tiebreaks(db_engine: Any) -> None:
    admin, admin_h, _aid = await _make_admin("cup-admin")
    await _create_event(admin, admin_h, "lifecycle-cup")

    names = ["alice-cup", "bob-cup", "carol-cup", "dave-cup", "eve-cup"]
    users: dict[str, tuple[AsyncClient, dict[str, str], uuid.UUID]] = {}
    for name in names:
        users[name] = await _make_user(name)
        reg = await users[name][0].post(
            "/api/events/lifecycle-cup/registrations",
            json={"kind": "user"},
            headers=users[name][1],
        )
        assert reg.status_code == 201, reg.text

    base = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)

    def day(n: int) -> datetime:
        return base + timedelta(days=n)

    plan = [
        # (username, room, task, base_points, when): bob reaches his
        # total earliest, then carol, then alice.
        ("bob-cup", "room-b", "t2", 100, day(1)),
        ("carol-cup", "room-c", "t3", 50, day(2)),
        ("alice-cup", "room-a", "t1", 100, day(3)),
        ("dave-cup", "room-d", "t4", 20, day(5)),
        ("eve-cup", "room-e", "t5", 20, day(5)),  # identical instant to dave
    ]
    async with _db() as db:
        for username, room, task, pts, at in plan:
            solve, created = await _solve(
                db,
                "lifecycle-cup",
                actor_user_id=users[username][2],
                room_slug=room,
                task_slug=task,
                task_points=pts,
                solved_at=at,
            )
            await db.commit()
            assert created
            assert solve.first_blood is True  # one solver per task here

    alice = users["alice-cup"][0]
    board = (await alice.get("/api/events/lifecycle-cup/scoreboard")).json()
    assert board["frozen"] is False
    rows = board["rows"]
    # Points desc; ties by earliest cumulative solve time (bob beat
    # alice to 110); dave/eve share points and time so name asc applies.
    assert [(r["name"], r["points"]) for r in rows] == [
        ("bob-cup", 110),
        ("alice-cup", 110),
        ("carol-cup", 55),
        ("dave-cup", 22),
        ("eve-cup", 22),
    ]
    assert [r["rank"] for r in rows] == [1, 2, 3, 4, 5]
    assert all(r["subject_kind"] == "user" for r in rows)


async def test_first_blood_once_and_idempotent_replay(db_engine: Any) -> None:
    admin, admin_h, _auid = await _make_admin("blood-admin")
    await _create_event(admin, admin_h, "blood-cup")
    u1, u1h, u1id = await _make_user("blood-one")
    u2, u2h, u2id = await _make_user("blood-two")
    for c, h in ((u1, u1h), (u2, u2h)):
        res = await c.post("/api/events/blood-cup/registrations", json={"kind": "user"}, headers=h)
        assert res.status_code == 201

    t0 = datetime.now(UTC) - timedelta(hours=1)
    async with _db() as db:
        first, created1 = await _solve(
            db,
            "blood-cup",
            actor_user_id=u1id,
            room_slug="r",
            task_slug="t",
            task_points=40,
            solved_at=t0,
        )
        second, created2 = await _solve(
            db,
            "blood-cup",
            actor_user_id=u2id,
            room_slug="r",
            task_slug="t",
            task_points=40,
            solved_at=t0 + timedelta(minutes=1),
        )
        replay, created3 = await _solve(
            db,
            "blood-cup",
            actor_user_id=u1id,
            room_slug="r",
            task_slug="t",
            task_points=40,
            solved_at=t0,
        )
        total = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(EventSolve)
                    .where(EventSolve.event_id == await _event_id(db, "blood-cup"))
                )
            ).scalar_one()
        )
        await db.commit()

    assert created1 and created2
    assert created3 is False
    assert replay.id == first.id  # stored row returned unchanged
    assert first.points_awarded == 44  # 40 + round(4.0) first-blood bonus
    assert first.first_blood is True
    assert second.points_awarded == 40  # no double bonus
    assert second.first_blood is False
    assert total == 2


async def test_freeze_snapshot_immutability_and_admin_refresh(db_engine: Any) -> None:
    from openrange.api.auth.service import AuthError

    admin, admin_h, _auid = await _make_admin("freeze-admin")
    future = datetime.now(UTC) + timedelta(hours=6)
    past = datetime.now(UTC) - timedelta(hours=1)
    await _create_event(admin, admin_h, "frozen-cup", scoreboard_freeze_at=future.isoformat())

    u1, _h1, u1id = await _make_user("freezer-one")
    _u2, _h2, u2id = await _make_user("freezer-two")
    async with _db() as db:
        solve, created = await _solve(
            db,
            "frozen-cup",
            actor_user_id=u1id,
            room_slug="r",
            task_slug="t",
            task_points=100,
            solved_at=datetime.now(UTC) - timedelta(minutes=30),
        )
        await db.commit()
    assert created and solve.points_awarded == 110

    # Freeze time passes (builder PATCH moves it into the past).
    patched = await admin.patch(
        "/api/events/frozen-cup",
        json={"scoreboard_freeze_at": past.isoformat()},
        headers=admin_h,
    )
    assert patched.status_code == 200

    first_view = (await u1.get("/api/events/frozen-cup/scoreboard")).json()
    assert first_view["frozen"] is True
    assert first_view["computed_at"] is not None
    assert len(first_view["rows"]) == 1

    # A new solve lands after the freeze via a direct write (the service
    # would refuse); the frozen view must NOT change.
    async with _db() as db:
        db.add(
            EventSolve(
                event_id=await _event_id(db, "frozen-cup"),
                subject_kind="user",
                subject_id=u2id,
                room_slug="r",
                task_slug="t",
                points_awarded=100,
                first_blood=False,
                solved_at=datetime.now(UTC),
            )
        )
        await db.commit()

    second_view = (await u1.get("/api/events/frozen-cup/scoreboard")).json()
    assert second_view["rows"] == first_view["rows"]
    assert second_view["computed_at"] == first_view["computed_at"]

    # Only an explicit refresh picks up the late row.
    refreshed = await admin.post("/api/events/frozen-cup/scoreboard/refresh", headers=admin_h)
    assert refreshed.status_code == 200
    assert len(refreshed.json()["rows"]) == 2

    third_view = (await u1.get("/api/events/frozen-cup/scoreboard")).json()
    assert third_view["computed_at"] >= first_view["computed_at"]
    assert {r["subject_id"] for r in third_view["rows"]} == {str(u1id), str(u2id)}

    # Ingestion after freeze is refused outright.
    with pytest.raises(AuthError) as excinfo:
        async with _db() as db:
            await _solve(
                db,
                "frozen-cup",
                actor_user_id=u2id,
                room_slug="r2",
                task_slug="t",
                task_points=10,
            )
    assert excinfo.value.status == 409


async def test_team_registration_bounds_and_closed_window(db_engine: Any) -> None:
    admin, admin_h, _auid = await _make_admin("teamreg-admin")
    await _create_event(admin, admin_h, "team-cup", team_size_min=2, team_size_max=3)
    closed = await _create_event(
        admin,
        admin_h,
        "closed-cup",
        **{
            "starts_at": _window(-3600, 7 * 86400)["starts_at"],
            "ends_at": _window(-3600, 7 * 86400)["ends_at"],
            "registration_close_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
        },
    )

    captain, cap_headers, _cid = await _make_user("reg-captain")
    member, member_headers, _mid = await _make_user("reg-member")
    extra, extra_headers, _eid = await _make_user("reg-extra")
    fourth, fourth_headers, _fid = await _make_user("reg-fourth")

    # Solo team: below the event's minimum of two.
    created = await captain.post("/api/teams", json={"name": "reg-squad"}, headers=cap_headers)
    assert created.status_code == 201
    below_min = await captain.post(
        "/api/events/team-cup/registrations",
        json={"kind": "team", "team_name": "reg-squad"},
        headers=cap_headers,
    )
    assert below_min.status_code == 409
    assert "at least 2" in str(below_min.json()["detail"])

    code = (await captain.post("/api/teams/reg-squad/invites", headers=cap_headers)).json()["code"]
    joined = await member.post("/api/teams/join", json={"code": code}, headers=member_headers)
    assert joined.status_code == 200

    ok = await captain.post(
        "/api/events/team-cup/registrations",
        json={"kind": "team", "team_name": "reg-squad"},
        headers=cap_headers,
    )
    assert ok.status_code == 201, ok.text

    dup = await captain.post(
        "/api/events/team-cup/registrations",
        json={"kind": "team", "team_name": "reg-squad"},
        headers=cap_headers,
    )
    assert dup.status_code == 409

    # A four-person team cannot register while the maximum is three.
    big = await captain.post("/api/teams", json={"name": "big-squad"}, headers=cap_headers)
    assert big.status_code == 201
    for invitee_client, invitee_headers in (
        (member, member_headers),
        (extra, extra_headers),
        (fourth, fourth_headers),
    ):
        minted = await captain.post("/api/teams/big-squad/invites", headers=cap_headers)
        res = await invitee_client.post(
            "/api/teams/join", json={"code": minted.json()["code"]}, headers=invitee_headers
        )
        assert res.status_code == 200
    over_max = await captain.post(
        "/api/events/team-cup/registrations",
        json={"kind": "team", "team_name": "big-squad"},
        headers=cap_headers,
    )
    assert over_max.status_code == 409
    assert "at most 3" in str(over_max.json()["detail"])

    # Closed registration window rejects everyone.
    late = await extra.post(
        "/api/events/closed-cup/registrations", json={"kind": "user"}, headers=extra_headers
    )
    assert late.status_code == 409
    assert closed["slug"] == "closed-cup"


async def test_attribution_stays_with_original_team_after_switch(db_engine: Any) -> None:
    from openrange.api.events.service import start_team_session
    from openrange.api.teams.models import Team

    admin, admin_h, _auid = await _make_admin("attr-admin")
    await _create_event(admin, admin_h, "attr-cup")

    cap_a, cap_a_headers, _caid = await _make_user("attr-cap-a")
    worker, worker_headers, wid = await _make_user("attr-worker")
    cap_b, cap_b_headers, _cbid = await _make_user("attr-cap-b")

    alpha = await cap_a.post("/api/teams", json={"name": "attr-alpha"}, headers=cap_a_headers)
    assert alpha.status_code == 201
    beta = await cap_b.post("/api/teams", json={"name": "attr-beta"}, headers=cap_b_headers)
    assert beta.status_code == 201

    code_alpha = (await cap_a.post("/api/teams/attr-alpha/invites", headers=cap_a_headers)).json()[
        "code"
    ]
    joined_alpha = await worker.post(
        "/api/teams/join", json={"code": code_alpha}, headers=worker_headers
    )
    assert joined_alpha.status_code == 200

    async def team_id(name: str) -> uuid.UUID:
        async with _db() as db:
            team = (await db.execute(select(Team).where(Team.name == name))).scalar_one()
            return team.id

    alpha_id = await team_id("attr-alpha")
    beta_id = await team_id("attr-beta")
    now = datetime.now(UTC)

    # Solve before any session exists: stays with the individual.
    async with _db() as db:
        event = (await db.execute(select(Event).where(Event.slug == "attr-cup"))).scalar_one()
        early, created_early = await record_event_solve(
            db,
            event=event,
            actor_user_id=wid,
            room_slug="room-1",
            task_slug="t1",
            task_points=100,
            solved_at=now - timedelta(hours=2),
        )
        assert created_early
        assert (early.subject_kind, early.subject_id) == ("user", wid)
        # Alpha starts its shared session; the next solve attributes to it.
        await start_team_session(db, event, alpha_id)
        on_alpha, created_alpha = await record_event_solve(
            db,
            event=event,
            actor_user_id=wid,
            room_slug="room-1",
            task_slug="t2",
            task_points=100,
            solved_at=now + timedelta(minutes=30),
        )
        await db.commit()

    assert created_alpha
    assert (on_alpha.subject_kind, on_alpha.subject_id) == ("team", alpha_id)

    # Mid-event switch: leave alpha, join beta, start beta's session.
    left = await worker.delete(f"/api/teams/attr-alpha/members/{wid}", headers=worker_headers)
    assert left.status_code == 200
    code_beta = (await cap_b.post("/api/teams/attr-beta/invites", headers=cap_b_headers)).json()[
        "code"
    ]
    joined_beta = await worker.post(
        "/api/teams/join", json={"code": code_beta}, headers=worker_headers
    )
    assert joined_beta.status_code == 200

    async with _db() as db:
        event = (await db.execute(select(Event).where(Event.slug == "attr-cup"))).scalar_one()
        await start_team_session(db, event, beta_id)
        on_beta, created_beta = await record_event_solve(
            db,
            event=event,
            actor_user_id=wid,
            room_slug="room-1",
            task_slug="t3",
            task_points=100,
            solved_at=now + timedelta(hours=1),
        )
        await db.commit()

    assert created_beta
    assert (on_beta.subject_kind, on_beta.subject_id) == ("team", beta_id)

    # The earlier row still belongs to alpha; nothing was reattributed.
    async with _db() as db:
        rows = list(
            (
                await db.execute(
                    select(EventSolve)
                    .where(EventSolve.event_id == await _event_id(db, "attr-cup"))
                    .order_by(EventSolve.solved_at.asc())
                )
            ).scalars()
        )
    assert [(r.subject_kind, r.subject_id) for r in rows] == [
        ("user", wid),
        ("team", alpha_id),
        ("team", beta_id),
    ]

    board = (await worker.get("/api/events/attr-cup/scoreboard")).json()
    assert [(r["subject_kind"], r["points"]) for r in board["rows"]] == [
        ("user", 110),
        ("team", 110),
        ("team", 110),
    ]
    assert [r["rank"] for r in board["rows"]] == [1, 2, 3]


async def test_builder_rbac_org_visibility_and_listing(db_engine: Any) -> None:
    learner, learner_h, _lid = await _make_user("rbac-learner")
    admin, admin_h, _aid = await _make_admin("rbac-admin")
    owner, owner_h, _oid = await _make_user("org-owner")

    # Learners cannot create public events.
    denied = await learner.post(
        "/api/events",
        json={"slug": "nope-cup", "name": "Nope", **_window(-3600, 86400)},
        headers=learner_h,
    )
    assert denied.status_code == 403

    # Org owners can create org-scoped events without being admins.
    org_res = await owner.post("/api/orgs", json={"name": "rbac-org"}, headers=owner_h)
    assert org_res.status_code == 201, org_res.text
    created = await owner.post(
        "/api/events",
        json={
            "slug": "org-cup",
            "name": "Org Cup",
            "visibility": "org:rbac-org",
            **_window(-3600, 86400),
        },
        headers=owner_h,
    )
    assert created.status_code == 201, created.text

    # Strangers get a 404 for the org event and never see it listed.
    stranger_view = await learner.get("/api/events/org-cup")
    assert stranger_view.status_code == 404
    listing = (await learner.get("/api/events")).json()
    slugs = [e["slug"] for e in listing]
    assert "org-cup" not in slugs

    # Admins see everything, including org events they do not belong to.
    admin_list = [e["slug"] for e in (await admin.get("/api/events")).json()]
    assert "org-cup" in admin_list

    # Joining the org makes the event visible.
    invite = await owner.post("/api/orgs/rbac-org/invites", json={}, headers=owner_h)
    assert invite.status_code == 201
    accepted = await learner.post(
        f"/api/invites/{invite.json()['token']}/accept", headers=learner_h
    )
    assert accepted.status_code == 200, accepted.text
    member_view = await learner.get("/api/events/org-cup")
    assert member_view.status_code == 200
    assert "org-cup" in [e["slug"] for e in (await learner.get("/api/events")).json()]

    # Only builders may patch or refresh: learner is neither.
    patch_denied = await learner.patch(
        "/api/events/org-cup", json={"name": "Hijacked"}, headers=learner_h
    )
    assert patch_denied.status_code == 403
    refresh_denied = await learner.post("/api/events/org-cup/scoreboard/refresh", headers=learner_h)
    assert refresh_denied.status_code == 403
    unknown_refresh = await learner.post(
        "/api/events/no-such/scoreboard/refresh", headers=learner_h
    )
    assert unknown_refresh.status_code == 404

    # The org owner refreshes fine.
    refreshed = await owner.post("/api/events/org-cup/scoreboard/refresh", headers=owner_h)
    assert refreshed.status_code == 200

    # Malformed payloads are rejected.
    bad_window = await admin.post(
        "/api/events",
        json={"slug": "backwards", "name": "Backwards", **_window(86400, -3600)},
        headers=admin_h,
    )
    assert bad_window.status_code == 422
    bad_slug = await admin.post(
        "/api/events",
        json={"slug": "Not A Slug", "name": "Bad", **_window(-3600, 86400)},
        headers=admin_h,
    )
    assert bad_slug.status_code == 422

    # Ended events drop out of listings but stay fetchable.
    ended = await admin.post(
        "/api/events",
        json={
            "slug": "ended-cup",
            "name": "Ended Cup",
            "starts_at": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
            "ends_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        },
        headers=admin_h,
    )
    assert ended.status_code == 201
    assert "ended-cup" not in [e["slug"] for e in (await admin.get("/api/events")).json()]
    still_there = await admin.get("/api/events/ended-cup")
    assert still_there.status_code == 200


async def test_anonymous_requests_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/events")).status_code == 401
    assert (await client.get("/api/events/whatever/scoreboard")).status_code == 401
