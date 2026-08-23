"""Organization HTTP routes: /api/orgs and /api/invites."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from openrange.api.auth.dependencies import CurrentUser, DbSession
from openrange.api.orgs import service as orgsvc
from openrange.api.orgs.models import Assignment, Cohort, Organization, OrgMember
from openrange.api.users.models import User
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/orgs", tags=["orgs"])
invite_router = APIRouter(prefix="/api/invites", tags=["orgs"])

api_router = APIRouter()
api_router.include_router(router)
api_router.include_router(invite_router)

OrgRole = Literal["owner", "instructor", "member"]


class OrgCreateIn(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9-]{3,40}$")
    display_name: str = Field(default="", max_length=64)


class OrgUpdateIn(BaseModel):
    display_name: str = Field(max_length=64)


class MemberRoleIn(BaseModel):
    role: OrgRole


class CohortCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CohortUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class CohortMemberIn(BaseModel):
    user_id: uuid.UUID


class AssignmentCreateIn(BaseModel):
    content_kind: Literal["room", "path"]
    content_slug: str = Field(min_length=1, max_length=128)
    cohort_id: uuid.UUID | None = None
    due_at: datetime | None = None


class InviteCreateIn(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    role: OrgRole = "member"
    expires_in_hours: int = Field(
        default=orgsvc.DEFAULT_INVITE_HOURS, ge=1, le=orgsvc.MAX_INVITE_HOURS
    )


def public_org(org: Organization, role: str | None = None) -> dict[str, object]:
    view: dict[str, object] = {
        "id": str(org.id),
        "name": org.name,
        "display_name": org.display_name,
        "created_at": org.created_at.isoformat(),
    }
    if role is not None:
        view["role"] = role
    return view


def public_member(member: OrgMember, user: User) -> dict[str, object]:
    return {
        "user_id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "role": member.role,
        "joined_at": member.joined_at.isoformat(),
    }


def public_cohort(cohort: Cohort, member_count: int | None = None) -> dict[str, object]:
    view: dict[str, object] = {
        "id": str(cohort.id),
        "org_id": str(cohort.org_id),
        "name": cohort.name,
        "starts_at": cohort.starts_at.isoformat() if cohort.starts_at else None,
        "ends_at": cohort.ends_at.isoformat() if cohort.ends_at else None,
        "metadata": dict(cohort.metadata_json),
        "created_at": cohort.created_at.isoformat(),
    }
    if member_count is not None:
        view["member_count"] = member_count
    return view


def public_assignment(assignment: Assignment) -> dict[str, object]:
    return {
        "id": str(assignment.id),
        "org_id": str(assignment.org_id),
        "cohort_id": str(assignment.cohort_id) if assignment.cohort_id else None,
        "content_kind": assignment.content_kind,
        "content_slug": assignment.content_slug,
        "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
        "created_by": str(assignment.created_by) if assignment.created_by else None,
        "created_at": assignment.created_at.isoformat(),
    }


# --- Organizations ----------------------------------------------------------


@router.post("", status_code=201)
async def create_org(payload: OrgCreateIn, user: CurrentUser, db: DbSession) -> dict[str, object]:
    org = await orgsvc.create_org(
        db, owner=user, name=payload.name, display_name=payload.display_name
    )
    return public_org(org, role="owner")


@router.get("/mine")
async def my_orgs(user: CurrentUser, db: DbSession) -> list[dict[str, object]]:
    return [
        public_org(org, role=member.role)
        for org, member in await orgsvc.list_orgs_for_user(db, user.id)
    ]


@router.get("/{slug}")
async def get_org(slug: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    org, member = await orgsvc.require_membership(db, user.id, slug)
    return public_org(org, role=member.role)


@router.put("/{slug}")
async def update_org(
    slug: str, payload: OrgUpdateIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    org, _member = await orgsvc.require_role(db, user.id, slug, orgsvc.OWNER)
    org.display_name = payload.display_name
    await db.flush()
    return public_org(org)


# --- Members ----------------------------------------------------------------


@router.get("/{slug}/members")
async def list_members(
    slug: str,
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    org, _member = await orgsvc.require_membership(db, user.id, slug)
    rows, total = await orgsvc.list_members(db, org.id, limit=limit, offset=offset)
    items = [public_member(m, u) for m, u in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.patch("/{slug}/members/{user_id}")
async def patch_member(
    slug: str, user_id: uuid.UUID, payload: MemberRoleIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    org, _actor = await orgsvc.require_role(db, user.id, slug, orgsvc.OWNER)
    member = await orgsvc.set_member_role(db, org.id, user_id, payload.role)
    target = await db.get(User, user_id)
    assert target is not None
    return public_member(member, target)


@router.delete("/{slug}/members/{user_id}")
async def delete_member(
    slug: str, user_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> dict[str, bool]:
    org, _actor = await orgsvc.require_role(db, user.id, slug, orgsvc.OWNER)
    await orgsvc.remove_member(db, org.id, user_id)
    return {"removed": True}


# --- Invites (owner-administered) --------------------------------------------


@router.post("/{slug}/invites", status_code=201)
async def create_invite(
    slug: str, payload: InviteCreateIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    org, _owner = await orgsvc.require_role(db, user.id, slug, orgsvc.OWNER)
    invite, raw_token = await orgsvc.create_invite(
        db,
        org,
        created_by=user.id,
        email=payload.email,
        role=payload.role,
        hours=payload.expires_in_hours,
    )
    # The plaintext token is returned exactly once and never stored.
    return {**orgsvc.public_invite_view(invite, org), "token": raw_token}


# --- Cohorts -----------------------------------------------------------------


@router.post("/{slug}/cohorts", status_code=201)
async def create_cohort(
    slug: str, payload: CohortCreateIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    org, _actor = await orgsvc.require_role(db, user.id, slug, orgsvc.INSTRUCTOR)
    cohort = await orgsvc.create_cohort(
        db,
        org,
        name=payload.name,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        metadata_json=payload.metadata,
    )
    return public_cohort(cohort, member_count=0)


@router.get("/{slug}/cohorts")
async def list_cohorts(slug: str, user: CurrentUser, db: DbSession) -> list[dict[str, object]]:
    org, _member = await orgsvc.require_membership(db, user.id, slug)
    cohorts = await orgsvc.list_cohorts(db, org.id)
    counts = {c.id: len(await orgsvc.list_cohort_members(db, c.id)) for c in cohorts}
    return [public_cohort(c, member_count=counts[c.id]) for c in cohorts]


@router.get("/{slug}/cohorts/{cohort_id}")
async def get_cohort(
    slug: str, cohort_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    org, _member = await orgsvc.require_membership(db, user.id, slug)
    cohort = await orgsvc.get_cohort(db, org.id, cohort_id)
    members = await orgsvc.list_cohort_members(db, cohort.id)
    view = public_cohort(cohort, member_count=len(members))
    view["members"] = [
        {
            "user_id": str(u.id),
            "username": u.username,
            "added_by": str(m.added_by) if m.added_by else None,
            "joined_at": m.joined_at.isoformat(),
        }
        for m, u in members
    ]
    return view


@router.patch("/{slug}/cohorts/{cohort_id}")
async def patch_cohort(
    slug: str, cohort_id: uuid.UUID, payload: CohortUpdateIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    org, _actor = await orgsvc.require_role(db, user.id, slug, orgsvc.INSTRUCTOR)
    cohort = await orgsvc.get_cohort(db, org.id, cohort_id)
    await orgsvc.update_cohort(
        db,
        cohort,
        name=payload.name,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        metadata_json=payload.metadata,
    )
    return public_cohort(cohort)


@router.delete("/{slug}/cohorts/{cohort_id}")
async def delete_cohort(
    slug: str, cohort_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> dict[str, bool]:
    org, _actor = await orgsvc.require_role(db, user.id, slug, orgsvc.INSTRUCTOR)
    cohort = await orgsvc.get_cohort(db, org.id, cohort_id)
    await db.delete(cohort)
    await db.flush()
    return {"deleted": True}


@router.post("/{slug}/cohorts/{cohort_id}/members")
async def add_cohort_member(
    slug: str, cohort_id: uuid.UUID, payload: CohortMemberIn, user: CurrentUser, db: DbSession
) -> dict[str, bool]:
    org, actor = await orgsvc.require_role(db, user.id, slug, orgsvc.INSTRUCTOR)
    cohort = await orgsvc.get_cohort(db, org.id, cohort_id)
    await orgsvc.add_cohort_member(db, org, cohort, user_id=payload.user_id, added_by=actor.user_id)
    return {"added": True}


@router.delete("/{slug}/cohorts/{cohort_id}/members/{user_id}")
async def remove_cohort_member(
    slug: str, cohort_id: uuid.UUID, user_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> dict[str, bool]:
    org, _actor = await orgsvc.require_role(db, user.id, slug, orgsvc.INSTRUCTOR)
    cohort = await orgsvc.get_cohort(db, org.id, cohort_id)
    await orgsvc.remove_cohort_member(db, cohort, user_id)
    return {"removed": True}


# --- Assignments --------------------------------------------------------------


@router.post("/{slug}/assignments", status_code=201)
async def create_assignment(
    slug: str, payload: AssignmentCreateIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    org, actor = await orgsvc.require_role(db, user.id, slug, orgsvc.INSTRUCTOR)
    assignment = await orgsvc.create_assignment(
        db,
        org,
        created_by=actor.user_id,
        content_kind=payload.content_kind,
        content_slug=payload.content_slug,
        cohort_id=payload.cohort_id,
        due_at=payload.due_at,
    )
    return public_assignment(assignment)


@router.get("/{slug}/assignments")
async def list_assignments(slug: str, user: CurrentUser, db: DbSession) -> list[dict[str, object]]:
    org, _member = await orgsvc.require_membership(db, user.id, slug)
    assignments = await orgsvc.list_assignments(db, org.id)
    return [public_assignment(a) for a in assignments]


@router.get("/{slug}/assignments/{assignment_id}/progress")
async def assignment_progress(
    slug: str, assignment_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> list[dict[str, object]]:
    org, _actor = await orgsvc.require_role(db, user.id, slug, orgsvc.INSTRUCTOR)
    assignment = await orgsvc.get_assignment(db, org.id, assignment_id)
    return await orgsvc.assignment_progress(db, org, assignment)


# --- Public invite flow ---------------------------------------------------------


@invite_router.get("/{token}")
async def preview_invite(token: str, db: DbSession) -> dict[str, object]:
    # Token knowledge is the credential; login is not required.
    return await orgsvc.preview_invite(db, token)


@invite_router.post("/{token}/accept")
async def accept_invite(token: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    return await orgsvc.accept_invite(db, user, token)


__all__ = ["api_router"]
