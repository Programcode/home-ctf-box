"""Team domain logic.

Roles: captain > member, carried by ``team_members.capability``. A team
may have several captains; the last remaining captain cannot leave or be
demoted without promoting someone else first. Invite codes are hashed
like org invites (SHA-256), returned once, and consumed on use; minting
a new code replaces any previous open one.
"""

from __future__ import annotations

import uuid

from openrange.api.auth.service import AuthError
from openrange.api.auth.tokens import generate_token, hash_token
from openrange.api.config import get_settings
from openrange.api.teams.models import Team, TeamMember
from openrange.api.users.models import User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

MEMBER = "member"
CAPTAIN = "captain"

CAPABILITY_RANK: dict[str, int] = {MEMBER: 1, CAPTAIN: 2}

# Names that would collide with collection-level route segments.
RESERVED_NAMES = {"mine", "join"}

NAME_PATTERN = r"^[a-z0-9-]{3,30}$"


def max_team_size() -> int:
    return get_settings().team_max_size


async def get_team_by_name(db: AsyncSession, name: str) -> Team | None:
    return (await db.execute(select(Team).where(Team.name == name))).scalar_one_or_none()


async def member_count(db: AsyncSession, team_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team_id)
            )
        ).scalar_one()
    )


async def get_membership(
    db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
) -> TeamMember | None:
    return (
        await db.execute(
            select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        )
    ).scalar_one_or_none()


async def create_team(
    db: AsyncSession, *, owner: User, name: str, display_name: str | None
) -> Team:
    if name in RESERVED_NAMES:
        raise AuthError("team name is reserved", 422)
    if await get_team_by_name(db, name) is not None:
        raise AuthError("team name already taken", 409)
    team = Team(name=name, display_name=display_name or name, captain_id=owner.id)
    db.add(team)
    await db.flush()
    db.add(TeamMember(team_id=team.id, user_id=owner.id, capability=CAPTAIN))
    await db.flush()
    return team


async def require_captain(db: AsyncSession, team: Team, user_id: uuid.UUID) -> TeamMember:
    membership = await get_membership(db, team.id, user_id)
    if membership is None:
        raise AuthError("unknown team", 404)
    if membership.capability != CAPTAIN:
        raise AuthError("requires the team captain capability", 403)
    return membership


async def mint_invite(db: AsyncSession, team: Team) -> str:
    """Return the plaintext code exactly once; only its hash is stored."""
    raw_code = generate_token(16)
    team.invite_code_hash = hash_token(raw_code)
    await db.flush()
    return raw_code


async def join_team(db: AsyncSession, user: User, raw_code: str) -> tuple[Team, TeamMember]:
    team = (
        await db.execute(select(Team).where(Team.invite_code_hash == hash_token(raw_code)))
    ).scalar_one_or_none()
    if team is None:
        raise AuthError("unknown invite code", 404)
    if await get_membership(db, team.id, user.id) is not None:
        raise AuthError("already a member of this team", 409)
    if await member_count(db, team.id) >= max_team_size():
        raise AuthError("team is full", 409)
    membership = TeamMember(team_id=team.id, user_id=user.id, capability=MEMBER)
    db.add(membership)
    # Single use: the code dies with this membership.
    team.invite_code_hash = None
    await db.flush()
    return team, membership


async def _captain_count(
    db: AsyncSession, team_id: uuid.UUID, exclude_user: uuid.UUID | None = None
) -> int:
    stmt = (
        select(func.count())
        .select_from(TeamMember)
        .where(TeamMember.team_id == team_id, TeamMember.capability == CAPTAIN)
    )
    if exclude_user is not None:
        stmt = stmt.where(TeamMember.user_id != exclude_user)
    return int((await db.execute(stmt)).scalar_one())


async def leave_team(db: AsyncSession, team: Team, user_id: uuid.UUID) -> None:
    membership = await get_membership(db, team.id, user_id)
    if membership is None:
        raise AuthError("not a member of this team", 404)
    if membership.capability == CAPTAIN and await _captain_count(db, team.id) <= 1:
        raise AuthError("promote another captain before leaving", 409)
    await db.delete(membership)
    await db.flush()


async def kick_member(
    db: AsyncSession, team: Team, actor_id: uuid.UUID, target_user_id: uuid.UUID
) -> None:
    await require_captain(db, team, actor_id)
    target = await get_membership(db, team.id, target_user_id)
    if target is None:
        raise AuthError("unknown member", 404)
    if target.capability == CAPTAIN:
        raise AuthError("demote the captain before kicking", 409)
    await db.delete(target)
    await db.flush()


async def set_capability(
    db: AsyncSession,
    team: Team,
    actor_id: uuid.UUID,
    target_user_id: uuid.UUID,
    capability: str,
) -> TeamMember:
    await require_captain(db, team, actor_id)
    membership = await get_membership(db, team.id, target_user_id)
    if membership is None:
        raise AuthError("unknown member", 404)
    if (
        capability != CAPTAIN
        and membership.capability == CAPTAIN
        and await _captain_count(db, team.id) <= 1
    ):
        raise AuthError("cannot demote the last captain", 409)
    membership.capability = capability
    await db.flush()
    return membership
