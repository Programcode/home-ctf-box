"""Content Studio workflow gates (plan Phase 10).

Drives draft creation, file upload, validation, submission, review,
and atomic publishing through the real API against Postgres, with
staging and real content trees pointed at temp directories.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from openrange.api.studio import service as studio_service
from openrange.content.linting import Finding
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine
from testshelpers.curriculum import MODULE_BASICS_YAML, write_curriculum

pytestmark = [pytest.mark.integration]

PASSWORD = "correct-horse-battery"

ROOM_YAML_TEMPLATE = """\
apiVersion: openrange.io/v1
kind: Room
metadata:
  slug: {slug}
  title: Studio Fixture Room
  version: 1.0.0
  difficulty: easy
  points: 100
  estimated_minutes: 15
spec:
  track: web-foundations
  type: challenge
  summary: Minimal challenge room used by content studio publishing tests end to end.
  objectives:
    - Exercise the studio draft and publish workflow safely.
    - Prove validation gates run before content lands for learners.
  scope:
    allowed_targets:
      - http://target:8000
  safety:
    simulated_only: true
    no_real_malware: true
    reviewer_notes: Read-only fixture target used only in automated studio tests.
  target:
    build_context: ./target
    ports:
      - 8000
    healthcheck:
      http_path: /healthz
  tasks:
    - id: find-the-flag
      title: Find the fixture flag
      prompt: Retrieve the flag value exposed by the fixture target health page.
      points: 100
      hints:
        - cost: 0
          text: The value appears verbatim in the target response headers.
        - cost: 10
          text: Inspect the response headers of the health endpoint closely.
      solution: Send a GET request to the target and read the flag header value directly.
      validator:
        type: exact
        value: FLAG{{studio-fixture-{marker}}}
"""

SOLVER_PY = """\
def solve(ctx):
    return ctx.expected_flags
