"""Organization domain logic (plan Phase 11).

Role model per organization: owner > instructor > member. Reads inside
an org need any membership; cohort/assignment writes need instructor+;
org, member, and invite administration needs owner. Non-members always
get 404 so cross-org probing learns nothing.

Assignment progress is derived lazily from the learning engine's
read-model tables (enrollments + section_progress). The scoring module
does not exist yet; when it lands its score_events can join here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from openrange.api.auth.service import AuthError
from openrange.api.auth.tokens import generate_token, hash_token
from openrange.api.learning import content as learning_content
from openrange.api.learning.models import Enrollment, SectionProgress
from openrange.api.orgs.models import (
    Assignment,
    AssignmentProgressCache,
    Cohort,
    CohortMember,
    Organization,
    OrgInvite,
    OrgMember,
)
from openrange.api.users.models import User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

OWNER = "owner"
INSTRUCTOR = "instructor"
MEMBER = "member"

ROLE_RANK: dict[str, int] = {MEMBER: 1, INSTRUCTOR: 2, OWNER: 3}

# Slugs that would collide with collection-level route segments.
RESERVED_SLUGS = {"mine", "assignments", "invites"}

DEFAULT_INVITE_HOURS = 24 * 7
MAX_INVITE_HOURS = 24 * 30


def _now() -> datetime:
    return datetime.now(UTC)


# --- Organizations --------------------------------------------------------


async def create_org(
    db: AsyncSession, *, owner: User, name: str, display_name: str | None
) -> Organization:
    if name in RESERVED_SLUGS:
        raise AuthError("organization name is reserved", 422)
    existing = (
        await db.execute(select(Organization).where(Organization.name == name))
    ).scalar_one_or_none()
    if existing is not None:
        raise AuthError("organization name already taken", 409)
    org = Organization(name=name, display_name=display_name or name)
    db.add(org)
    await db.flush()
    db.add(OrgMember(org_id=org.id, user_id=owner.id, role=OWNER))
    await db.flush()
    return org


async def get_org_by_slug(db: AsyncSession, slug: str) -> Organization | None:
    return (
        await db.execute(select(Organization).where(Organization.name == slug))
    ).scalar_one_or_none()


async def get_membership(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> OrgMember | None:
    return (
        await db.execute(
            select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
        )
    ).scalar_one_or_none()


async def require_membership(
    db: AsyncSession, user_id: uuid.UUID, slug: str
) -> tuple[Organization, OrgMember]:
    """Membership guard. Unknown slug and non-member are the same 404."""
    org = await get_org_by_slug(db, slug)
    if org is None:
        raise AuthError("unknown organization", 404)
    member = await get_membership(db, org.id, user_id)
    if member is None:
        raise AuthError("unknown organization", 404)
    return org, member


async def require_role(
    db: AsyncSession, user_id: uuid.UUID, slug: str, minimum: str
) -> tuple[Organization, OrgMember]:
    org, member = await require_membership(db, user_id, slug)
    if ROLE_RANK.get(member.role, 0) < ROLE_RANK[minimum]:
        raise AuthError(f"requires the {minimum} role in this organization", 403)
    return org, member


async def list_orgs_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Organization, OrgMember]]:
    rows = await db.execute(
        select(OrgMember, Organization)
        .join(Organization, Organization.id == OrgMember.org_id)
        .where(OrgMember.user_id == user_id)
        .order_by(OrgMember.joined_at.asc())
    )
    return [(org, member) for member, org in rows.all()]


async def list_members(
    db: AsyncSession, org_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[tuple[OrgMember, User]], int]:
    total = int(
        (
            await db.execute(
                select(func.count()).select_from(OrgMember).where(OrgMember.org_id == org_id)
            )
        ).scalar_one()
    )
    rows = await db.execute(
        select(OrgMember, User)
        .join(User, User.id == OrgMember.user_id)
        .where(OrgMember.org_id == org_id)
        .order_by(OrgMember.joined_at.asc(), OrgMember.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return [(member, user) for member, user in rows.all()], total


async def _owner_count(
    db: AsyncSession, org_id: uuid.UUID, exclude_user: uuid.UUID | None = None
) -> int:
    stmt = (
        select(func.count())
        .select_from(OrgMember)
        .where(OrgMember.org_id == org_id, OrgMember.role == OWNER)
    )
    if exclude_user is not None:
        stmt = stmt.where(OrgMember.user_id != exclude_user)
    return int((await db.execute(stmt)).scalar_one())


async def _member_by_user(
    db: AsyncSession, org_id: uuid.UUID, target_user_id: uuid.UUID
) -> OrgMember:
    member = await get_membership(db, org_id, target_user_id)
    if member is None:
        raise AuthError("unknown member", 404)
    return member


async def set_member_role(
    db: AsyncSession, org_id: uuid.UUID, target_user_id: uuid.UUID, new_role: str
) -> OrgMember:
    member = await _member_by_user(db, org_id, target_user_id)
    if member.role == OWNER and new_role != OWNER and await _owner_count(db, org_id) <= 1:
        raise AuthError("cannot demote the last owner", 409)
    member.role = new_role
    await db.flush()
    return member


async def remove_member(db: AsyncSession, org_id: uuid.UUID, target_user_id: uuid.UUID) -> None:
    member = await _member_by_user(db, org_id, target_user_id)
    if member.role == OWNER and await _owner_count(db, org_id) <= 1:
        raise AuthError("cannot remove the last owner", 409)
    await db.delete(member)
    await db.flush()


# --- Cohorts ----------------------------------------------------------------


async def create_cohort(
    db: AsyncSession,
    org: Organization,
    *,
    name: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
    metadata_json: dict[str, Any] | None,
) -> Cohort:
    cohort = Cohort(
        org_id=org.id,
        name=name,
        starts_at=starts_at,
        ends_at=ends_at,
        metadata_json=metadata_json or {},
    )
    db.add(cohort)
    await db.flush()
    return cohort


async def list_cohorts(db: AsyncSession, org_id: uuid.UUID) -> list[Cohort]:
    rows = await db.execute(
        select(Cohort).where(Cohort.org_id == org_id).order_by(Cohort.created_at.asc())
    )
    return list(rows.scalars().all())


async def get_cohort(db: AsyncSession, org_id: uuid.UUID, cohort_id: uuid.UUID) -> Cohort:
    cohort = await db.get(Cohort, cohort_id)
    if cohort is None or cohort.org_id != org_id:
        raise AuthError("unknown cohort", 404)
    return cohort


async def update_cohort(
    db: AsyncSession,
    cohort: Cohort,
    *,
    name: str | None,
    starts_at: datetime | None,
    ends_at: datetime | None,
    metadata_json: dict[str, Any] | None,
) -> Cohort:
    if name is not None:
        cohort.name = name
    if starts_at is not None:
        cohort.starts_at = starts_at
    if ends_at is not None:
        cohort.ends_at = ends_at
    if metadata_json is not None:
        cohort.metadata_json = metadata_json
    await db.flush()
    return cohort


async def add_cohort_member(
    db: AsyncSession, org: Organization, cohort: Cohort, *, user_id: uuid.UUID, added_by: uuid.UUID
) -> CohortMember:
    if await get_membership(db, org.id, user_id) is None:
        raise AuthError("user is not a member of this organization", 422)
    existing = (
        await db.execute(
            select(CohortMember).where(
                CohortMember.cohort_id == cohort.id, CohortMember.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AuthError("user is already in this cohort", 409)
    row = CohortMember(cohort_id=cohort.id, user_id=user_id, added_by=added_by)
    db.add(row)
    await db.flush()
    return row


async def remove_cohort_member(db: AsyncSession, cohort: Cohort, user_id: uuid.UUID) -> None:
    row = (
        await db.execute(
            select(CohortMember).where(
                CohortMember.cohort_id == cohort.id, CohortMember.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise AuthError("unknown cohort member", 404)
    await db.delete(row)
    await db.flush()


async def list_cohort_members(
    db: AsyncSession, cohort_id: uuid.UUID
) -> list[tuple[CohortMember, User]]:
    rows = await db.execute(
        select(CohortMember, User)
        .join(User, User.id == CohortMember.user_id)
        .where(CohortMember.cohort_id == cohort_id)
        .order_by(CohortMember.joined_at.asc())
    )
    return [(member, user) for member, user in rows.all()]


# --- Assignments ------------------------------------------------------------


async def create_assignment(
    db: AsyncSession,
    org: Organization,
    *,
    created_by: uuid.UUID,
    content_kind: str,
    content_slug: str,
    cohort_id: uuid.UUID | None,
    due_at: datetime | None,
) -> Assignment:
    if cohort_id is not None:
        await get_cohort(db, org.id, cohort_id)  # raises unknown-cohort 404
    if content_kind == "path":
        exists = learning_content.get_path_bundle(content_slug) is not None
    else:
        exists = learning_content.get_room_bundle(content_slug) is not None
    if not exists:
        raise AuthError(f"unknown {content_kind} {content_slug!r}", 404)
    assignment = Assignment(
        org_id=org.id,
        cohort_id=cohort_id,
        content_kind=content_kind,
        content_slug=content_slug,
        due_at=due_at,
        created_by=created_by,
    )
    db.add(assignment)
    await db.flush()
    return assignment


async def list_assignments(db: AsyncSession, org_id: uuid.UUID) -> list[Assignment]:
    rows = await db.execute(
        select(Assignment).where(Assignment.org_id == org_id).order_by(Assignment.created_at.desc())
    )
    return list(rows.scalars().all())


async def get_assignment(
    db: AsyncSession, org_id: uuid.UUID, assignment_id: uuid.UUID
) -> Assignment:
    assignment = await db.get(Assignment, assignment_id)
    # Cross-org isolation: assignments from other orgs do not exist here.
    if assignment is None or assignment.org_id != org_id:
        raise AuthError("unknown assignment", 404)
    return assignment


# --- Progress derivation ----------------------------------------------------


def _required_pairs(path_slug: str) -> list[tuple[str, str]]:
    bundle = learning_content.get_path_bundle(path_slug)
    if bundle is None:
        return []
    outline = learning_content.path_outline(bundle)
    return [
        (ref.module_slug, ref.section_id)
        for ref in outline.sections
        if not ref.optional_branch and ref.module_slug in outline.required_modules
    ]


async def _derive_path_progress(
    db: AsyncSession, path_slug: str, user_id: uuid.UUID, required: list[tuple[str, str]]
) -> tuple[str, int, datetime | None]:
    """(status, percent, last_event_at) from enrollments + section_progress."""

    enrollments = (
        (
            await db.execute(
                select(Enrollment).where(
                    Enrollment.user_id == user_id, Enrollment.path_slug == path_slug
                )
            )
        )
        .scalars()
        .all()
    )
    if not enrollments:
        return "not_started", 0, None

    enrollment_ids = [e.id for e in enrollments]
    progress_rows = (
        (
            await db.execute(
                select(SectionProgress).where(
                    SectionProgress.enrollment_id.in_(enrollment_ids),
                    SectionProgress.status == "completed",
                )
            )
        )
        .scalars()
        .all()
    )
    done = {(p.module_slug, p.section_id) for p in progress_rows}
    completed_required = sum(1 for pair in required if pair in done)
    total = len(required)

    percent = 0
    if any(e.state == "completed" for e in enrollments):
        percent = 100
    elif total > 0:
        percent = completed_required * 100 // total

    if percent >= 100:
        status = "completed"
    else:
        status = "in_progress"

    last_event = max((p.completed_at for p in progress_rows), default=None)
    return status, percent, last_event


async def assignment_progress(
    db: AsyncSession, org: Organization, assignment: Assignment
) -> list[dict[str, object]]:
    """Per-learner progress rows; refreshes the cache table on read."""

    if assignment.cohort_id is not None:
        member_rows = (
            (
                await db.execute(
                    select(CohortMember.user_id).where(
                        CohortMember.cohort_id == assignment.cohort_id
                    )
                )
            )
            .scalars()
            .all()
        )
    else:
        member_rows = (
            (await db.execute(select(OrgMember.user_id).where(OrgMember.org_id == org.id)))
            .scalars()
            .all()
        )

    users: dict[uuid.UUID, User] = {}
    if member_rows:
        user_rows = (
            (await db.execute(select(User).where(User.id.in_(member_rows)).order_by(User.username)))
            .scalars()
            .all()
        )
        users = {u.id: u for u in user_rows}

    required = _required_pairs(assignment.content_slug) if assignment.content_kind == "path" else []
    # Rooms have no completion read-model yet (no scoring module); they
    # report not_started until one lands.
    derive_rooms = assignment.content_kind != "path"

    views: list[dict[str, object]] = []
    for user in users.values():
        if derive_rooms:
            status, percent, last_event = "not_started", 0, None
        else:
            status, percent, last_event = await _derive_path_progress(
                db, assignment.content_slug, user.id, required
            )
        cache_row = (
            await db.execute(
                select(AssignmentProgressCache).where(
                    AssignmentProgressCache.assignment_id == assignment.id,
                    AssignmentProgressCache.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if cache_row is None:
            cache_row = AssignmentProgressCache(
                assignment_id=assignment.id, user_id=user.id, status=status, percent=percent
            )
            db.add(cache_row)
        else:
            cache_row.status = status
            cache_row.percent = percent
        cache_row.last_event_at = last_event
        views.append(
            {
                "user_id": str(user.id),
                "username": user.username,
                "display_name": user.display_name,
                "status": status,
                "percent": percent,
                "last_event_at": last_event.isoformat() if last_event else None,
            }
        )
    views.sort(key=lambda v: str(v["username"]))
    return views


# --- Invites ----------------------------------------------------------------


async def create_invite(
    db: AsyncSession,
    org: Organization,
    *,
    created_by: uuid.UUID,
    email: str | None,
    role: str,
    hours: int,
) -> tuple[OrgInvite, str]:
    raw_token = generate_token()
    invite = OrgInvite(
        token_hash=hash_token(raw_token),
        org_id=org.id,
        email=email.lower() if email else None,
        role=role,
        expires_at=_now() + timedelta(hours=hours),
        created_by=created_by,
    )
    db.add(invite)
    await db.flush()
    return invite, raw_token


async def _invite_by_token(db: AsyncSession, raw_token: str) -> OrgInvite | None:
    return (
        await db.execute(select(OrgInvite).where(OrgInvite.token_hash == hash_token(raw_token)))
    ).scalar_one_or_none()


def mask_email(email: str) -> str:
    local, sep, domain = email.partition("@")
    if not sep:
        return "..."
    return f"{local[:1]}...@{domain}"


def public_invite_view(
    invite: OrgInvite, org: Organization, email_masked: bool = False
) -> dict[str, object]:
    shown_email = invite.email
    if shown_email and email_masked:
        shown_email = mask_email(shown_email)
    return {
        "organization": {"name": org.name, "display_name": org.display_name},
        "email": shown_email,
        "role": invite.role,
        "expires_at": invite.expires_at.isoformat(),
        "accepted": invite.accepted_at is not None,
        "expired": invite.expires_at <= _now(),
    }


async def preview_invite(db: AsyncSession, raw_token: str) -> dict[str, object]:
    """Token knowledge is the only credential needed for the preview."""
    invite = await _invite_by_token(db, raw_token)
    if invite is None:
        raise AuthError("unknown invite", 404)
    org = await db.get(Organization, invite.org_id)
    assert org is not None
    return public_invite_view(invite, org, email_masked=True)


async def accept_invite(db: AsyncSession, user: User, raw_token: str) -> dict[str, object]:
    invite = await _invite_by_token(db, raw_token)
    if invite is None:
        raise AuthError("unknown invite", 404)
    if invite.accepted_at is not None:
        raise AuthError("invite already accepted", 409)
    if invite.expires_at <= _now():
        raise AuthError("invite expired", 410)
    if invite.email is not None and (user.email or "").lower() != invite.email:
        raise AuthError("invite was issued to another account", 403)
    if await get_membership(db, invite.org_id, user.id) is not None:
        raise AuthError("already a member of this organization", 409)
    member = OrgMember(
        org_id=invite.org_id, user_id=user.id, role=invite.role, invited_by=invite.created_by
    )
    db.add(member)
    invite.accepted_at = _now()
    await db.flush()
    org = await db.get(Organization, invite.org_id)
    assert org is not None
    return {"membership": {"role": member.role}, **public_invite_view(invite, org)}
