"""Notifications core integration gate (plan Phase 12 slice).

Drives the notification feed, preferences, announcement fanout, the
email outbox drainer, and RBAC through the real API against Postgres.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from openrange.api.notifications.service import emit
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.integration]

STRONG = "correct-horse-battery"


async def make_user(username: str) -> tuple[AsyncClient, dict[str, str]]:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    client = AsyncClient(transport=transport, base_url="http://test", timeout=60)
    res = await client.post("/api/auth/register", json={"username": username, "password": STRONG})
    assert res.status_code == 201, res.text
    return client, {"x-csrf-token": res.json()["csrf_token"]}


async def grant_role(db_engine: AsyncEngine, username: str, role_name: str) -> None:
    from openrange.api.db import session_factory
    from openrange.api.users.models import Role, User, UserRole

    assert session_factory is not None
    async with session_factory() as db:
        role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one()
        user = (await db.execute(select(User).where(User.username == username))).scalar_one()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()


async def set_email(username: str, email: str | None) -> None:
    from openrange.api.db import session_factory
    from openrange.api.users.models import User

    assert session_factory is not None
    async with session_factory() as db:
        user = (await db.execute(select(User).where(User.username == username))).scalar_one()
        user.email = email
        await db.commit()


async def user_id_of(username: str) -> uuid.UUID:
    from openrange.api.db import session_factory
    from openrange.api.users.models import User

    assert session_factory is not None
    async with session_factory() as db:
        user = (await db.execute(select(User.id).where(User.username == username))).scalar_one()
        assert user is not None
        return uuid.UUID(str(user))


@dataclass
class RecordingSender:
    sent: list[tuple[str, str]] = field(default_factory=list)

    async def send(self, *, to_email: str, subject: str, body_text: str) -> None:
        self.sent.append((to_email, subject))


class FailingSender:
    def __init__(self, error: str = "smtp down") -> None:
        self.error = error
        self.calls = 0

    async def send(self, *, to_email: str, subject: str, body_text: str) -> None:
        self.calls += 1
        raise RuntimeError(self.error)


async def seed_notification(username: str, category: str = "system") -> None:
    from openrange.api.db import session_factory

    uid = await user_id_of(username)
    assert session_factory is not None
    async with session_factory() as db:
        await emit(db, category=category, payload={"seeded": True}, user_ids=[uid])
        await db.commit()


async def table_count(table: str) -> int:
    from openrange.api.db import session_factory
    from openrange.api.notifications import models as nm

    model = {"notifications": nm.Notification, "email_outbox": nm.EmailOutbox}[table]
    assert session_factory is not None
    async with session_factory() as db:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def test_fanout_honors_mute_and_email_prefs(db_engine: AsyncEngine) -> None:
    admin, headers_adm = await make_user("notifadmin")
    alice, headers_alice = await make_user("notifalice")
    bob, headers_bob = await make_user("notifbob")
    dave, headers_dave = await make_user("notifdave")
    await grant_role(db_engine, "notifadmin", "admin")

    # Prefs roundtrip plus validation of unknown categories.
    default_prefs = await alice.get("/api/notifications/me/prefs", headers=headers_alice)
    assert default_prefs.status_code == 200, default_prefs.text
    assert default_prefs.json() == {
        "channel_in_app": True,
        "channel_email": False,
        "digest_weekly": False,
        "muted_categories": [],
    }
    bad = await alice.put(
        "/api/notifications/me/prefs",
        json={"muted_categories": ["nope"]},
        headers=headers_alice,
    )
    assert bad.status_code == 422

    # Alice opts into email (with an address); Bob mutes announcements;
    # Dave wants email but has no address on file.
    await set_email("notifalice", "alice@example.com")
    saved = await alice.put(
        "/api/notifications/me/prefs", json={"channel_email": True}, headers=headers_alice
    )
    assert saved.status_code == 200, saved.text
    muted = await bob.put(
        "/api/notifications/me/prefs",
        json={"muted_categories": ["announcement"]},
        headers=headers_bob,
    )
    assert muted.status_code == 200, muted.text
    dave_email = await dave.put(
        "/api/notifications/me/prefs", json={"channel_email": True}, headers=headers_dave
    )
    assert dave_email.status_code == 200, dave_email.text

    res = await admin.post(
        "/api/notifications/admin/announcements",
        json={
            "title": "Maintenance window",
            "body": "Range restarts tonight.",
            "severity": "warning",
        },
        headers=headers_adm,
    )
    assert res.status_code == 200, res.text
    announcement_id = res.json()["id"]

    alice_feed = await alice.get("/api/notifications/me")
    assert alice_feed.status_code == 200, alice_feed.text
    items = alice_feed.json()["items"]
    assert len(items) == 1
    assert items[0]["category"] == "announcement"
    assert items[0]["payload"]["announcement_id"] == announcement_id
    assert items[0]["read_at"] is None

    bob_feed = await bob.get("/api/notifications/me")
    assert bob_feed.json()["items"] == []
    dave_feed = await dave.get("/api/notifications/me")
    assert len(dave_feed.json()["items"]) == 1

    outbox = await admin.get(
        "/api/notifications/admin/email-outbox", params={"status": "queued"}, headers=headers_adm
    )
    assert outbox.status_code == 200, outbox.text
    rows = outbox.json()
    assert len(rows) == 1
    assert rows[0]["to_email"] == "alice@example.com"
    assert "Maintenance window" in rows[0]["subject"]

    await admin.aclose()
    await alice.aclose()
    await bob.aclose()
    await dave.aclose()


async def test_read_read_all_idempotent_and_paginates(db_engine: AsyncEngine) -> None:
    carol, headers_c = await make_user("notifcarol")
    for _ in range(3):
        await seed_notification("notifcarol")

    feed = await carol.get("/api/notifications/me")
    body = feed.json()
    assert body["total"] == 3
    ids = [item["id"] for item in body["items"]]
    assert len(ids) == 3

    first_read = await carol.post(f"/api/notifications/{ids[0]}/read", headers=headers_c)
    assert first_read.status_code == 200, first_read.text
    again = await carol.post(f"/api/notifications/{ids[0]}/read", headers=headers_c)
    assert again.status_code == 200, again.text
    assert again.json() == first_read.json()

    after = await carol.get("/api/notifications/me")
    items_after = after.json()["items"]
    read_rows = [i for i in items_after if i["read_at"] is not None]
    unread_rows = [i for i in items_after if i["read_at"] is None]
    assert len(read_rows) == 1
    assert len(unread_rows) == 2

    cleared = await carol.post("/api/notifications/read-all", headers=headers_c)
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["updated"] == 2
    repeat = await carol.post("/api/notifications/read-all", headers=headers_c)
    assert repeat.json()["updated"] == 0

    page = await carol.get("/api/notifications/me", params={"limit": 2, "offset": 0})
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 2
    assert all(i["read_at"] is not None for i in page.json()["items"])

    ghost = await carol.post(f"/api/notifications/{uuid.uuid4()}/read", headers=headers_c)
    assert ghost.status_code == 404
    junk = await carol.post("/api/notifications/not-a-uuid/read", headers=headers_c)
    assert junk.status_code == 404

    await carol.aclose()


async def test_audience_scoping(db_engine: AsyncEngine) -> None:
    erin, _headers_e = await make_user("notifierin")
    frank, _headers_f = await make_user("notifyfrank")

    assert await table_count("notifications") == 0
    from openrange.api.db import session_factory

    assert session_factory is not None
    async with session_factory() as db:
        created = await emit(
            db, category="system", audience="org:nonexistent", payload={"scope": "org"}
        )
        await db.commit()
    assert created == []
    assert await table_count("notifications") == 0

    async with session_factory() as db:
        created_all = await emit(
            db, category="announcement", audience="all", payload={"scope": "all"}
        )
        await db.commit()
    assert len(created_all) == 2
    assert await table_count("notifications") == 2

    erin_id = await user_id_of("notifierin")
    async with session_factory() as db:
        targeted = await emit(
            db, category="achievement", payload={"scope": "one"}, user_ids=[erin_id]
        )
        await db.commit()
    assert len(targeted) == 1

    erin_feed = await erin.get("/api/notifications/me")
    categories = {i["category"] for i in erin_feed.json()["items"]}
    assert categories == {"announcement", "achievement"}
    frank_feed = await frank.get("/api/notifications/me")
    assert {i["category"] for i in frank_feed.json()["items"]} == {"announcement"}

    await erin.aclose()
    await frank.aclose()


async def test_outbox_drain_marks_sent_with_fake_sender(db_engine: AsyncEngine) -> None:
    from openrange.api.db import session_factory
    from openrange.api.notifications.models import EmailOutbox
    from openrange.api.notifications.worker import OutboxDrainer

    assert session_factory is not None
    async with session_factory() as db:
        db.add(EmailOutbox(to_email="one@example.com", subject="Subject one", body_text="Body one"))
        db.add(EmailOutbox(to_email="two@example.com", subject="Subject two", body_text="Body two"))
        await db.commit()

    fake = RecordingSender()
    drainer = OutboxDrainer(batch_size=10, max_attempts=3)
    processed = await drainer.drain_once(sender=fake)
    assert processed == 2
    assert sorted(fake.sent) == [
        ("one@example.com", "Subject one"),
        ("two@example.com", "Subject two"),
    ]

    assert session_factory is not None
    async with session_factory() as db:
        rows = (
            (await db.execute(select(EmailOutbox).order_by(EmailOutbox.to_email))).scalars().all()
        )
        assert all(r.status == "sent" for r in rows)
        assert all(r.sent_at is not None for r in rows)
        assert all(r.attempts == 0 for r in rows)

    drained_again = await drainer.drain_once(sender=fake)
    assert drained_again == 0


async def test_failed_attempt_increments_and_backs_off(db_engine: AsyncEngine) -> None:
    from openrange.api.db import session_factory
    from openrange.api.notifications.models import EmailOutbox
    from openrange.api.notifications.worker import OutboxDrainer

    assert session_factory is not None
    async with session_factory() as db:
        row = EmailOutbox(to_email="x@example.com", subject="S", body_text="B")
        db.add(row)
        await db.commit()
        row_id = row.id

    failing = FailingSender("smtp refused")
    drainer = OutboxDrainer(max_attempts=2)

    processed = await drainer.drain_once(sender=failing)
    assert processed == 1
    assert failing.calls == 1

    assert session_factory is not None
    async with session_factory() as db:
        current = await db.get(EmailOutbox, row_id)
        assert current is not None
        assert current.status == "queued"
        assert current.attempts == 1
        assert "RuntimeError" in current.last_error
        assert current.next_attempt_at is not None
        wait = (current.next_attempt_at - datetime.now(UTC)).total_seconds()
        assert 30 <= wait <= 120

    # Backoff gates an immediate retry: nothing eligible yet.
    assert await drainer.drain_once(sender=failing) == 0
    assert failing.calls == 1

    async with session_factory() as db:
        current = await db.get(EmailOutbox, row_id)
        assert current is not None
        current.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        await db.commit()

    processed = await drainer.drain_once(sender=failing)
    assert processed == 1
    assert failing.calls == 2

    async with session_factory() as db:
        final = await db.get(EmailOutbox, row_id)
        assert final is not None
        assert final.status == "failed"
        assert final.attempts == 2
        assert final.sent_at is None
        assert "RuntimeError" in final.last_error


async def test_announcement_lifecycle_and_future_start(db_engine: AsyncEngine) -> None:
    admin, headers_adm = await make_user("notifadmin2")
    await grant_role(db_engine, "notifadmin2", "admin")

    future = await admin.post(
        "/api/notifications/admin/announcements",
        json={
            "title": "Scheduled",
            "body": "Fires later.",
            "starts_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        },
        headers=headers_adm,
    )
    assert future.status_code == 200, future.text
    assert await table_count("notifications") == 0

    listed = await admin.get("/api/notifications/admin/announcements", headers=headers_adm)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1
    scheduled_id = listed.json()[0]["id"]

    removed = await admin.delete(
        f"/api/notifications/admin/announcements/{scheduled_id}", headers=headers_adm
    )
    assert removed.status_code == 200, removed.text
    gone = await admin.delete(
        f"/api/notifications/admin/announcements/{scheduled_id}", headers=headers_adm
    )
    assert gone.status_code == 404
    final_list = await admin.get("/api/notifications/admin/announcements", headers=headers_adm)
    assert final_list.json() == []

    bad_audience = await admin.post(
        "/api/notifications/admin/announcements",
        json={"title": "T", "body": "B", "audience": "bogus"},
        headers=headers_adm,
    )
    assert bad_audience.status_code == 422

    await admin.aclose()


async def test_rbac_negatives(db_engine: AsyncEngine) -> None:
    learner, headers_l = await make_user("notiflearner")
    op, headers_op = await make_user("notifop")
    admin, headers_adm = await make_user("notifadmin3")
    await grant_role(db_engine, "notifop", "operator")
    await grant_role(db_engine, "notifadmin3", "admin")

    denied_create = await learner.post(
        "/api/notifications/admin/announcements",
        json={"title": "nope", "body": "nope"},
        headers=headers_l,
    )
    assert denied_create.status_code == 403
    denied_list = await learner.get("/api/notifications/admin/announcements", headers=headers_l)
    assert denied_list.status_code == 403
    denied_outbox = await learner.get("/api/notifications/admin/email-outbox", headers=headers_l)
    assert denied_outbox.status_code == 403
    denied_delete = await learner.delete(
        f"/api/notifications/admin/announcements/{uuid.uuid4()}", headers=headers_l
    )
    assert denied_delete.status_code == 403

    # Operators see the outbox but cannot publish announcements.
    op_outbox = await op.get("/api/notifications/admin/email-outbox", headers=headers_op)
    assert op_outbox.status_code == 200
    op_create = await op.post(
        "/api/notifications/admin/announcements",
        json={"title": "nope", "body": "nope"},
        headers=headers_op,
    )
    assert op_create.status_code == 403

    ok_create = await admin.post(
        "/api/notifications/admin/announcements",
        json={"title": "hi", "body": "hi"},
        headers=headers_adm,
    )
    assert ok_create.status_code == 200
    ok_outbox = await admin.get("/api/notifications/admin/email-outbox", headers=headers_adm)
    assert ok_outbox.status_code == 200

    bare = await _anon_get_me()
    assert bare == 401

    await learner.aclose()
    await op.aclose()
    await admin.aclose()


async def _anon_get_me() -> int:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as anon:
        res = await anon.get("/api/notifications/me")
        return res.status_code