"""

DOCKERFILE = "FROM python:3.12-slim\n"


def room_files(slug: str, marker: str = "one") -> dict[str, str]:
    return {
        "room.yaml": ROOM_YAML_TEMPLATE.format(slug=slug, marker=marker),
        "solver/solver.py": SOLVER_PY,
        "target/Dockerfile": DOCKERFILE,
        "README.md": "# Studio Fixture Room\n\nA minimal room used by studio tests.\n",
    }


async def make_user(username: str) -> tuple[AsyncClient, dict[str, str], str]:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    client = AsyncClient(transport=transport, base_url="http://test", timeout=60)
    res = await client.post("/api/auth/register", json={"username": username, "password": PASSWORD})
    assert res.status_code == 201, res.text
    return client, {"x-csrf-token": res.json()["csrf_token"]}, res.json()["id"]


async def grant_role(db_engine: AsyncEngine, username: str, role_name: str) -> None:
    from openrange.api.db import session_factory
    from openrange.api.users.models import Role, User, UserRole

    assert session_factory is not None
    async with session_factory() as db:
        role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one()
        user = (await db.execute(select(User).where(User.username == username))).scalar_one()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()


@pytest.fixture(autouse=True)
def studio_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    staging = tmp_path / "content-staging"
    real = tmp_path / "real-content"
    staging.mkdir()
    real.mkdir()
    monkeypatch.setenv(studio_service.STAGING_ROOT_ENV, str(staging))
    monkeypatch.setenv(studio_service.CONTENT_DIR_ENV, str(real))
    return staging, real


async def create_room_draft(client: AsyncClient, headers: dict[str, str], slug: str) -> str:
    res = await client.post(
        "/api/studio/drafts", json={"kind": "room", "slug": slug}, headers=headers
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def upload_room_files(
    client: AsyncClient,
    headers: dict[str, str],
    draft_id: str,
    slug: str = "studio-gate-room",
    marker: str = "one",
) -> None:
    # Uploads are rooted at the draft workspace; room bundles live under
    # rooms/<slug>/ just like in the real content tree.
    for path, text in room_files(slug, marker).items():
        res = await client.put(
            f"/api/studio/drafts/{draft_id}/files/rooms/{slug}/{path}",
            content=text,
            headers=headers,
        )
        assert res.status_code == 200, res.text


async def approve_and_publish(
    reviewer: tuple[AsyncClient, dict[str, str]],
    admin: tuple[AsyncClient, dict[str, str]],
    draft_id: str,
) -> None:
    reviewer_client, reviewer_headers = reviewer
    admin_client, admin_headers = admin
    res = await reviewer_client.post(
        f"/api/studio/drafts/{draft_id}/review",
        json={"state": "approved", "note": "looks good"},
        headers=reviewer_headers,
    )
    assert res.status_code == 200, res.text
    res = await admin_client.post(f"/api/studio/drafts/{draft_id}/publish", headers=admin_headers)
    assert res.status_code == 200, res.text


async def test_happy_path_create_upload_validate_submit_approve_publish(
    db_engine: AsyncEngine,
) -> None:
    author, ha, _ = await make_user("studio-author")
    reviewer, hr, _ = await make_user("studio-reviewer")
    await grant_role(db_engine, "studio-reviewer", "reviewer")
    admin, hadm, _ = await make_user("studio-admin")
    await grant_role(db_engine, "studio-admin", "admin")

    draft_id = await create_room_draft(author, ha, "studio-gate-room")
    await upload_room_files(author, ha, draft_id)

    tree = await author.get(f"/api/studio/drafts/{draft_id}/files", headers=ha)
    assert tree.status_code == 200
    prefix = "rooms/studio-gate-room/"
    paths = {f["path"] for f in tree.json()["files"]}
    assert paths == {
        f"{prefix}room.yaml",
        f"{prefix}solver/solver.py",
        f"{prefix}target/Dockerfile",
        f"{prefix}README.md",
    }

    raw = await author.get(
        f"/api/studio/drafts/{draft_id}/file",
        params={"path": f"{prefix}room.yaml"},
        headers=ha,
    )
    assert raw.status_code == 200
    assert "slug: studio-gate-room" in raw.text

    verdict = await author.post(f"/api/studio/drafts/{draft_id}/validate", headers=ha)
    assert verdict.status_code == 200, verdict.text
    body = verdict.json()
    assert body["ok"] is True, body["findings"]
    assert all(f["severity"] != "error" for f in body["findings"])

    submitted = await author.post(f"/api/studio/drafts/{draft_id}/submit", headers=ha)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "in_review"

    await approve_and_publish((reviewer, hr), (admin, hadm), draft_id)

    detail = await author.get(f"/api/studio/drafts/{draft_id}", headers=ha)
    assert detail.json()["status"] == "published"

    events = await author.get(f"/api/studio/drafts/{draft_id}/events", headers=ha)
    assert [e["event"] for e in events.json()] == ["submitted", "approved", "published"]


async def test_published_files_land_in_real_tree(
    studio_dirs: tuple[Path, Path], db_engine: AsyncEngine
) -> None:
    author, ha, _ = await make_user("studio-land-author")
    reviewer, hr, _ = await make_user("studio-land-reviewer")
    await grant_role(db_engine, "studio-land-reviewer", "reviewer")
    admin, hadm, _ = await make_user("studio-land-admin")
    await grant_role(db_engine, "studio-land-admin", "admin")

    draft_id = await create_room_draft(author, ha, "studio-gate-room")
    await upload_room_files(author, ha, draft_id)
    await author.post(f"/api/studio/drafts/{draft_id}/submit", headers=ha)
    await approve_and_publish((reviewer, hr), (admin, hadm), draft_id)

    _staging, real = studio_dirs
    landed = real / "rooms" / "studio-gate-room"
    assert (landed / "room.yaml").is_file()
    assert (landed / "solver" / "solver.py").is_file()
    assert (landed / "target" / "Dockerfile").is_file()

    # No staging leftovers beside the published bundle.
    leftovers = [p.name for p in (real / "rooms").iterdir() if p.name.startswith(".")]
    assert leftovers == []


async def test_validation_failure_blocks_publish(
    studio_dirs: tuple[Path, Path], db_engine: AsyncEngine
) -> None:
    author, ha, _ = await make_user("studio-broken-author")
    reviewer, hr, _ = await make_user("studio-broken-reviewer")
    await grant_role(db_engine, "studio-broken-reviewer", "reviewer")
    admin, hadm, _ = await make_user("studio-broken-admin")
    await grant_role(db_engine, "studio-broken-admin", "admin")

    draft_id = await create_room_draft(author, ha, "broken-room")
    files = room_files("broken-room")
    del files["solver/solver.py"]
    for path, text in files.items():
        put = await author.put(
            f"/api/studio/drafts/{draft_id}/files/rooms/broken-room/{path}",
            content=text,
            headers=ha,
        )
        assert put.status_code == 200

    verdict = await author.post(f"/api/studio/drafts/{draft_id}/validate", headers=ha)
    body = verdict.json()
    assert body["ok"] is False
    assert any(f["rule"] == "solver" for f in body["findings"])

    await author.post(f"/api/studio/drafts/{draft_id}/submit", headers=ha)

    review = await reviewer.post(
        f"/api/studio/drafts/{draft_id}/review",
        json={"state": "approved", "note": "ok"},
        headers=hr,
    )
    assert review.status_code == 200

    _staging, real = studio_dirs
    publish = await admin.post(f"/api/studio/drafts/{draft_id}/publish", headers=hadm)
    assert publish.status_code == 409
    assert not (real / "rooms" / "broken-room").exists()

    detail = await author.get(f"/api/studio/drafts/{draft_id}", headers=ha)
    assert detail.json()["status"] == "approved"


async def test_publish_without_approval_conflicts(db_engine: AsyncEngine) -> None:
    author, ha, _ = await make_user("studio-noapp-author")
    admin, hadm, _ = await make_user("studio-noapp-admin")
    await grant_role(db_engine, "studio-noapp-admin", "admin")

    draft_id = await create_room_draft(author, ha, "unapproved-room")
    await upload_room_files(author, ha, draft_id)
    await author.post(f"/api/studio/drafts/{draft_id}/submit", headers=ha)

    publish = await admin.post(f"/api/studio/drafts/{draft_id}/publish", headers=hadm)
    assert publish.status_code == 409


async def test_non_reviewer_cannot_approve_and_author_cannot_self_review(
    db_engine: AsyncEngine,
) -> None:
    author, ha, _ = await make_user("studio-selfrev-author")
    stranger, hs, _ = await make_user("studio-selfrev-stranger")
    reviewer, hr, _ = await make_user("studio-selfrev-reviewer")
    await grant_role(db_engine, "studio-selfrev-reviewer", "reviewer")

    draft_id = await create_room_draft(author, ha, "self-review-room")
    await upload_room_files(author, ha, draft_id)
    await author.post(f"/api/studio/drafts/{draft_id}/submit", headers=ha)

    # A plain user with no stake cannot even see the draft.
    peek = await stranger.get(f"/api/studio/drafts/{draft_id}", headers=hs)
    assert peek.status_code == 404
    denied = await stranger.post(
        f"/api/studio/drafts/{draft_id}/review",
        json={"state": "approved", "note": "ship it"},
        headers=hs,
    )
    assert denied.status_code == 404

    self_review = await author.post(
        f"/api/studio/drafts/{draft_id}/review",
        json={"state": "approved", "note": "trust me"},
        headers=ha,
    )
    assert self_review.status_code == 403

    ok_review = await reviewer.post(
        f"/api/studio/drafts/{draft_id}/review",
        json={"state": "changes_requested", "note": "add a lesson"},
        headers=hr,
    )
    assert ok_review.status_code == 200
    assert ok_review.json()["status"] == "changes_requested"


async def test_atomic_rollback_on_post_copy_lint_failure(
    studio_dirs: tuple[Path, Path],
    db_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    author, ha, _ = await make_user("studio-atomic-author")
    reviewer, hr, _ = await make_user("studio-atomic-reviewer")
    await grant_role(db_engine, "studio-atomic-reviewer", "reviewer")
    admin, hadm, _ = await make_user("studio-atomic-admin")
    await grant_role(db_engine, "studio-atomic-admin", "admin")

    # Round one publishes a good bundle into the real tree.
    first = await create_room_draft(author, ha, "atomic-room")
    await upload_room_files(author, ha, first, slug="atomic-room", marker="original")
    await author.post(f"/api/studio/drafts/{first}/submit", headers=ha)
    await approve_and_publish((reviewer, hr), (admin, hadm), first)
    _staging, real = studio_dirs
    original = (real / "rooms" / "atomic-room" / "room.yaml").read_text()
    assert "FLAG{studio-fixture-original}" in original

    # Round two carries valid content but the post-copy lint is rigged
    # to fail, forcing a rollback of the real tree.
    second = await create_room_draft(author, ha, "atomic-room")
    await upload_room_files(author, ha, second, slug="atomic-room", marker="replacement")
    await author.post(f"/api/studio/drafts/{second}/submit", headers=ha)
    await reviewer.post(
        f"/api/studio/drafts/{second}/review",
        json={"state": "approved", "note": "ok"},
        headers=hr,
    )

    def failing_lint(kind: str, bundle_dir: Path) -> list[Finding]:
        return [Finding("error", "injected", "post-copy lint failure injected by test")]

    monkeypatch.setattr(studio_service, "lint_published_bundle", failing_lint)
    failed = await admin.post(f"/api/studio/drafts/{second}/publish", headers=hadm)
    assert failed.status_code == 409

    rolled_back = (real / "rooms" / "atomic-room" / "room.yaml").read_text()
    assert "FLAG{studio-fixture-original}" in rolled_back
    assert "FLAG{studio-fixture-replacement}" not in rolled_back
    leftovers = [p.name for p in (real / "rooms").iterdir() if p.name.startswith(".")]
    assert leftovers == []

    detail = await author.get(f"/api/studio/drafts/{second}", headers=ha)
    assert detail.json()["status"] == "approved"
    events = await author.get(f"/api/studio/drafts/{second}/events", headers=ha)
    assert [e["event"] for e in events.json()] == ["submitted", "approved"]


async def test_events_audit_trail_is_ordered(db_engine: AsyncEngine) -> None:
    author, ha, _ = await make_user("studio-events-author")
    reviewer, hr, _ = await make_user("studio-events-reviewer")
    await grant_role(db_engine, "studio-events-reviewer", "reviewer")

    draft_id = await create_room_draft(author, ha, "events-room")
    await upload_room_files(author, ha, draft_id)
    await author.post(f"/api/studio/drafts/{draft_id}/submit", headers=ha)
    await reviewer.post(
        f"/api/studio/drafts/{draft_id}/review",
        json={"state": "changes_requested", "note": "tighten the prompt"},
        headers=hr,
    )
    # Re-submit after changes, then get an approval.
    await author.post(f"/api/studio/drafts/{draft_id}/submit", headers=ha)
    await reviewer.post(
        f"/api/studio/drafts/{draft_id}/review",
        json={"state": "approved", "note": "better now"},
        headers=hr,
    )

    events = await author.get(f"/api/studio/drafts/{draft_id}/events", headers=ha)
    sequence = [(e["event"], e["detail"].get("note")) for e in events.json()]
    assert sequence == [
        ("submitted", None),
        ("rejected", "tighten the prompt"),
        ("submitted", None),
        ("approved", "better now"),
    ]
    timestamps = [e["created_at"] for e in events.json()]
    assert timestamps == sorted(timestamps)


async def test_isolation_list_delete_rules(db_engine: AsyncEngine) -> None:
    owner, ho, _ = await make_user("studio-iso-owner")
    other, hx, _ = await make_user("studio-iso-other")
    admin, hadm, _ = await make_user("studio-iso-admin")
    await grant_role(db_engine, "studio-iso-admin", "admin")

    draft_id = await create_room_draft(owner, ho, "isolated-room")

    hidden = await other.get(f"/api/studio/drafts/{draft_id}", headers=hx)
    assert hidden.status_code == 404
    listing = await other.get("/api/studio/drafts", headers=hx)
    assert listing.json() == []
    admin_view = await admin.get("/api/studio/drafts", headers=hadm)
    assert len(admin_view.json()) == 1

    forbidden_edit = await other.put(
        f"/api/studio/drafts/{draft_id}/files/evil.txt", content="x", headers=hx
    )
    assert forbidden_edit.status_code == 404
    forbidden_delete = await other.delete(f"/api/studio/drafts/{draft_id}", headers=hx)
    assert forbidden_delete.status_code == 404

    deleted = await owner.delete(f"/api/studio/drafts/{draft_id}", headers=ho)
    assert deleted.status_code == 200
    gone = await owner.get(f"/api/studio/drafts/{draft_id}", headers=ho)
    assert gone.status_code == 404


async def test_bundle_zip_roundtrip_publishes(
    studio_dirs: tuple[Path, Path], db_engine: AsyncEngine
) -> None:
    author, ha, _ = await make_user("studio-zip-author")
    reviewer, hr, _ = await make_user("studio-zip-reviewer")
    await grant_role(db_engine, "studio-zip-reviewer", "reviewer")
    admin, hadm, _ = await make_user("studio-zip-admin")
    await grant_role(db_engine, "studio-zip-admin", "admin")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, text in room_files("zipped-room").items():
            zf.writestr(f"rooms/zipped-room/{path}", text)

    created = await author.post(
        "/api/studio/drafts", json={"kind": "room", "slug": "zipped-room"}, headers=ha
    )
    draft_id = created.json()["id"]
    uploaded = await author.post(
        f"/api/studio/drafts/{draft_id}/bundle",
        files={"file": ("bundle.zip", buf.getvalue(), "application/zip")},
        headers=ha,
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["extracted"] == 4

    verdict = await author.post(f"/api/studio/drafts/{draft_id}/validate", headers=ha)
    assert verdict.json()["ok"] is True

    await author.post(f"/api/studio/drafts/{draft_id}/submit", headers=ha)
    await approve_and_publish((reviewer, hr), (admin, hadm), draft_id)

    _staging, real = studio_dirs
    assert (real / "rooms" / "zipped-room" / "room.yaml").is_file()


async def test_module_and_path_kinds_validate(
    studio_dirs: tuple[Path, Path], db_engine: AsyncEngine
) -> None:
    author, ha, _ = await make_user("studio-kinds-author")
    staging, _real = studio_dirs

    module = await author.post(
        "/api/studio/drafts", json={"kind": "module", "slug": "learning-basics"}, headers=ha
    )
    module_id = module.json()["id"]
    put = await author.put(
        f"/api/studio/drafts/{module_id}/files/modules/learning-basics/module.yaml",
        content=MODULE_BASICS_YAML,
        headers=ha,
    )
    assert put.status_code == 200
    verdict = await author.post(f"/api/studio/drafts/{module_id}/validate", headers=ha)
    assert verdict.status_code == 200
    assert verdict.json()["ok"] is True, verdict.json()["findings"]

    seed = write_curriculum(staging / "seed")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path in sorted(seed.rglob("*")):
            if path.is_file():
                zf.writestr(path.relative_to(seed).as_posix(), path.read_text())

    path_draft = await author.post(
        "/api/studio/drafts", json={"kind": "path", "slug": "foundations-path"}, headers=ha
    )
    path_id = path_draft.json()["id"]
    uploaded = await author.post(
        f"/api/studio/drafts/{path_id}/bundle",
        files={"file": ("curriculum.zip", buf.getvalue(), "application/zip")},
        headers=ha,
    )
    assert uploaded.status_code == 200, uploaded.text
    verdict = await author.post(f"/api/studio/drafts/{path_id}/validate", headers=ha)
    assert verdict.json()["ok"] is True, verdict.json()["findings"]
