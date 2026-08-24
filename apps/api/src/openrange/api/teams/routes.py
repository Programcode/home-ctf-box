"""Team HTTP routes: /api/teams."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter
from openrange.api.auth.dependencies import CurrentUser, DbSession
from openrange.api.auth.service import AuthError
from openrange.api.teams import service as teamsvc
from openrange.api.teams.models import Team, TeamMember
from openrange.api.users.models import User
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(prefix="/api/teams", tags=["teams"])

Capability = Literal["member", "captain"]


class TeamCreateIn(BaseModel):
    name: str = Field(pattern=teamsvc.NAME_PATTERN)
    display_name: str = Field(default="", max_length=64)


class JoinIn(BaseModel):
    code: str = Field(min_length=1, max_length=128)


class MemberCapabilityIn(BaseModel):
    capability: Capability


def public_team(team: Team) -> dict[str, object]:
    """Public profile shape: identity only, roster never included."""
    return {
        "name": team.name,
        "display_name": team.display_name,
        "created_at": team.created_at.isoformat(),
    }


def member_view(member: TeamMember, user: User) -> dict[str, object]:
    return {
        "user_id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "capability": member.capability,
        "joined_at": member.joined_at.isoformat(),
    }


async def _team_or_404(db: DbSession, name: str) -> Team:
    team = await teamsvc.get_team_by_name(db, name)
    if team is None:
        raise AuthError("unknown team", 404)
    return team


# Literal segments (/mine, /join) are declared before /{name} on purpose:
# FastAPI matches in declaration order.
@router.post("", status_code=201)
async def create_team(payload: TeamCreateIn, user: CurrentUser, db: DbSession) -> dict[str, object]:
    team = await teamsvc.create_team(
        db, owner=user, name=payload.name, display_name=payload.display_name
    )
    view = public_team(team)
    view["your_capability"] = "captain"
    return view


@router.get("/mine")
async def my_teams(user: CurrentUser, db: DbSession) -> list[dict[str, object]]:
    rows = await db.execute(
        select(TeamMember, Team)
        .join(Team, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == user.id)
        .order_by(TeamMember.joined_at.asc())
    )
    views: list[dict[str, object]] = []
    for member, team in rows.all():
        view = public_team(team)
        view["capability"] = member.capability
        view["joined_at"] = member.joined_at.isoformat()
        views.append(view)
    return views


@router.post("/join")
async def join(payload: JoinIn, user: CurrentUser, db: DbSession) -> dict[str, object]:
    team, membership = await teamsvc.join_team(db, user, payload.code)
    view = public_team(team)
    view["capability"] = membership.capability
    return view


@router.get("/{name}")
async def get_team(name: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    team = await _team_or_404(db, name)
    view = public_team(team)
    # Public profile exposes the headcount only, never the roster.
    view["member_count"] = await teamsvc.member_count(db, team.id)
    return view


@router.post("/{name}/invites", status_code=201)
async def create_invite(name: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    team = await _team_or_404(db, name)
    await teamsvc.require_captain(db, team, user.id)
    raw_code = await teamsvc.mint_invite(db, team)
    # The plaintext code is returned exactly once and never stored.
    return {"code": raw_code}


@router.patch("/{name}/members/{user_id}")
async def patch_member(
    name: str,
    user_id: uuid.UUID,
    payload: MemberCapabilityIn,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    team = await _team_or_404(db, name)
    membership = await teamsvc.set_capability(
        db, team, actor_id=user.id, target_user_id=user_id, capability=payload.capability
    )
    target = await db.get(User, user_id)
    assert target is not None
    return member_view(membership, target)


@router.delete("/{name}/members/{user_id}")
async def delete_member(
    name: str, user_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    team = await _team_or_404(db, name)
    if user_id == user.id:
        await teamsvc.leave_team(db, team, user.id)
    else:
        await teamsvc.kick_member(db, team, actor_id=user.id, target_user_id=user_id)
    return {"removed": True}


__all__ = ["router"]
