"""Learning engine integration gate (plan Phase 8).

Drives enrollment, prerequisite-ordered progress, server-graded
quizzes, progressive hints, notes, certificates, and RBAC through the
real API against Postgres, with a fixture curriculum on disk.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from openrange.api.learning import content as learning_content
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine
from testshelpers.curriculum import write_curriculum

pytestmark = [pytest.mark.integration]

PATH = "foundations-path"


@pytest.fixture(autouse=True)
def curriculum(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    root = write_curriculum(tmp_path / "content")
    monkeypatch.setenv(learning_content.CONTENT_DIR_ENV, str(root))
    learning_content.clear_caches()
    yield root
    learning_content.clear_caches()


async def make_user(username: str) -> tuple[AsyncClient, dict[str, str]]:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    client = AsyncClient(transport=transport, base_url="http://test", timeout=60)
    res = await client.post(
        "/api/auth/register",
        json={"username": username, "password": "correct-horse-battery"},
    )
    assert res.status_code == 201, res.text
    return client, {"x-csrf-token": res.json()["csrf_token"]}


def _assert_no_answer_key(payload: object) -> None:
    text = str(payload)
    assert "answer_ids" not in text, "bundle answer key leaked"
    assert "explanation" not in text, "quiz explanation leaked to client"


async def enroll(client: AsyncClient, headers: dict[str, str]) -> dict[str, object]:
    res = await client.post(f"/api/learning/paths/{PATH}/enroll", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


async def complete(
    client: AsyncClient,
    headers: dict[str, str],
    module: str,
    section: str,
    expect: int = 200,
) -> dict[str, object]:
    res = await client.post(
        f"/api/learning/modules/{module}/sections/{section}/complete", headers=headers
    )
    assert res.status_code == expect, res.text
    return res.json()


async def test_happy_path_enroll_quiz_hints_certificate() -> None:
    alice, headers_a = await make_user("learnalice")

    # Catalog shows the path with no enrollment yet.
    listed = await alice.get("/api/learning/paths", headers=headers_a)
    assert listed.status_code == 200, listed.text
    entry = next(p for p in listed.json() if p["slug"] == PATH)
    assert entry["enrollment_state"] is None
    _assert_no_answer_key(listed.json())

    detail = await alice.get(f"/api/learning/paths/{PATH}", headers=headers_a)
    assert detail.status_code == 200
    tree = detail.json()
    _assert_no_answer_key(tree)
    optional_flags = {m["slug"]: m["optional_branch"] for m in tree["modules"]}
    assert optional_flags == {
        "learning-basics": False,
        "advanced-bits": True,
        "capstone-prep": False,
    }
    intro = tree["modules"][0]["sections"][0]
    assert intro["prerequisites"] == []

    # Certificate before starting is a conflict; unknown paths 404.
    early = await alice.get(f"/api/learning/certificates/{PATH}", headers=headers_a)
    assert early.status_code in (404, 409)
    missing = await alice.get("/api/learning/certificates/nope", headers=headers_a)
    assert missing.status_code == 404

    enrolled = await enroll(alice, headers_a)
    assert enrolled["state"] == "active"
    dup = await alice.post(f"/api/learning/paths/{PATH}/enroll", headers=headers_a)
    assert dup.status_code == 409

    # Prerequisite enforcement: the last required section cannot be
    # completed before earlier required sections.
    blocked = await complete(alice, headers_a, "capstone-prep", "capstone-intro", expect=409)
    assert "prerequisite" in str(blocked)

    # Optional branch is completable at any time.
    optional_done = await complete(alice, headers_a, "advanced-bits", "deep-dive")
    assert optional_done["path_completed"] is False

    # Ordered progress on the required module.
    await complete(alice, headers_a, "learning-basics", "intro")
    again = await complete(alice, headers_a, "learning-basics", "intro")
    assert again["already_completed"] is True

    # Quiz grading: fail first, then pass. Attempts are recorded.
    failed = await alice.post(
        "/api/learning/quiz/quiz-check/attempt",
        json={"answers": {"q-check": ["wrong-opt"]}},
        headers=headers_a,
    )
    assert failed.status_code == 200 and failed.json()["passed"] is False
    _assert_no_answer_key(failed.json())
    passed = await alice.post(
        "/api/learning/quiz/quiz-check/attempt",
        json={"answers": {"q-check": ["right-opt"]}},
        headers=headers_a,
    )
    assert passed.json()["passed"] is True
    unknown_quiz = await alice.post(
        "/api/learning/quiz/nope/attempt",
        json={"answers": {}},
        headers=headers_a,
    )
    assert unknown_quiz.status_code == 404

    await complete(alice, headers_a, "learning-basics", "quiz-check")
    await complete(alice, headers_a, "learning-basics", "wrap-up")

    # Pause blocks learning actions; resume restores them.
    paused = await alice.post(f"/api/learning/paths/{PATH}/pause", headers=headers_a)
    assert paused.json()["state"] == "paused"
    await complete(alice, headers_a, "capstone-prep", "capstone-intro", expect=409)
    resumed = await alice.post(f"/api/learning/paths/{PATH}/resume", headers=headers_a)
    assert resumed.json()["state"] == "active"

    # Finishing every required section completes the path.
    final = await complete(alice, headers_a, "capstone-prep", "capstone-intro")
    assert final["path_completed"] is True

    # Progressive hints against the capstone room.
    hint1 = await alice.post("/api/learning/hints/hint-lab-room/find-leak", headers=headers_a)
    assert hint1.status_code == 200
    body1 = hint1.json()
    assert body1["tier"] == 1 and body1["cost"] == 5
    assert "solution" not in body1 or body1["solution"] is None
    hint2 = await alice.post("/api/learning/hints/hint-lab-room/find-leak", headers=headers_a)
    assert hint2.json()["tier"] == 2 and hint2.json()["cost"] == 10
    solution = await alice.post("/api/learning/hints/hint-lab-room/find-leak", headers=headers_a)
    sol_body = solution.json()
    assert sol_body["solution"], sol_body
    bad_task = await alice.post("/api/learning/hints/hint-lab-room/no-such-task", headers=headers_a)
    assert bad_task.status_code == 404
    bad_room = await alice.post("/api/learning/hints/no-such-room/find-leak", headers=headers_a)
    assert bad_room.status_code == 404

    # Certificate issues once, idempotently, with signed evidence.
    cert = await alice.get(f"/api/learning/certificates/{PATH}", headers=headers_a)
    assert cert.status_code == 200, cert.text
    cert_body = cert.json()
    assert cert_body["path_version"] == "2.1.0"
    payload = cert_body["payload"]
    assert len(payload["completion_hash"]) == 64
    assert payload["signature"]
    again_cert = await alice.get(f"/api/learning/certificates/{PATH}", headers=headers_a)
    assert again_cert.json()["id"] == cert_body["id"]

    # Raw progress view: XP-safe counters only.
    progress = await alice.get("/api/learning/me/progress", headers=headers_a)
    assert progress.status_code == 200
    prog = progress.json()
    mine = prog["enrollments"][0]
    assert mine["path_slug"] == PATH
    assert mine["hint_cost_total"] == 15
    assert mine["quiz_attempts"] == 2
    totals = {m["slug"]: m for m in mine["modules"]}
    assert totals["learning-basics"]["sections_completed"] == 3
    assert prog["certificates"][0]["id"] == cert_body["id"]

    await alice.aclose()


async def test_pause_resume_lifecycle() -> None:
    bob, headers_b = await make_user("learnbob")
    await enroll(bob, headers_b)
    paused = await bob.post(f"/api/learning/paths/{PATH}/pause", headers=headers_b)
    assert paused.status_code == 200
    double_pause = await bob.post(f"/api/learning/paths/{PATH}/pause", headers=headers_b)
    assert double_pause.status_code == 409
    resumed = await bob.post(f"/api/learning/paths/{PATH}/resume", headers=headers_b)
    assert resumed.status_code == 200
    double_resume = await bob.post(f"/api/learning/paths/{PATH}/resume", headers=headers_b)
    assert double_resume.status_code == 409
    not_enrolled = await bob.post("/api/learning/paths/nope/pause", headers=headers_b)
    assert not_enrolled.status_code == 404
    await bob.aclose()


async def test_notes_autosave_and_search() -> None:
    carol, headers_c = await make_user("learncarol")
    dave, headers_d = await make_user("learndave")

    saved = await carol.put(
        "/api/learning/notes",
        json={"scope": "module", "ref": PATH, "body": "remember **ordering**"},
        headers=headers_c,
    )
    assert saved.status_code == 200, saved.text
    # Autosave overwrites the same note instead of duplicating it.
    resaved = await carol.put(
        "/api/learning/notes",
        json={"scope": "module", "ref": PATH, "body": "autosaved v2"},
        headers=headers_c,
    )
    assert resaved.status_code == 200
    fetched = await carol.get(
        "/api/learning/notes",
        params={"scope": "module", "ref": PATH},
        headers=headers_c,
    )
    assert fetched.json()["body"] == "autosaved v2"

    found = await carol.get(
        "/api/learning/notes/search", params={"q": "autosaved"}, headers=headers_c
    )
    assert found.status_code == 200
    assert [n["ref"] for n in found.json()] == [PATH]
    empty = await carol.get(
        "/api/learning/notes/search", params={"q": "zzz-nothing"}, headers=headers_c
    )
    assert empty.json() == []

    # Notes are private per user.
    stolen = await dave.get(
        "/api/learning/notes",
        params={"scope": "module", "ref": PATH},
        headers=headers_d,
    )
    assert stolen.status_code == 404
    cross = await dave.get(
        "/api/learning/notes/search", params={"q": "autosaved"}, headers=headers_d
    )
    assert cross.json() == []

    bad_scope = await carol.put(
        "/api/learning/notes",
        json={"scope": "user", "ref": "x", "body": "y"},
        headers=headers_c,
    )
    assert bad_scope.status_code == 422
    await carol.aclose()
    await dave.aclose()


async def test_rbac_instructor_reads_enrollment(db_engine: AsyncEngine) -> None:
    eve, headers_e = await make_user("learneve")
    mallory, headers_m = await make_user("learnmallory")
    teacher, headers_t = await make_user("teachuser")
    admin, headers_adm = await make_user("rootadmin2")

    enrollment = await enroll(eve, headers_e)
    eid = str(enrollment["enrollment_id"])

    # Grant instructor role to teacher directly (seeded roles exist).
    from openrange.api.db import session_factory
    from openrange.api.users.models import Role, User, UserRole

    assert session_factory is not None
    async with session_factory() as db:
        instructor_role = (
            await db.execute(select(Role).where(Role.name == "instructor"))
        ).scalar_one()
        admin_role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one()
        teacher_row = (
            await db.execute(select(User).where(User.username == "teachuser"))
        ).scalar_one()
        admin_row = (
            await db.execute(select(User).where(User.username == "rootadmin2"))
        ).scalar_one()
        db.add(UserRole(user_id=teacher_row.id, role_id=instructor_role.id))
        db.add(UserRole(user_id=admin_row.id, role_id=admin_role.id))
        await db.commit()

    own = await eve.get(f"/api/learning/enrollments/{eid}", headers=headers_e)
    assert own.status_code == 200, own.text
    assert own.json()["user_id"]
    assert own.json()["completed_sections"] == []

    by_teacher = await teacher.get(f"/api/learning/enrollments/{eid}", headers=headers_t)
    assert by_teacher.status_code == 200, by_teacher.text
    assert by_teacher.json()["user_id"]

    by_admin = await admin.get(f"/api/learning/enrollments/{eid}", headers=headers_adm)
    assert by_admin.status_code == 200

    # Another learner cannot see eve's enrollment at all.
    denied = await mallory.get(f"/api/learning/enrollments/{eid}", headers=headers_m)
    assert denied.status_code == 404

    ghost = await eve.get(f"/api/learning/enrollments/{uuid.uuid4()}", headers=headers_e)
    assert ghost.status_code == 404

    await eve.aclose()
    await mallory.aclose()
    await teacher.aclose()
    await admin.aclose()
