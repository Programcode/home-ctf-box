"""Scoring engine integration gate (plan Phase 9).

Real Postgres: ledger ingestion with idempotency, XP/score separation,
leaderboards and snapshots, data-driven achievements, adjustments, and
anti-cheat signals with review flow. RBAC negatives included.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

pytestmark = pytest.mark.integration

STRONG = "correct-horse-battery"


async def _make_user(username: str) -> tuple[AsyncClient, dict[str, str], uuid.UUID]:
    """Isolated client per user so cookie jars never collide."""
    from httpx import ASGITransport
    from openrange.api.main import create_app

    app = create_app()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=120)
    res = await client.post("/api/auth/register", json={"username": username, "password": STRONG})
    assert res.status_code == 201, res.text
    headers = {"x-csrf-token": res.json()["csrf_token"]}
    me = await client.get("/api/users/me")
    assert me.status_code == 200
    return client, headers, uuid.UUID(me.json()["id"])


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
    # Import lazily: the factory is created when the app first serves a
    # request, so the module-level symbol is still None at import time.
    from openrange.api.db import session_factory as sf

    assert sf is not None
    async with sf() as session:
        yield session


async def _ingest(db: Any, **kwargs: Any) -> Any:
    from openrange.api.scoring.service import record_score_event

    return await record_score_event(db, **kwargs)


async def test_idempotent_ingestion_double_award_guard(db_engine: Any) -> None:
    from openrange.api.scoring.models import ScoreEvent

    user, _h, uid = await _make_user("scorer1")
    key = f"room-solve:{uid}:room-a"
    async with _db() as db:
        first, created_first = await _ingest(
            db,
            user_id=uid,
            kind="room_solve",
            ref_slug="room-a",
            points=100,
            xp=10,
            idempotency_key=key,
        )
        second, created_second = await _ingest(
            db,
            user_id=uid,
            kind="room_solve",
            ref_slug="room-a",
            points=100,
            xp=10,
            idempotency_key=key,
        )
        count = (
            await db.execute(
                select(func.count())
                .select_from(ScoreEvent)
                .where(ScoreEvent.idempotency_key == key)
            )
        ).scalar_one()
    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert int(count) == 1
    await user.aclose()


async def test_velocity_signal_and_dedupe(db_engine: Any) -> None:
    from openrange.api.scoring.models import AntiCheatSignal
    from openrange.api.scoring.service import VELOCITY_THRESHOLD

    user, _h, uid = await _make_user("speedster")
    now = datetime.now(UTC)

    async def solves(n: int, prefix: str) -> None:
        async with _db() as db:
            for i in range(n):
                await _ingest(
                    db,
                    user_id=uid,
                    kind="room_solve",
                    ref_slug=f"room-{prefix}-{i}",
                    points=10,
                    idempotency_key=f"{prefix}:{uid}:{i}",
                    created_at=now - timedelta(seconds=i % 30),
                )
            await db.commit()

    async def signal_count() -> int:
        async with _db() as db:
            signals = (
                (await db.execute(select(AntiCheatSignal).where(AntiCheatSignal.user_id == uid)))
                .scalars()
                .all()
            )
            return len(list(signals))

    assert VELOCITY_THRESHOLD == 20
    await solves(VELOCITY_THRESHOLD, "v")
    assert await signal_count() == 0  # threshold not crossed at exactly 20

    await solves(1, "over")
    assert await signal_count() == 1  # impossible_timing raised once

    await solves(3, "v2")
    assert await signal_count() == 1  # no duplicate open signals
    await user.aclose()


async def test_me_score_xp_separation_and_tracks(db_engine: Any) -> None:
    learner, _headers, uid = await _make_user("tracker")
    now = datetime.now(UTC)
    plan = [
        dict(
            kind="room_solve",
            ref_slug="room-web-1",
            points=100,
            xp=10,
            meta={"track": "web"},
            idempotency_key=f"t1:{uid}",
        ),
        dict(kind="xp_award", ref_slug="path-basics", xp=50, idempotency_key=f"t2:{uid}"),
        dict(kind="hint_cost", ref_slug="room-web-1", xp=70, idempotency_key=f"t3:{uid}"),
        dict(kind="first_blood", ref_slug="room-web-1", points=25, idempotency_key=f"t4:{uid}"),
    ]
    async with _db() as db:
        for kwargs in plan:
            await _ingest(db, user_id=uid, created_at=now, **kwargs)
        await db.commit()

    score = (await learner.get("/api/scoring/me/score")).json()
    assert score["points"] == 125  # 100 room + 25 blood; xp_award/hint_cost excluded
    assert score["xp"] == 0  # 10 + 50 - 70 floors at zero
    assert score["tracks"] == {"general": 25, "web": 100}  # blood carries no track
    assert score["first_bloods"] == ["room-web-1"]
    await learner.aclose()


async def test_leaderboards_scopes_tiebreaks_and_boards(db_engine: Any) -> None:
    alice, _ha, aid = await _make_user("lb-alice")
    bob, _hb, bid = await _make_user("lb-bob")
    carol, _hc, cid = await _make_user("lb-carol")

    aug = lambda day: datetime(2026, 8, day, tzinfo=UTC)  # noqa: E731
    jul = datetime(2026, 7, 15, tzinfo=UTC)
    async with _db() as db:
        await _ingest(
            db,
            user_id=aid,
            kind="room_solve",
            ref_slug="room-a",
            points=100,
            idempotency_key="l1",
            created_at=aug(10),
        )
        await _ingest(
            db,
            user_id=bid,
            kind="room_solve",
            ref_slug="room-a",
            points=100,
            idempotency_key="l2",
            created_at=aug(11),
        )
        await _ingest(
            db,
            user_id=cid,
            kind="room_solve",
            ref_slug="room-b",
            points=50,
            idempotency_key="l3",
            created_at=aug(12),
        )
        await _ingest(
            db,
            user_id=cid,
            kind="room_solve",
            ref_slug="room-jul",
            points=500,
            idempotency_key="l4",
            created_at=jul,
        )
        await _ingest(
            db,
            user_id=cid,
            kind="first_blood",
            ref_slug="room-a",
            points=25,
            idempotency_key="l5",
            created_at=aug(1),
        )
        await db.commit()

    all_time = (await alice.get("/api/scoring/leaderboards/all_time")).json()
    ids = [row["user_id"] for row in all_time["rows"]]
    assert ids == [str(cid), str(aid), str(bid)]  # 550; tie: alice earlier last event
    assert [row["rank"] for row in all_time["rows"]] == [1, 2, 3]
    assert all_time["period_key"] == "all"

    monthly = (await alice.get("/api/scoring/leaderboards/monthly?period=2026-08")).json()
    by_user = {row["user_id"]: row["points"] for row in monthly["rows"]}
    assert by_user[str(cid)] == 75  # July solve excluded from August window
    assert by_user[str(aid)] == 100

    missing_period = await alice.get("/api/scoring/leaderboards/monthly")
    assert missing_period.status_code == 422

    seasonal = (await alice.get("/api/scoring/leaderboards/seasonal?period=season-one")).json()
    assert seasonal["period_key"] == "season-one"
    assert len(seasonal["rows"]) == 3

    bad_scope = await alice.get("/api/scoring/leaderboards/nonsense")
    assert bad_scope.status_code == 422

    room_board = (await alice.get("/api/scoring/leaderboards/room/room-a")).json()
    room_points = [row["points"] for row in room_board["rows"]]
    room_ids = [row["user_id"] for row in room_board["rows"]]
    assert room_ids[0] == str(aid)  # 100 vs 100 tie broken by earlier last event
    assert sorted(room_points) == [25, 100, 100]  # carol only has the blood here

    empty_path = (await alice.get("/api/scoring/leaderboards/path/path-none")).json()
    assert empty_path["rows"] == []
    await alice.aclose()
    await bob.aclose()
    await carol.aclose()


async def test_path_board_ranks_xp_with_hint_floor(db_engine: Any) -> None:
    dana, _hd, did = await _make_user("path-dana")
    eve, _he, eid = await _make_user("path-eve")
    async with _db() as db:
        await _ingest(
            db, user_id=did, kind="xp_award", ref_slug="path-pentest", xp=120, idempotency_key="p1"
        )
        await _ingest(
            db, user_id=eid, kind="xp_award", ref_slug="path-pentest", xp=100, idempotency_key="p2"
        )
        await _ingest(
            db, user_id=eid, kind="hint_cost", ref_slug="path-pentest", xp=150, idempotency_key="p3"
        )  # floors eve at zero
        await db.commit()

    board = (await dana.get("/api/scoring/leaderboards/path/path-pentest")).json()
    rows = board["rows"]
    assert rows[0]["user_id"] == str(did)
    assert rows[0]["xp"] == 120
    by_eve = next(row for row in rows if row["user_id"] == str(eid))
    assert by_eve["xp"] == 0
    await dana.aclose()
    await eve.aclose()


async def test_achievements_data_driven_award_once(db_engine: Any) -> None:
    admin, admin_h, _auid = await _make_admin("achv-admin")
    learner, _lh, lid = await _make_user("achv-learner")

    rule = {"type": "count", "event": "room_solve", "track": "web", "threshold": 5}
    created = await admin.post(
        "/api/scoring/admin/achievements",
        json={
            "slug": "web-five",
            "name": "Web Runner",
            "description": "Solve five web rooms",
            "rule": rule,
        },
        headers=admin_h,
    )
    assert created.status_code == 200, created.text

    updated = await admin.post(
        "/api/scoring/admin/achievements",
        json={
            "slug": "web-five",
            "name": "Web Runner II",
            "description": "Solve five web rooms",
            "rule": rule,
        },
        headers=admin_h,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Web Runner II"

    invalid = await admin.post(
        "/api/scoring/admin/achievements",
        json={
            "slug": "bad-rule",
            "name": "Bad",
            "rule": {"type": "count", "event": "nope", "threshold": 0},
        },
        headers=admin_h,
    )
    assert invalid.status_code == 422

    for i in range(7):
        async with _db() as db:
            await _ingest(
                db,
                user_id=lid,
                kind="room_solve",
                ref_slug=f"room-w{i}",
                points=10,
                meta={"track": "web"},
                idempotency_key=f"w:{lid}:{i}",
            )
            await db.commit()

    from openrange.api.scoring.models import ScoreEvent, UserAchievement

    async with _db() as db:
        awards = (
            await db.execute(
                select(func.count())
                .select_from(UserAchievement)
                .where(UserAchievement.user_id == lid, UserAchievement.slug == "web-five")
            )
        ).scalar_one()
        award_events = (
            await db.execute(
                select(func.count())
                .select_from(ScoreEvent)
                .where(ScoreEvent.user_id == lid, ScoreEvent.kind == "achievement")
            )
        ).scalar_one()
    assert int(awards) == 1  # threshold crossing awards exactly once
    assert int(award_events) == 1

    mine = (await learner.get("/api/scoring/me/achievements")).json()
    assert [a["slug"] for a in mine] == ["web-five"]
    assert mine[0]["name"] == "Web Runner II"
    await admin.aclose()
    await learner.aclose()


async def test_adjustments_arithmetic_audit_trail_and_rbac(db_engine: Any) -> None:
    from openrange.api.scoring.models import ScoreAdjustment

    admin, admin_h, ad_uid = await _make_admin("adj-admin")
    learner, learner_h, lid = await _make_user("adj-learner")

    async with _db() as db:
        original, _created = await _ingest(
            db,
            user_id=lid,
            kind="room_solve",
            ref_slug="room-cheat",
            points=100,
            idempotency_key=f"adj:{lid}",
        )
        await db.commit()

    deduction = await admin.post(
        "/api/scoring/admin/score-adjustments",
        json={
            "user_id": str(lid),
            "points": -40,
            "reason": "flag leaked in writeup",
            "original_event_id": original.id,
        },
        headers=admin_h,
    )
    assert deduction.status_code == 200, deduction.text
    assert deduction.json()["original_event_id"] == original.id

    bonus = await admin.post(
        "/api/scoring/admin/score-adjustments",
        json={"user_id": str(lid), "points": 5, "reason": "good faith"},
        headers=admin_h,
    )
    assert bonus.status_code == 200

    score = (await learner.get("/api/scoring/me/score")).json()
    assert score["points"] == 65  # 100 - 40 + 5

    async with _db() as db:
        links = (await db.execute(select(ScoreAdjustment))).scalars().all()
    assert len(links) == 2
    linked = next(link for link in links if link.original_event_id == original.id)
    assert linked.created_by == ad_uid
    assert linked.reason == "flag leaked in writeup"

    unknown_ref = await admin.post(
        "/api/scoring/admin/score-adjustments",
        json={
            "user_id": str(lid),
            "points": -1,
            "reason": "x",
            "original_event_id": 999999,
        },
        headers=admin_h,
    )
    assert unknown_ref.status_code == 404

    # Learner hits every admin endpoint: always 403.
    csrf = {"x-csrf-token": learner_h["x-csrf-token"]}
    r = await learner.post(
        "/api/scoring/admin/achievements",
        json={"slug": "x", "name": "x", "rule": {}},
        headers=csrf,
    )
    assert r.status_code == 403
    r = await learner.post(
        "/api/scoring/admin/score-adjustments",
        json={"user_id": str(lid), "points": 1, "reason": "self-grant"},
        headers=csrf,
    )
    assert r.status_code == 403
    r = await learner.get("/api/scoring/admin/anti-cheat/signals")
    assert r.status_code == 403
    r = await learner.post(
        "/api/scoring/admin/anti-cheat/signals/1/review",
        json={"action": "dismiss", "note": ""},
        headers=csrf,
    )
    assert r.status_code == 403
    await admin.aclose()
    await learner.aclose()


async def test_signals_listing_and_review_flow(db_engine: Any) -> None:
    from openrange.api.scoring import service as svc

    admin, admin_h, _admin_uid = await _make_admin("sig-admin")
    suspect, _sh, sid = await _make_user("sig-suspect")

    async with _db() as db:
        signal = await svc.record_signal(
            db, user_id=sid, kind="flag_reuse", details={"seen_in": ["room-a", "room-b"]}
        )
        await db.commit()

    open_list = (await admin.get("/api/scoring/admin/anti-cheat/signals?status=open")).json()
    assert [s["id"] for s in open_list] == [signal.id]

    dismissed = await admin.post(
        f"/api/scoring/admin/anti-cheat/signals/{signal.id}/review",
        json={"action": "dismiss", "note": "legit speedrun"},
        headers=admin_h,
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"
    still_open = (await admin.get("/api/scoring/admin/anti-cheat/signals?status=open")).json()
    assert still_open == []

    escalated = await admin.post(
        f"/api/scoring/admin/anti-cheat/signals/{signal.id}/review",
        json={"action": "escalate", "note": "second look"},
        headers=admin_h,
    )
    assert escalated.status_code == 200
    assert escalated.json()["status"] == "escalated"

    missing = await admin.post(
        "/api/scoring/admin/anti-cheat/signals/424242/review",
        json={"action": "dismiss"},
        headers=admin_h,
    )
    assert missing.status_code == 404
    await admin.aclose()
    await suspect.aclose()


async def test_anonymous_requests_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/scoring/me/score")).status_code == 401
    assert (await client.get("/api/scoring/leaderboards/all_time")).status_code == 401
