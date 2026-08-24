"""Jeopardy challenge gates: flag verification, dynamic scoring, files,
anti-spray signals, and RBAC — through the real API against Postgres."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from openrange.api.challenges import service as challenges_service
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.integration]

PASSWORD = "correct-horse-battery"

DECAY = {"initial": 1000, "minimum": 100, "solves_to_floor": 90}


@pytest.fixture(autouse=True)
def challenge_files_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "challenge-files"
    root.mkdir()
    monkeypatch.setenv(challenges_service.FILES_ROOT_ENV, str(root))
    return root


async def make_user(username: str) -> tuple[AsyncClient, dict[str, str], str]:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    client = AsyncClient(transport=transport, base_url="http://test", timeout=60)
    res = await client.post("/api/auth/register", json={"username": username, "password": PASSWORD})
    assert res.status_code == 201, res.text
    headers = {"x-csrf-token": res.json()["csrf_token"]}
    client.headers.update(headers)
    return client, headers, res.json()["id"]


async def grant_role(db_engine: AsyncEngine, username: str, role_name: str) -> None:
    from openrange.api.db import session_factory
    from openrange.api.users.models import Role, User, UserRole

    assert session_factory is not None
    async with session_factory() as db:
        role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one()
        user = (await db.execute(select(User).where(User.username == username))).scalar_one()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()


@pytest.fixture
async def admin_client(db_engine: AsyncEngine) -> AsyncClient:
    client, headers, _user_id = await make_user("chal-admin")
    await grant_role(db_engine, "chal-admin", "admin")
    client.headers.update(headers)
    return client


@pytest.fixture
async def player_client() -> AsyncClient:
    client, headers, _user_id = await make_user("chal-player")
    client.headers.update(headers)
    return client


async def make_challenge(
    client: AsyncClient,
    slug: str,
    *,
    flag: str = "flag{test-marker}",
    case_sensitive: bool = False,
    scoring: str = "static",
    decay: dict[str, int] | None = None,
    points_base: int = 100,
    state: str = "visible",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "slug": slug,
        "name": f"Challenge {slug}",
        "category": "web",
        "description": "# hello\nfind the flag",
        "difficulty": 4,
        "points_base": points_base,
        "scoring": scoring,
        "flag": flag,
        "flag_case_sensitive": case_sensitive,
        "state": state,
    }
    if decay is not None:
        payload["dynamic_decay"] = decay
    res = await client.post("/api/challenges", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


# --- Pure scoring math ---------------------------------------------------------


def test_dynamic_decay_table_hand_computed() -> None:
    # step = (1000 - 100) / 90 = 10 exactly.
    expected = {0: 1000, 1: 990, 5: 950, 45: 550, 89: 110, 90: 100, 91: 100, 10_000: 100}
    for count_before, want in expected.items():
        got = challenges_service.compute_points(
            scoring="dynamic",
            points_base=123,
            dynamic_decay=DECAY,
            solve_count_before=count_before,
        )
        assert got == want, f"count_before={count_before}: got {got}, want {want}"


def test_static_scoring_ignores_decay_and_count() -> None:
    assert (
        challenges_service.compute_points(
            scoring="static",
            points_base=250,
            dynamic_decay=DECAY,
            solve_count_before=42,
        )
        == 250
    )


def test_first_blood_bonus_applies_once_flat() -> None:
    assert challenges_service.apply_first_blood(1000, is_first_blood=True) == 1100
    assert challenges_service.apply_first_blood(100, is_first_blood=True) == 110
    assert challenges_service.apply_first_blood(950, is_first_blood=False) == 950


def test_flag_normalization_rules() -> None:
    assert challenges_service.normalize_flag("  Flag{ABC}  ", case_sensitive=False) == "flag{abc}"
    assert challenges_service.normalize_flag("  Flag{ABC}  ", case_sensitive=True) == "Flag{ABC}"


def test_safe_resolve_rejects_escapes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(challenges_service.FILES_ROOT_ENV, str(tmp_path / "root"))
    inside = challenges_service.safe_resolve("abc/file-1")
    assert inside.is_relative_to((tmp_path / "root").resolve())
    for bad in [
        "../outside.txt",
        "a/../../outside",
        "/etc/passwd",
        r"C:\windows\temp",
        "a\\b.txt",
        "\x00bad",
    ]:
        with pytest.raises(challenges_service.AuthError):
            challenges_service.safe_resolve(bad)


# --- API flows -------------------------------------------------------------------


async def test_submit_flow_wrong_then_case_insensitive_correct(
    admin_client: AsyncClient, player_client: AsyncClient
) -> None:
    await make_challenge(admin_client, "web-warmup", flag="flag{Case_Marker}")

    wrong = await player_client.post("/api/challenges/web-warmup/submit", json={"flag": "nope"})
    assert wrong.status_code == 200
    assert wrong.json() == {
        "correct": False,
        "already_solved": False,
        "points": None,
        "first_blood": False,
    }

    ok = await player_client.post(
        "/api/challenges/web-warmup/submit", json={"flag": "  FLAG{case_marker} "}
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["correct"] is True
    assert body["already_solved"] is False
    assert body["points"] == 110  # static 100 + first blood 10%
    assert body["first_blood"] is True

    repeat = await player_client.post(
        "/api/challenges/web-warmup/submit", json={"flag": "anything"}
    )
    assert repeat.json()["already_solved"] is True
    assert repeat.json()["points"] is None


async def test_case_sensitive_challenge_rejects_case_mismatch(
    admin_client: AsyncClient, player_client: AsyncClient
) -> None:
    await make_challenge(admin_client, "rev-strict", flag="Flag{Exact}", case_sensitive=True)
    bad = await player_client.post(
        "/api/challenges/rev-strict/submit", json={"flag": "flag{exact}"}
    )
    assert bad.json()["correct"] is False
    good = await player_client.post(
        "/api/challenges/rev-strict/submit", json={"flag": " Flag{Exact} "}
    )
    assert good.json()["correct"] is True


async def test_duplicate_solve_is_idempotent_single_row(
    admin_client: AsyncClient, player_client: AsyncClient, db_engine: AsyncEngine
) -> None:
    await make_challenge(admin_client, "crypto-dupe")
    first = await player_client.post(
        "/api/challenges/crypto-dupe/submit", json={"flag": "flag{test-marker}"}
    )
    second = await player_client.post(
        "/api/challenges/crypto-dupe/submit", json={"flag": "flag{test-marker}"}
    )
    assert first.json()["correct"] is True
    assert second.json()["already_solved"] is True
    async with db_engine.connect() as conn:
        rows = await conn.execute(text("SELECT count(*) FROM challenge_solves"))
        assert rows.scalar_one() == 1


async def test_dynamic_decay_and_first_blood_once_across_players(
    admin_client: AsyncClient,
) -> None:
    await make_challenge(admin_client, "dyn-decay", scoring="dynamic", decay=DECAY, points_base=999)

    first, _h1, _id1 = await make_user("dyn-solver-a")
    r1 = await first.post("/api/challenges/dyn-decay/submit", json={"flag": "flag{test-marker}"})
    assert r1.json() == {
        "correct": True,
        "already_solved": False,
        "points": 1100,  # 1000 base value + 10% first blood
        "first_blood": True,
    }

    second, _h2, _id2 = await make_user("dyn-solver-b")
    r2 = await second.post("/api/challenges/dyn-decay/submit", json={"flag": "flag{test-marker}"})
    assert r2.json() == {
        "correct": True,
        "already_solved": False,
        "points": 990,  # one solve before, no bonus
        "first_blood": False,
    }

    # Board shows the value the NEXT solver would earn.
    observer, _h3, _id3 = await make_user("dyn-observer")
    listing = await observer.get("/api/challenges")
    dyn = [c for c in listing.json() if c["slug"] == "dyn-decay"]
    assert dyn[0]["solve_count"] == 2
    assert dyn[0]["points"] == 980


async def test_hidden_challenge_invisible_and_submit_404(
    admin_client: AsyncClient, player_client: AsyncClient
) -> None:
    await make_challenge(admin_client, "secret-draft", state="hidden")

    listing = await player_client.get("/api/challenges")
    assert listing.json() == []

    detail = await player_client.get("/api/challenges/secret-draft")
    assert detail.status_code == 404

    sub = await player_client.post("/api/challenges/secret-draft/submit", json={"flag": "x"})
    assert sub.status_code == 404

    missing_file = await player_client.get(f"/api/challenges/secret-draft/files/{uuid.uuid4()}")
    assert missing_file.status_code == 404

    admin_listing = await admin_client.get("/api/challenges")
    entry = [c for c in admin_listing.json() if c["slug"] == "secret-draft"]
    assert entry and entry[0]["state"] == "hidden"


async def test_patch_flips_state_for_release_scheduling(
    admin_client: AsyncClient, player_client: AsyncClient
) -> None:
    await make_challenge(admin_client, "release-me", state="hidden")
    patched = await admin_client.patch("/api/challenges/release-me", json={"state": "visible"})
    assert patched.status_code == 200
    assert patched.json()["state"] == "visible"
    seen = await player_client.get("/api/challenges")
    assert [c["slug"] for c in seen.json()] == ["release-me"]

    rehide = await admin_client.patch("/api/challenges/release-me", json={"state": "hidden"})
    assert rehide.json()["state"] == "hidden"
    gone = await player_client.get("/api/challenges/release-me")
    assert gone.status_code == 404


async def test_rbac_negatives(player_client: AsyncClient) -> None:
    from openrange.api.main import create_app

    anon_transport = ASGITransport(app=create_app())  # type: ignore[arg-type]
    async with AsyncClient(transport=anon_transport, base_url="http://test") as anon:
        assert (await anon.get("/api/challenges")).status_code == 401
        assert (await anon.post("/api/challenges", json={})).status_code == 401

    create = await player_client.post(
        "/api/challenges",
        json={"slug": "nope", "name": "Nope", "category": "misc", "flag": "x"},
    )
    assert create.status_code == 403

    patch = await player_client.patch("/api/challenges/some-challenge", json={"state": "hidden"})
    assert patch.status_code == 403

    upload = await player_client.post(
        "/api/challenges/some-challenge/files",
        files={"file": ("x.txt", b"data")},
    )
    assert upload.status_code == 403


async def test_file_upload_download_caps_and_traversal_guard(
    admin_client: AsyncClient,
    player_client: AsyncClient,
    challenge_files_dir: Path,
    db_engine: AsyncEngine,
) -> None:
    await make_challenge(admin_client, "forensics-pack")

    up = await admin_client.post(
        "/api/challenges/forensics-pack/files",
        files={"file": ("pcap.pcap", b"\xd4\xc3\xb2\xa1-fake")},
    )
    assert up.status_code == 201, up.text
    meta = up.json()
    assert meta["filename"] == "pcap.pcap"

    detail = await player_client.get("/api/challenges/forensics-pack")
    files = detail.json()["files"]
    assert len(files) == 1 and files[0]["sha256"] == meta["sha256"]

    down = await player_client.get(f"/api/challenges/forensics-pack/files/{meta['id']}")
    assert down.status_code == 200
    assert down.content == b"\xd4\xc3\xb2\xa1-fake"
    assert "pcap.pcap" in down.headers["content-disposition"]

    too_big = await admin_client.post(
        "/api/challenges/forensics-pack/files",
        files={"file": ("big.bin", b"\0" * (challenges_service.MAX_FILE_BYTES + 1))},
    )
    assert too_big.status_code == 413

    for i in range(challenges_service.MAX_FILES_PER_CHALLENGE - 1):
        more = await admin_client.post(
            "/api/challenges/forensics-pack/files",
            files={"file": (f"f{i}.txt", b"x")},
        )
        assert more.status_code == 201, more.text
    overflow = await admin_client.post(
        "/api/challenges/forensics-pack/files",
        files={"file": ("one-too-many.txt", b"x")},
    )
    assert overflow.status_code == 413

    # Traversal guard: a tampered storage_path must not escape the root.
    outside = challenge_files_dir.parent / "escaped.txt"
    outside.write_text("SECRET-OUTSIDE")
    async with db_engine.begin() as conn:
        await conn.execute(
            text("UPDATE challenge_files SET storage_path = '../escaped.txt' WHERE id = :fid"),
            {"fid": meta["id"]},
        )
    smuggled = await player_client.get(f"/api/challenges/forensics-pack/files/{meta['id']}")
    assert smuggled.status_code in (404, 422)
    assert b"SECRET-OUTSIDE" not in smuggled.content


async def test_anti_spray_records_signal_after_threshold(
    admin_client: AsyncClient, player_client: AsyncClient, db_engine: AsyncEngine
) -> None:
    await make_challenge(admin_client, "spray-target")
    for i in range(challenges_service.SPRAY_THRESHOLD + 1):
        res = await player_client.post(
            "/api/challenges/spray-target/submit", json={"flag": f"guess-{i}"}
        )
        assert res.status_code == 200

    async with db_engine.begin() as conn:
        rows = (
            await conn.execute(text("SELECT kind FROM anti_cheat_signals WHERE status = 'open'"))
        ).all()
    kinds = {row[0] for row in rows}
    assert "answer_spray" in kinds


async def test_flag_hash_never_leaks(admin_client: AsyncClient) -> None:
    await make_challenge(admin_client, "no-leak", flag="flag{s3cr3t}")
    listing = await admin_client.get("/api/challenges")
    assert "flag_hash" not in str(listing.json())
    detail = await admin_client.get("/api/challenges/no-leak")
    assert "flag_hash" not in str(detail.json())
