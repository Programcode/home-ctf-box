"""Content Studio workspace safety: path traversal, zip-slip, symlinks."""

from __future__ import annotations

import io
import uuid as uuid_mod
import zipfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from openrange.api.auth.service import AuthError
from openrange.api.studio import service as studio_service
from openrange.api.studio.models import ContentDraft

pytestmark = [pytest.mark.integration]

PASSWORD = "correct-horse-battery"


async def make_user(username: str) -> tuple[AsyncClient, dict[str, str], str]:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    client = AsyncClient(transport=transport, base_url="http://test", timeout=60)
    res = await client.post("/api/auth/register", json={"username": username, "password": PASSWORD})
    assert res.status_code == 201, res.text
    return client, {"x-csrf-token": res.json()["csrf_token"]}, res.json()["id"]


@pytest.fixture(autouse=True)
def studio_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    staging = tmp_path / "content-staging"
    real = tmp_path / "real-content"
    staging.mkdir()
    real.mkdir()
    monkeypatch.setenv(studio_service.STAGING_ROOT_ENV, str(staging))
    monkeypatch.setenv(studio_service.CONTENT_DIR_ENV, str(real))
    return staging, real


async def new_room_draft(client: AsyncClient, headers: dict[str, str]) -> tuple[str, Path]:
    created = await client.post(
        "/api/studio/drafts", json={"kind": "room", "slug": "safety-room"}, headers=headers
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    return draft_id, studio_service.staging_root() / draft_id


async def test_put_rejects_traversal_paths() -> None:
    author, ha, _ = await make_user("studio-trav-author")
    draft_id, _workspace = await new_room_draft(author, ha)

    # Literal dot segments are normalized by HTTP clients, so the wire
    # form is percent-encoded; the server must still see and reject them.
    evils = ["..%2fescape.txt", "..%2f..%2fescape.txt", "sub%2f..%2f..%2fescape.txt"]
    for evil in evils:
        res = await author.put(
            f"/api/studio/drafts/{draft_id}/files/{evil}", content="nope", headers=ha
        )
        assert res.status_code == 422, (evil, res.text)

    absolute = await author.put(
        f"/api/studio/drafts/{draft_id}/files//etc/openrange-evil.txt",
        content="nope",
        headers=ha,
    )
    assert absolute.status_code == 422

    staging = studio_service.staging_root()
    assert sorted(p.name for p in staging.iterdir()) == [draft_id]


async def test_get_file_rejects_traversal_queries() -> None:
    author, ha, _ = await make_user("studio-qtrav-author")
    draft_id, _workspace = await new_room_draft(author, ha)

    for evil in ["../secret.txt", "../../etc/passwd", "/etc/passwd", "a/../../b"]:
        res = await author.get(
            f"/api/studio/drafts/{draft_id}/file", params={"path": evil}, headers=ha
        )
        assert res.status_code == 422, (evil, res.text)


async def test_service_write_file_blocks_every_escape(tmp_path: Path) -> None:
    draft = ContentDraft(
        id=uuid_mod.uuid4(),
        kind="room",
        slug="safety-room",
        content_root=str(studio_service.staging_root() / "ws"),
    )
    root = studio_service.staging_root() / "ws"
    root.mkdir(parents=True)
    for evil in ["../x.txt", "..\\x.txt", "/etc/x.txt", "a/../../x.txt", "C:/x.txt"]:
        with pytest.raises(AuthError):
            studio_service.write_file(draft, evil, b"nope")


async def test_zip_slip_entries_are_rejected() -> None:
    author, ha, _ = await make_user("studio-zipslip-author")
    draft_id, workspace = await new_room_draft(author, ha)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../escaped.txt", "boom")
        zf.writestr("/absolute.txt", "boom")
    uploaded = await author.post(
        f"/api/studio/drafts/{draft_id}/bundle",
        files={"file": ("evil.zip", buf.getvalue(), "application/zip")},
        headers=ha,
    )
    assert uploaded.status_code == 422
    staging = studio_service.staging_root()
    assert not (staging.parent / "escaped.txt").exists()
    assert not (staging / "escaped.txt").exists()
    assert list(workspace.rglob("absolute.txt")) == []


async def test_zip_safe_entries_extract_and_unsafe_abort_first() -> None:
    author, ha, _ = await make_user("studio-zipmix-author")
    draft_id, workspace = await new_room_draft(author, ha)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("rooms/safety-room/room.yaml", "kind: Room\n")
        zf.writestr("../escaped-after-good.txt", "boom")
    uploaded = await author.post(
        f"/api/studio/drafts/{draft_id}/bundle",
        files={"file": ("mixed.zip", buf.getvalue(), "application/zip")},
        headers=ha,
    )
    assert uploaded.status_code == 422
    assert list(workspace.rglob("escaped-after-good.txt")) == []
    # Entries extracted before the abort stay put; validation catches any
    # half-uploaded tree later.
    assert (workspace / "rooms" / "safety-room" / "room.yaml").is_file()


async def test_zip_symlink_members_are_rejected() -> None:
    author, ha, _ = await make_user("studio-zip-link-author")
    draft_id, _workspace = await new_room_draft(author, ha)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("link.yaml")
        info.external_attr = 0o120777 << 16
        zf.writestr(info, "/etc/passwd")
    uploaded = await author.post(
        f"/api/studio/drafts/{draft_id}/bundle",
        files={"file": ("links.zip", buf.getvalue(), "application/zip")},
        headers=ha,
    )
    assert uploaded.status_code == 422
    assert "symlink" in uploaded.json()["detail"]


async def test_safe_join_symlink_escape_is_blocked(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("classified")

    link = root / "innocent"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(AuthError):
        studio_service.safe_join(root, "innocent/secret.txt")
    # Even the link itself refuses to resolve through an outside target.
    with pytest.raises(AuthError):
        studio_service.safe_join(root, "innocent")
    with pytest.raises(AuthError):
        studio_service.safe_join(root, "../outside/secret.txt")
    with pytest.raises(AuthError):
        studio_service.safe_join(root, "/etc/passwd")
    with pytest.raises(AuthError):
        studio_service.safe_join(root, "")


async def test_read_file_refuses_symlinked_files(tmp_path: Path) -> None:
    author, ha, _ = await make_user("studio-readlink-author")
    draft_id, workspace = await new_room_draft(author, ha)
    bundle = workspace / "rooms" / "safety-room"

    outside = tmp_path / "outside-file.txt"
    outside.write_text("classified")
    (bundle / "leak.yaml").symlink_to(outside)

    draft = ContentDraft(
        id=uuid_mod.UUID(draft_id),
        kind="room",
        slug="safety-room",
        content_root=str(workspace),
    )

    listing = await author.get(f"/api/studio/drafts/{draft_id}/files", headers=ha)
    assert listing.json()["files"] == []  # symlinks are hidden from listings

    with pytest.raises(AuthError):
        studio_service.read_file(draft, "rooms/safety-room/leak.yaml")


async def test_bundle_size_and_entry_limits() -> None:
    author, ha, _ = await make_user("studio-limits-author")
    draft_id, _workspace = await new_room_draft(author, ha)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(2100):
            zf.writestr(f"f{i:05}.txt", "x")
    too_many = await author.post(
        f"/api/studio/drafts/{draft_id}/bundle",
        files={"file": ("many.zip", buf.getvalue(), "application/zip")},
        headers=ha,
    )
    assert too_many.status_code == 413

    not_a_zip = await author.post(
        f"/api/studio/drafts/{draft_id}/bundle",
        files={"file": ("garbage.zip", b"this is not a zip", "application/zip")},
        headers=ha,
    )
    assert not_a_zip.status_code == 422


async def test_delete_removes_staging_workspace() -> None:
    author, ha, _ = await make_user("studio-rm-author")
    draft_id, workspace = await new_room_draft(author, ha)
    put = await author.put(
        f"/api/studio/drafts/{draft_id}/files/rooms/safety-room/room.yaml",
        content="kind: Room\n",
        headers=ha,
    )
    assert put.status_code == 200
    assert workspace.is_dir()

    deleted = await author.delete(f"/api/studio/drafts/{draft_id}", headers=ha)
    assert deleted.status_code == 200
    assert not workspace.exists()

    ghost = await author.get(f"/api/studio/drafts/{draft_id}", headers=ha)
    assert ghost.status_code == 404
