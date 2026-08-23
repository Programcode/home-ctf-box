"""Organizations, cohorts, and assignment progress gate (plan Phase 11).

Drives org lifecycle, the per-org role matrix, cross-org isolation,
last-owner protection, member pagination, cohort CRUD, and lazily
derived assignment progress through the real API against Postgres,
with a fixture curriculum on disk for path outlines.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from openrange.api.learning import content as learning_content
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from testshelpers.curriculum import write_curriculum

pytestmark = [pytest.mark.integration]

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def curriculum(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    root = write_curriculum(tmp_path / "content")
    monkeypatch.setenv(learning_content.CONTENT_DIR_ENV, str(root))
    learning_content.clear_caches()
    yield root
    learning_content.clear_caches()


async def make_user(
    username: str, email: str | None = None
) -> tuple[AsyncClient, dict[str, str], str]:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    client = AsyncClient(transport=transport, base_url="http://test", timeout=60)
    res = await client.post(
        "/api/auth/register", json={"username": username, "password": PASSWORD, "email": email}
    )
    assert res.status_code == 201, res.text
    return client, {"x-csrf-token": res.json()["csrf_token"]}, res.json()["id"]


async def create_org(client: AsyncClient, headers: dict[str, str], name: str) -> dict[str, object]:
    res = await client.post(
        "/api/orgs", json={"name": name, "display_name": f"Org {name}"}, headers=headers
    )
    assert res.status_code == 201, res.text
    return res.json()


async def join_via_link_invite(
    owner: AsyncClient,
    owner_headers: dict[str, str],
    slug: str,
    joiner: AsyncClient,
    joiner_headers: dict[str, str],
) -> None:
    res = await owner.post(
        f"/api/orgs/{slug}/invites", json={"role": "member"}, headers=owner_headers
    )
    assert res.status_code == 201, res.text
    token = res.json()["token"]
    accept = await joiner.post(f"/api/invites/{token}/accept", headers=joiner_headers)
    assert accept.status_code == 200, accept.text


@pytest.fixture
async def db(db_engine: AsyncEngine) -> AsyncIterator[async_sessionmaker]:
    """Session factory for direct read-model seeding."""
    yield async_sessionmaker(db_engine, expire_on_commit=False)


async def test_create_org_lifecycle_and_visibility() -> None:
    alice, ha, _ = await make_user("org-alice")
    org = await create_org(alice, ha, "alpha-range")
    assert org["role"] == "owner" and org["display_name"] == "Org alpha-range"

    mine = await alice.get("/api/orgs/mine", headers=ha)
    assert [o["name"] for o in mine.json()] == ["alpha-range"]

    detail = await alice.get("/api/orgs/alpha-range", headers=ha)
    assert detail.status_code == 200

    bob, hb, _ = await make_user("org-bob")
    outsider = await bob.get("/api/orgs/alpha-range", headers=hb)
    # Cross-org isolation hides even the existence of the org.
    assert outsider.status_code == 404

    # Slug rules and collisions.
    for bad in ["ab", "UPPER", "has space", "x" * 41]:
        res = await alice.post("/api/orgs", json={"name": bad}, headers=ha)
        assert res.status_code == 422, bad
    reserved = await alice.post("/api/orgs", json={"name": "mine"}, headers=ha)
    assert reserved.status_code == 422
    dup = await alice.post("/api/orgs", json={"name": "alpha-range"}, headers=ha)
    assert dup.status_code == 409

    rename = await alice.put(
        "/api/orgs/alpha-range", json={"display_name": "Alpha Range"}, headers=ha
    )
    assert rename.status_code == 200 and rename.json()["display_name"] == "Alpha Range"


async def test_role_matrix_and_cross_org_isolation() -> None:
    alice, ha, _ = await make_user("matrix-alice")
    await create_org(alice, ha, "matrix-org")
    carol, hc, uid_carol = await make_user("matrix-carol")
    await join_via_link_invite(alice, ha, "matrix-org", carol, hc)
    promote = await alice.patch(
        f"/api/orgs/matrix-org/members/{uid_carol}", json={"role": "instructor"}, headers=ha
    )
    assert promote.status_code == 200

    dave, hd, _ = await make_user("matrix-dave")
    await create_org(dave, hd, "other-org")

    cohort_res = await carol.post(
        "/api/orgs/matrix-org/cohorts",
        json={"name": "cohort-a"},
        headers=hc,
    )
    assert cohort_res.status_code == 201, cohort_res.text
    cohort_id = cohort_res.json()["id"]

    assign_res = await carol.post(
        "/api/orgs/matrix-org/assignments",
        json={"content_kind": "path", "content_slug": "foundations-path"},
        headers=hc,
    )
    assert assign_res.status_code == 201, assign_res.text
    assignment_id = assign_res.json()["id"]

    # Member: reads yes, writes no.
    bob, hb, _ = await make_user("matrix-bob")
    await join_via_link_invite(alice, ha, "matrix-org", bob, hb)
    assert (await bob.get("/api/orgs/matrix-org/members", headers=hb)).status_code == 200
    forbidden_member = [
        ("/api/orgs/matrix-org/cohorts", "post", {"name": "nope"}),
        (
            "/api/orgs/matrix-org/assignments",
            "post",
            {"content_kind": "path", "content_slug": "foundations-path"},
        ),
        ("/api/orgs/matrix-org/invites", "post", {}),
        ("/api/orgs/matrix-org", "put", {"display_name": "hijack"}),
        (f"/api/orgs/matrix-org/members/{uid_carol}", "patch", {"role": "owner"}),
        (f"/api/orgs/matrix-org/members/{uid_carol}", "delete", None),
        (f"/api/orgs/matrix-org/cohorts/{cohort_id}", "delete", None),
    ]
    for url, method, body in forbidden_member:
        res = await bob.request(method.upper(), url, json=body, headers=hb)
        assert res.status_code == 403, (url, method, res.text)

    # Instructor: cohort/assignment writes yes, admin writes no.
    assert (
        await carol.get(f"/api/orgs/matrix-org/assignments/{assignment_id}/progress", headers=hc)
    ).status_code == 200
    forbidden_instructor = [
        ("/api/orgs/matrix-org/invites", "post", {}),
        ("/api/orgs/matrix-org", "put", {"display_name": "nope"}),
        (f"/api/orgs/matrix-org/members/{uid_carol}", "patch", {"role": "member"}),
    ]
    for url, method, body in forbidden_instructor:
        res = await carol.request(method.upper(), url, json=body, headers=hc)
        assert res.status_code == 403, (url, method, res.text)

    # Owner of another org: everything looks like it does not exist.
    cross = [
        ("/api/orgs/matrix-org", "get", None),
        ("/api/orgs/matrix-org/members", "get", None),
        ("/api/orgs/matrix-org/cohorts", "post", {"name": "invade"}),
        ("/api/orgs/matrix-org/invites", "post", {}),
        (f"/api/orgs/matrix-org/members/{uid_carol}", "delete", None),
        (f"/api/orgs/matrix-org/assignments/{assignment_id}/progress", "get", None),
    ]
    for url, method, body in cross:
        res = await dave.request(method.upper(), url, json=body, headers=hd)
        assert res.status_code == 404, (url, method, res.text)

    missing = await alice.get("/api/orgs/does-not-exist", headers=ha)
    assert missing.status_code == 404


async def test_member_administration_and_last_owner_protection() -> None:
    alice, ha, uid_alice = await make_user("admin-alice")
    await create_org(alice, ha, "admin-org")
    bob, hb, uid_bob = await make_user("admin-bob")
    await join_via_link_invite(alice, ha, "admin-org", bob, hb)

    # Promote, then demote while another owner exists.
    assert (
        await alice.patch(
            f"/api/orgs/admin-org/members/{uid_bob}", json={"role": "owner"}, headers=ha
        )
    ).status_code == 200
    assert (
        await alice.patch(
            f"/api/orgs/admin-org/members/{uid_bob}", json={"role": "member"}, headers=ha
        )
    ).status_code == 200

    # Last owner cannot be demoted or removed.
    blocked_demote = await alice.patch(
        f"/api/orgs/admin-org/members/{uid_alice}", json={"role": "member"}, headers=ha
    )
    assert blocked_demote.status_code == 409
    blocked_leave = await alice.delete(f"/api/orgs/admin-org/members/{uid_alice}", headers=ha)
    assert blocked_leave.status_code == 409

    # With a second owner present, the original owner may step down.
    await alice.patch(f"/api/orgs/admin-org/members/{uid_bob}", json={"role": "owner"}, headers=ha)
    leave = await alice.delete(f"/api/orgs/admin-org/members/{uid_alice}", headers=ha)
    assert leave.status_code == 200
    gone = await alice.get("/api/orgs/admin-org", headers=ha)
    assert gone.status_code == 404

    unknown_patch = await bob.patch(
        f"/api/orgs/admin-org/members/{uuid.uuid4()}", json={"role": "member"}, headers=hb
    )
    assert unknown_patch.status_code == 404
    unknown_delete = await bob.delete(f"/api/orgs/admin-org/members/{uuid.uuid4()}", headers=hb)
    assert unknown_delete.status_code == 404
    bad_role = await bob.patch(
        f"/api/orgs/admin-org/members/{uid_bob}", json={"role": "emperor"}, headers=hb
    )
    assert bad_role.status_code == 422


async def test_members_pagination() -> None:
    alice, ha, _ = await make_user("page-alice")
    await create_org(alice, ha, "page-org")
    usernames = ["page-u1", "page-u2", "page-u3", "page-u4", "page-u5", "page-u6", "page-u7"]

    clients = []
    try:
        for name in usernames:
            client, headers, _uid = await make_user(name)
            clients.append(client)
            await join_via_link_invite(alice, ha, "page-org", client, headers)
        seen: list[str] = []
        for offset in (0, 3, 6):
            res = await alice.get(f"/api/orgs/page-org/members?limit=3&offset={offset}", headers=ha)
            assert res.status_code == 200, res.text
            body = res.json()
            assert body["total"] == 8
            assert body["limit"] == 3 and body["offset"] == offset
            seen.extend(m["username"] for m in body["items"])
        assert len(seen) == 8 and len(set(seen)) == 8

        too_big = await alice.get("/api/orgs/page-org/members?limit=101", headers=ha)
        assert too_big.status_code == 422
        too_small = await alice.get("/api/orgs/page-org/members?limit=0", headers=ha)
        assert too_small.status_code == 422
    finally:
        for c in clients:
            await c.aclose()


async def test_cohort_crud_and_membership() -> None:
    alice, ha, _ = await make_user("coh-alice")
    await create_org(alice, ha, "coh-org")
    bob, hb, uid_bob = await make_user("coh-bob")
    await join_via_link_invite(alice, ha, "coh-org", bob, hb)
    _stranger_client, _h_stranger, uid_stranger = await make_user("coh-stranger")

    created = await alice.post(
        "/api/orgs/coh-org/cohorts",
        json={
            "name": "fall-2026",
            "starts_at": "2026-09-01T00:00:00Z",
            "ends_at": "2026-12-20T00:00:00Z",
            "metadata": {"term": "fall"},
        },
        headers=ha,
    )
    assert created.status_code == 201, created.text
    cohort = created.json()
    assert cohort["metadata"] == {"term": "fall"}
    assert cohort["starts_at"].startswith("2026-09-01")

    listing = await bob.get("/api/orgs/coh-org/cohorts", headers=hb)
    assert [c["name"] for c in listing.json()] == ["fall-2026"]

    patched = await alice.patch(
        f"/api/orgs/coh-org/cohorts/{cohort['id']}",
        json={"name": "fall-2026-late", "metadata": {"term": "fall", "room": "B"}},
        headers=ha,
    )
    assert patched.json()["name"] == "fall-2026-late"

    # Only organization members can be added to a cohort.
    refused = await alice.post(
        f"/api/orgs/coh-org/cohorts/{cohort['id']}/members",
        json={"user_id": uid_stranger},
        headers=ha,
    )
    assert refused.status_code == 422

    added = await alice.post(
        f"/api/orgs/coh-org/cohorts/{cohort['id']}/members",
        json={"user_id": uid_bob},
        headers=ha,
    )
    assert added.status_code == 200
    dup = await alice.post(
        f"/api/orgs/coh-org/cohorts/{cohort['id']}/members",
        json={"user_id": uid_bob},
        headers=ha,
    )
    assert dup.status_code == 409

    detail = await bob.get(f"/api/orgs/coh-org/cohorts/{cohort['id']}", headers=hb)
    assert detail.json()["members"][0]["username"] == "coh-bob"
    assert detail.json()["member_count"] == 1

    removed = await alice.delete(
        f"/api/orgs/coh-org/cohorts/{cohort['id']}/members/{uid_bob}", headers=ha
    )
    assert removed.status_code == 200
    re_remove = await alice.delete(
        f"/api/orgs/coh-org/cohorts/{cohort['id']}/members/{uid_bob}", headers=ha
    )
    assert re_remove.status_code == 404

    deleted = await alice.delete(f"/api/orgs/coh-org/cohorts/{cohort['id']}", headers=ha)
    assert deleted.status_code == 200
    gone = await alice.get(f"/api/orgs/coh-org/cohorts/{cohort['id']}", headers=ha)
    assert gone.status_code == 404


async def test_assignment_progress_derivation(db: async_sessionmaker) -> None:
    from openrange.api.learning.models import Enrollment, SectionProgress

    alice, ha, _ = await make_user("prog-alice")
    await create_org(alice, ha, "prog-org")
    lena, hl, uid_lena = await make_user("prog-lena")
    await join_via_link_invite(alice, ha, "prog-org", lena, hl)

    cohort = (
        await alice.post("/api/orgs/prog-org/cohorts", json={"name": "learners"}, headers=ha)
    ).json()
    add = await alice.post(
        f"/api/orgs/prog-org/cohorts/{cohort['id']}/members",
        json={"user_id": uid_lena},
        headers=ha,
    )
    assert add.status_code == 200

    assignment = (
        await alice.post(
            "/api/orgs/prog-org/assignments",
            json={
                "content_kind": "path",
                "content_slug": "foundations-path",
                "cohort_id": cohort["id"],
                "due_at": "2026-12-31T23:59:00Z",
            },
            headers=ha,
        )
    ).json()
    progress_url = f"/api/orgs/prog-org/assignments/{assignment['id']}/progress"

    rows = (await alice.get(progress_url, headers=ha)).json()
    assert rows == [
        {
            "user_id": uid_lena,
            "username": "prog-lena",
            "display_name": "",
            "status": "not_started",
            "percent": 0,
            "last_event_at": None,
        }
    ]

    # Seed the learning read-model directly: half of the four required
    # sections of foundations-path are complete.
    async with db() as session:
        enroll = Enrollment(
            user_id=uuid.UUID(uid_lena),
            path_slug="foundations-path",
            path_version="2.1.0",
            state="active",
        )
        session.add(enroll)
        await session.flush()
        session.add_all(
            [
                SectionProgress(
                    enrollment_id=enroll.id, module_slug="learning-basics", section_id="intro"
                ),
                SectionProgress(
                    enrollment_id=enroll.id, module_slug="learning-basics", section_id="quiz-check"
                ),
            ]
        )
        await session.commit()

    rows = (await alice.get(progress_url, headers=ha)).json()
    assert rows[0]["status"] == "in_progress"
    assert rows[0]["percent"] == 50
    assert rows[0]["last_event_at"] is not None

    # Finish every required section and mark the enrollment complete.
    async with db() as session:
        enroll = (
            (
                await session.execute(
                    select(Enrollment).where(
                        Enrollment.user_id == uuid.UUID(uid_lena),
                        Enrollment.path_slug == "foundations-path",
                    )
                )
            )
            .scalars()
            .one()
        )
        session.add_all(
            [
                SectionProgress(
                    enrollment_id=enroll.id,
                    module_slug="learning-basics",
                    section_id="wrap-up",
                ),
                SectionProgress(
                    enrollment_id=enroll.id,
                    module_slug="capstone-prep",
                    section_id="capstone-intro",
                ),
            ]
        )
        enroll.state = "completed"
        await session.commit()

    rows = (await alice.get(progress_url, headers=ha)).json()
    assert rows[0]["status"] == "completed"
    assert rows[0]["percent"] == 100

    # Optional-branch sections never count toward the required total.
    async with db() as session:
        enroll = (
            (
                await session.execute(
                    select(Enrollment).where(
                        Enrollment.user_id == uuid.UUID(uid_lena),
                        Enrollment.path_slug == "foundations-path",
                    )
                )
            )
            .scalars()
            .one()
        )
        session.add(
            SectionProgress(
                enrollment_id=enroll.id,
                module_slug="advanced-bits",
                section_id="deep-dive",
            )
        )
        await session.commit()
    rows = (await alice.get(progress_url, headers=ha)).json()
    assert rows[0]["percent"] == 100

    # Org-wide assignment covers every member including the owner.
    org_wide = (
        await alice.post(
            "/api/orgs/prog-org/assignments",
            json={"content_kind": "path", "content_slug": "foundations-path"},
            headers=ha,
        )
    ).json()
    wide_rows = (
        await alice.get(f"/api/orgs/prog-org/assignments/{org_wide['id']}/progress", headers=ha)
    ).json()
    assert {r["username"] for r in wide_rows} == {"prog-alice", "prog-lena"}
    owner_row = next(r for r in wide_rows if r["username"] == "prog-alice")
    assert owner_row["status"] == "not_started"

    # Rooms have no completion read-model yet; they stay not_started.
    room_assignment = (
        await alice.post(
            "/api/orgs/prog-org/assignments",
            json={"content_kind": "room", "content_slug": "hint-lab-room"},
            headers=ha,
        )
    ).json()
    room_rows = (
        await alice.get(
            f"/api/orgs/prog-org/assignments/{room_assignment['id']}/progress", headers=ha
        )
    ).json()
    assert all(r["status"] == "not_started" and r["percent"] == 0 for r in room_rows)

    # Validation: unknown content and foreign cohort ids are rejected.
    bad_content = await alice.post(
        "/api/orgs/prog-org/assignments",
        json={"content_kind": "path", "content_slug": "no-such-path"},
        headers=ha,
    )
    assert bad_content.status_code == 404
    bad_cohort = await alice.post(
        "/api/orgs/prog-org/assignments",
        json={
            "content_kind": "path",
            "content_slug": "foundations-path",
            "cohort_id": str(uuid.uuid4()),
        },
        headers=ha,
    )
    assert bad_cohort.status_code == 404


async def test_unauthenticated_access_rejected() -> None:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as anon:
        for method, url, body in [
            ("GET", "/api/orgs/some-org", None),
            ("POST", "/api/orgs", {"name": "anon-org"}),
            ("POST", "/api/invites/deadbeef/accept", None),
        ]:
            res = await anon.request(method, url, json=body)
            assert res.status_code == 401, (url, res.status_code)
