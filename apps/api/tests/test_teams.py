"""Teams integration gate (plan Phase 9 item 7).

Real Postgres: creation with founding captain, hashed single-use invite
codes, size caps, capability management, captain-leave guard, kick
rules, public profiles without roster leakage, and RBAC negatives.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.integration

STRONG = "correct-horse-battery"

_clients: list[AsyncClient] = []


@pytest.fixture(autouse=True)
async def _close_clients() -> AsyncIterator[None]:
    yield
    while _clients:
        await _clients.pop().aclose()


async def _make_user(username: str) -> tuple[AsyncClient, dict[str, str], uuid.UUID]:
    """Isolated client per user so cookie jars never collide."""
    from httpx import ASGITransport
    from openrange.api.main import create_app

    app = create_app()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=120)
    _clients.append(client)
    res = await client.post("/api/auth/register", json={"username": username, "password": STRONG})
    assert res.status_code == 201, res.text
    me = await client.get("/api/users/me")
    return client, {"x-csrf-token": res.json()["csrf_token"]}, uuid.UUID(me.json()["id"])


@asynccontextmanager
async def _db() -> AsyncIterator[Any]:
    from openrange.api.db import session_factory as sf

    assert sf is not None
    async with sf() as session:
        yield session


async def _new_team(
    name: str, owner_username: str
) -> tuple[AsyncClient, dict[str, str], uuid.UUID]:
    client, headers, uid = await _make_user(owner_username)
    res = await client.post(
        "/api/teams", json={"name": name, "display_name": f"Team {name}"}, headers=headers
    )
    assert res.status_code == 201, res.text
    return client, headers, uid


async def _join(captain: AsyncClient, cap_headers: dict[str, str], name: str) -> None:
    """Captain mints one code and it is consumed immediately."""
    minted = await captain.post(f"/api/teams/{name}/invites", headers=cap_headers)
    assert minted.status_code == 201, minted.text
    joiner, joiner_headers, _jid = await _make_user(f"m-{uuid.uuid4().hex[:8]}")
    joined = await joiner.post(
        "/api/teams/join", json={"code": minted.json()["code"]}, headers=joiner_headers
    )
    assert joined.status_code == 200, joined.text


async def test_create_team_founder_is_captain(db_engine: Any) -> None:
    client, _headers, uid = await _new_team("alpha-squad", "cap-alpha")
    mine = (await client.get("/api/teams/mine")).json()
    assert len(mine) == 1
    assert mine[0]["name"] == "alpha-squad"
    assert mine[0]["display_name"] == "Team alpha-squad"
    assert mine[0]["capability"] == "captain"

    async with _db() as db:
        from openrange.api.teams.models import Team, TeamMember

        team = (await db.execute(select(Team).where(Team.name == "alpha-squad"))).scalar_one()
        assert str(team.captain_id) == str(uid)
        member = (
            await db.execute(select(TeamMember).where(TeamMember.team_id == team.id))
        ).scalar_one()
        assert member.user_id == uid
        assert member.capability == "captain"


async def test_duplicate_invalid_and_reserved_names(db_engine: Any) -> None:
    client, headers, _uid = await _new_team("bravo-team", "cap-bravo")

    dup = await client.post("/api/teams", json={"name": "bravo-team"}, headers=headers)
    assert dup.status_code == 409

    upper = await client.post("/api/teams", json={"name": "Gamma"}, headers=headers)
    assert upper.status_code == 422

    short = await client.post("/api/teams", json={"name": "ab"}, headers=headers)
    assert short.status_code == 422

    too_long = await client.post("/api/teams", json={"name": "a" * 31}, headers=headers)
    assert too_long.status_code == 422

    reserved = await client.post("/api/teams", json={"name": "mine"}, headers=headers)
    # "mine" matches the slug pattern, so the service-level guard fires.
    assert reserved.status_code == 422


async def test_invite_single_use_and_permission(db_engine: Any) -> None:
    captain, cap_headers, _cid = await _new_team("delta-team", "cap-delta")
    member, member_headers, _mid = await _make_user("member-delta")
    stranger, stranger_headers, _sid = await _make_user("stranger-delta")

    # Members cannot mint invites; strangers learn nothing about teams.
    forbidden = await member.post("/api/teams/delta-team/invites", headers=member_headers)
    assert forbidden.status_code == 404  # not a member at all

    profile = await member.get("/api/teams/delta-team")
    assert profile.json()["member_count"] == 1
    assert "members" not in profile.json()  # no roster leak on the public view

    minted = await captain.post("/api/teams/delta-team/invites", headers=cap_headers)
    assert minted.status_code == 201, minted.text
    code = minted.json()["code"]

    joined = await member.post("/api/teams/join", json={"code": code}, headers=member_headers)
    assert joined.status_code == 200, joined.text
    assert joined.json()["capability"] == "member"

    # Same code cannot be replayed.
    replay = await stranger.post("/api/teams/join", json={"code": code}, headers=stranger_headers)
    assert replay.status_code == 404

    # Joining twice is blocked even with a fresh code.
    minted2 = await captain.post("/api/teams/delta-team/invites", headers=cap_headers)
    again = await member.post(
        "/api/teams/join", json={"code": minted2.json()["code"]}, headers=member_headers
    )
    assert again.status_code == 409

    # Now that they are a member, minting is a capability error (403).
    mint_forbidden = await member.post("/api/teams/delta-team/invites", headers=member_headers)
    assert mint_forbidden.status_code == 403

    bogus = await stranger.post(
        "/api/teams/join", json={"code": "nonsense"}, headers=stranger_headers
    )
    assert bogus.status_code == 404


async def test_team_size_cap_settings_default(db_engine: Any) -> None:
    from openrange.api.teams.service import max_team_size

    captain, cap_headers, _cid = await _new_team("echo-team", "cap-echo")
    limit = max_team_size()
    assert limit == 8  # settings-driven default

    for _i in range(limit - 1):
        await _join(captain, cap_headers, "echo-team")

    profile = await captain.get("/api/teams/echo-team")
    assert profile.json()["member_count"] == limit

    minted = await captain.post("/api/teams/echo-team/invites", headers=cap_headers)
    overflow, overflow_headers, _oid = await _make_user("overflow-echo")
    full = await overflow.post(
        "/api/teams/join", json={"code": minted.json()["code"]}, headers=overflow_headers
    )
    assert full.status_code == 409
    assert "full" in str(full.json()["detail"])


async def test_capability_patch_and_last_captain_guard(db_engine: Any) -> None:
    captain, cap_headers, cid = await _new_team("foxtrot", "cap-foxtrot")
    member, member_headers, mid = await _make_user("member-foxtrot")

    minted = await captain.post("/api/teams/foxtrot/invites", headers=cap_headers)
    joined = await member.post(
        "/api/teams/join", json={"code": minted.json()["code"]}, headers=member_headers
    )
    assert joined.status_code == 200

    # Non-captains cannot change capabilities.
    denied = await member.patch(
        f"/api/teams/foxtrot/members/{cid}",
        json={"capability": "member"},
        headers=member_headers,
    )
    assert denied.status_code == 403

    promoted = await captain.patch(
        f"/api/teams/foxtrot/members/{mid}",
        json={"capability": "captain"},
        headers=cap_headers,
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["capability"] == "captain"

    # Two captains exist now, so demoting one is allowed.
    demoted = await member.patch(
        f"/api/teams/foxtrot/members/{cid}",
        json={"capability": "member"},
        headers=member_headers,
    )
    assert demoted.status_code == 200

    # But the remaining sole captain cannot be demoted.
    blocked = await member.patch(
        f"/api/teams/foxtrot/members/{mid}",
        json={"capability": "member"},
        headers=member_headers,
    )
    assert blocked.status_code == 409

    # Unknown members are a 404 when queried by the remaining captain.
    unknown = await member.patch(
        f"/api/teams/foxtrot/members/{uuid.uuid4()}",
        json={"capability": "captain"},
        headers=member_headers,
    )
    assert unknown.status_code == 404


async def test_leave_and_kick_rules(db_engine: Any) -> None:
    captain, cap_headers, cid = await _new_team("golf-team", "cap-golf")
    member, member_headers, mid = await _make_user("member-golf")

    minted = await captain.post("/api/teams/golf-team/invites", headers=cap_headers)
    joined = await member.post(
        "/api/teams/join", json={"code": minted.json()["code"]}, headers=member_headers
    )
    assert joined.status_code == 200

    # Sole captain cannot leave.
    blocked = await captain.delete(f"/api/teams/golf-team/members/{cid}", headers=cap_headers)
    assert blocked.status_code == 409
    assert "promote" in str(blocked.json()["detail"])

    # Promote member, then the founder can leave.
    promote = await captain.patch(
        f"/api/teams/golf-team/members/{mid}",
        json={"capability": "captain"},
        headers=cap_headers,
    )
    assert promote.status_code == 200
    left = await captain.delete(f"/api/teams/golf-team/members/{cid}", headers=cap_headers)
    assert left.status_code == 200
    mine = (await captain.get("/api/teams/mine")).json()
    assert mine == []

    # Kicking requires the captain capability.
    stranger, stranger_headers, _sid = await _make_user("stranger-golf")
    kick_denied = await stranger.delete(
        f"/api/teams/golf-team/members/{mid}", headers=stranger_headers
    )
    assert kick_denied.status_code == 404  # stranger is not in the team at all

    # Captains cannot be kicked directly; demote first.
    new_cap, new_cap_headers, _ncid = await _make_user("cap2-golf")
    mint2 = await member.post("/api/teams/golf-team/invites", headers=member_headers)
    # member is now captain (promoted above), so minting works.
    assert mint2.status_code == 201
    joined2 = await new_cap.post(
        "/api/teams/join", json={"code": mint2.json()["code"]}, headers=new_cap_headers
    )
    assert joined2.status_code == 200
    promote2 = await member.patch(
        f"/api/teams/golf-team/members/{_ncid}",
        json={"capability": "captain"},
        headers=member_headers,
    )
    assert promote2.status_code == 200
    kick_captain = await member.delete(
        f"/api/teams/golf-team/members/{_ncid}", headers=member_headers
    )
    assert kick_captain.status_code == 409

    # Kicking a plain member works; kicking self is leaving.
    plain, plain_headers, pid = await _make_user("plain-golf")
    mint3 = await member.post("/api/teams/golf-team/invites", headers=member_headers)
    joined3 = await plain.post(
        "/api/teams/join", json={"code": mint3.json()["code"]}, headers=plain_headers
    )
    assert joined3.status_code == 200
    kicked = await member.delete(f"/api/teams/golf-team/members/{pid}", headers=member_headers)
    assert kicked.status_code == 200
    gone = (await plain.get("/api/teams/mine")).json()
    assert gone == []


async def test_unknown_team_and_anonymous_requests(db_engine: Any, client: AsyncClient) -> None:
    user, user_headers, _uid = await _make_user("solo-hotel")
    missing = await user.get("/api/teams/does-not-exist")
    assert missing.status_code == 404

    assert (await client.get("/api/teams/mine")).status_code == 401
    assert (await client.get("/api/teams/nope-india")).status_code == 401
    anon_join = await client.post("/api/teams/join", json={"code": "x"})
    assert anon_join.status_code == 401
    assert user_headers["x-csrf-token"]
