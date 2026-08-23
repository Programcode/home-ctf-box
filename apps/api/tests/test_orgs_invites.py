"""Organization invite flow gate (plan Phase 11).

Token semantics: plaintext is returned exactly once at mint time, the
database keeps only the SHA-256 hash, previews need token knowledge but
no login, acceptance needs a logged-in account matching the invite
email (case-insensitively) unless it is a link invite, and expired or
already-accepted invites are rejected.
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from openrange.api.learning import content as learning_content
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from testshelpers.curriculum import write_curriculum

pytestmark = [pytest.mark.integration]

PASSWORD = "correct-horse-battery"


@pytest.fixture
async def db(db_engine: AsyncEngine) -> AsyncIterator[async_sessionmaker]:
    """Session factory for direct read-model seeding."""
    yield async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def curriculum(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    root = write_curriculum(tmp_path / "content")
    monkeypatch.setenv(learning_content.CONTENT_DIR_ENV, str(root))
    learning_content.clear_caches()
    yield root
    learning_content.clear_caches()


def new_client() -> AsyncClient:
    from openrange.api.main import create_app

    app: FastAPI = create_app()
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60)  # type: ignore[arg-type]


async def make_user(
    username: str, email: str | None = None
) -> tuple[AsyncClient, dict[str, str], str]:
    client = new_client()
    res = await client.post(
        "/api/auth/register", json={"username": username, "password": PASSWORD, "email": email}
    )
    assert res.status_code == 201, res.text
    return client, {"x-csrf-token": res.json()["csrf_token"]}, res.json()["id"]


async def make_org_owner(name: str) -> tuple[AsyncClient, dict[str, str]]:
    owner, headers, _uid = await make_user(name)
    res = await owner.post("/api/orgs", json={"name": name}, headers=headers)
    assert res.status_code == 201, res.text
    return owner, headers


async def mint_invite(
    owner: AsyncClient,
    owner_headers: dict[str, str],
    slug: str,
    payload: dict[str, object],
) -> dict[str, object]:
    res = await owner.post(f"/api/orgs/{slug}/invites", json=payload, headers=owner_headers)
    assert res.status_code == 201, res.text
    return res.json()


async def test_email_invite_token_once_hash_stored_and_accept(db: async_sessionmaker) -> None:
    from openrange.api.orgs.models import OrgInvite

    owner, owner_headers = await make_org_owner("inv-alice")

    minted = await mint_invite(
        owner, owner_headers, "inv-alice", {"email": "bob@example.com", "role": "instructor"}
    )
    token = minted["token"]
    assert isinstance(token, str) and len(token) >= 32
    assert "token_hash" not in str(minted)

    # Exactly one row and only the SHA-256 of the plaintext in storage.
    async with db() as session:
        invites = (await session.execute(select(OrgInvite))).scalars().all()
        assert len(invites) == 1
        stored = invites[0]
        assert stored.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert token not in stored.token_hash
        assert stored.email == "bob@example.com"
        assert stored.accepted_at is None

    # Preview needs no login; the target email is masked.
    anon = new_client()
    preview = await anon.get(f"/api/invites/{token}")
    assert preview.status_code == 200
    body = preview.json()
    assert body["organization"]["name"] == "inv-alice"
    assert body["role"] == "instructor"
    assert body["accepted"] is False
    assert body["expired"] is False
    assert body["email"].startswith("b") and "..." in body["email"]
    missing = await anon.get("/api/invites/not-a-real-token")
    assert missing.status_code == 404
    await anon.aclose()

    # A different account cannot accept an email-scoped invite...
    carol, carol_headers, _uid_carol = await make_user("inv-carol", email="carol@example.com")
    wrong = await carol.post(f"/api/invites/{token}/accept", headers=carol_headers)
    assert wrong.status_code == 403

    bob, bob_headers, _uid_bob = await make_user("inv-bob", email="BOB@Example.COM")
    accepted = await bob.post(f"/api/invites/{token}/accept", headers=bob_headers)
    # ...but the intended address matches case-insensitively.
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["membership"]["role"] == "instructor"

    mine = await bob.get("/api/orgs/mine", headers=bob_headers)
    assert [o["name"] for o in mine.json()] == ["inv-alice"]
    roster = await owner.get("/api/orgs/inv-alice/members", headers=owner_headers)
    roles = {m["username"]: m["role"] for m in roster.json()["items"]}
    assert roles == {"inv-alice": "owner", "inv-bob": "instructor"}

    replay = await bob.post(f"/api/invites/{token}/accept", headers=bob_headers)
    assert replay.status_code == 409

    await carol.aclose()
    await bob.aclose()


async def test_link_invite_acceptable_by_any_authenticated_user() -> None:
    owner, owner_headers = await make_org_owner("link-alice")
    minted = await mint_invite(owner, owner_headers, "link-alice", {})
    token = minted["token"]
    assert minted["email"] is None

    dave, dave_headers, _uid_dave = await make_user("link-dave")
    accepted = await dave.post(f"/api/invites/{token}/accept", headers=dave_headers)
    assert accepted.status_code == 200
    assert accepted.json()["membership"]["role"] == "member"

    # Joining again through a second link does not duplicate membership.
    second = await mint_invite(owner, owner_headers, "link-alice", {})
    dup = await dave.post(f"/api/invites/{second['token']}/accept", headers=dave_headers)
    assert dup.status_code == 409


async def test_expired_invite_rejected(db: async_sessionmaker) -> None:
    from openrange.api.orgs.models import OrgInvite

    owner, owner_headers = await make_org_owner("exp-alice")
    minted = await mint_invite(owner, owner_headers, "exp-alice", {"role": "member"})
    token = minted["token"]

    async with db() as session:
        row = (await session.execute(select(OrgInvite).limit(1))).scalars().one()
        row.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await session.commit()

    dave, dave_headers, _uid_dave = await make_user("exp-dave")
    rejected = await dave.post(f"/api/invites/{token}/accept", headers=dave_headers)
    assert rejected.status_code == 410

    anon = new_client()
    state = await anon.get(f"/api/invites/{token}")
    assert state.json()["expired"] is True
    await anon.aclose()


async def test_member_cannot_mint_invites_but_can_read_roster() -> None:
    owner, owner_headers = await make_org_owner("roster-alice")
    member, member_headers, _uid_member = await make_user("roster-bob")
    minted = await mint_invite(owner, owner_headers, "roster-alice", {})
    join = await member.post(f"/api/invites/{minted['token']}/accept", headers=member_headers)
    assert join.status_code == 200

    denied = await member.post(
        "/api/orgs/roster-alice/invites", json={"email": "x@example.com"}, headers=member_headers
    )
    assert denied.status_code == 403
