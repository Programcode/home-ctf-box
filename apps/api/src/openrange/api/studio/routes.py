"""Content Studio HTTP routes: /api/studio.

Authorization model (plan Phase 10 core):
- any authenticated user may create and edit their own drafts;
- drafts are 404-isolated: users without a stake cannot see them;
- review and publish need the matching RBAC permission or a listing in
  the draft's reviewers; the author can never review their own draft.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import Response
from openrange.api.auth.dependencies import CurrentUser, DbSession
from openrange.api.auth.service import AuthError
from openrange.api.studio import service as studio
from openrange.api.studio.models import ContentDraft, DraftReview, PublishEvent
from openrange.api.users.models import User
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(prefix="/api/studio", tags=["studio"])

DraftKind = Literal["room", "module", "path"]


class DraftCreateIn(BaseModel):
    kind: DraftKind
    slug: str = Field(pattern=studio.SLUG_PATTERN)
    base_ref: str = Field(default="", max_length=256)


class ReviewIn(BaseModel):
    state: Literal["approved", "changes_requested"]
    note: str = Field(default="", max_length=8000)


def public_draft(draft: ContentDraft) -> dict[str, object]:
    return {
        "id": str(draft.id),
        "kind": draft.kind,
        "slug": draft.slug,
        "base_ref": draft.base_ref,
        "status": draft.status,
        "author_id": str(draft.author_id),
        "reviewers": list(draft.reviewers or []),
        "created_at": draft.created_at.isoformat(),
        "updated_at": draft.updated_at.isoformat(),
    }


def public_event(event: PublishEvent) -> dict[str, object]:
    return {
        "id": str(event.id),
        "event": event.event,
        "actor_id": str(event.actor_id) if event.actor_id else None,
        "detail": dict(event.detail or {}),
        "created_at": event.created_at.isoformat(),
    }


def _is_content_admin(user: User) -> bool:
    return user.has_permission("content:manage")


def _can_review(user: User) -> bool:
    return (
        user.has_permission("content:review-technical")
        or user.has_permission("content:review-instructional")
        or user.has_permission("content:review-security")
    )


async def get_visible_draft(db: DbSession, draft_id: uuid.UUID, user: User) -> ContentDraft:
    """Fetch the draft or 404 when the caller has no stake in it."""
    draft = await db.get(ContentDraft, draft_id)
    if draft is None:
        raise AuthError("draft not found", 404)
    if _is_content_admin(user):
        return draft
    if draft.author_id == user.id:
        return draft
    listed = str(user.id) in [str(r) for r in (draft.reviewers or [])]
    # Listed reviewers follow their draft; unlisted reviewers may open
    # anything currently sitting in the review queue.
    if listed or (_can_review(user) and draft.status == "in_review"):
        return draft
    raise AuthError("draft not found", 404)


async def require_editable_draft(db: DbSession, draft_id: uuid.UUID, user: User) -> ContentDraft:
    """Drafts are editable by their author; content admins too."""
    draft = await db.get(ContentDraft, draft_id)
    if draft is None:
        raise AuthError("draft not found", 404)
    if draft.author_id != user.id and not _is_content_admin(user):
        raise AuthError("draft not found", 404)
    if draft.status == "published":
        raise AuthError("published drafts are read-only", 409)
    return draft


# --- Draft lifecycle ----------------------------------------------------------


@router.post("/drafts", status_code=201)
async def create_draft(
    payload: DraftCreateIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    draft_id = uuid.uuid4()
    draft = ContentDraft(
        id=draft_id,
        kind=payload.kind,
        slug=payload.slug,
        base_ref=payload.base_ref,
        author_id=user.id,
        content_root=studio.create_workspace(draft_id, payload.kind, payload.slug),
    )
    db.add(draft)
    await db.flush()
    return public_draft(draft)


@router.get("/drafts")
async def list_drafts(
    user: CurrentUser,
    db: DbSession,
    status: Annotated[str | None, Query()] = None,
    kind: Annotated[DraftKind | None, Query()] = None,
) -> list[dict[str, object]]:
    query = select(ContentDraft).order_by(ContentDraft.created_at)
    # Regular users only ever see their own drafts.
    if not _is_content_admin(user):
        query = query.where(ContentDraft.author_id == user.id)
    if status is not None:
        query = query.where(ContentDraft.status == status)
    if kind is not None:
        query = query.where(ContentDraft.kind == kind)
    drafts = (await db.execute(query)).scalars().all()
    return [public_draft(d) for d in drafts]


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: uuid.UUID, user: CurrentUser, db: DbSession) -> dict[str, object]:
    draft = await get_visible_draft(db, draft_id, user)
    return public_draft(draft)


@router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: uuid.UUID, user: CurrentUser, db: DbSession) -> dict[str, bool]:
    draft = await db.get(ContentDraft, draft_id)
    if draft is None or (draft.author_id != user.id and not _is_content_admin(user)):
        raise AuthError("draft not found", 404)
    if draft.status == "published":
        raise AuthError("published drafts are part of the audit trail", 409)
    studio.remove_workspace(draft)
    await db.delete(draft)
    await db.flush()
    return {"deleted": True}


# --- Workspace files ------------------------------------------------------------


@router.put("/drafts/{draft_id}/files/{file_path:path}")
async def put_file(
    draft_id: uuid.UUID,
    file_path: str,
    request: Request,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    draft = await require_editable_draft(db, draft_id, user)
    content = await request.body()
    written = studio.write_file(draft, file_path, content)
    await db.flush()
    return {"written": True, "path": written.path, "size": written.size}


@router.post("/drafts/{draft_id}/bundle")
async def upload_bundle(
    draft_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(description="zip archive of the bundle tree")],
) -> dict[str, object]:
    draft = await require_editable_draft(db, draft_id, user)
    assert file.file is not None
    archive = await file.read()
    written = studio.extract_bundle(draft, archive)
    await db.flush()
    return {"extracted": len(written), "files": sorted(written)}


@router.get("/drafts/{draft_id}/files")
async def list_files(draft_id: uuid.UUID, user: CurrentUser, db: DbSession) -> dict[str, object]:
    draft = await get_visible_draft(db, draft_id, user)
    files = studio.list_files(draft)
    return {"files": [{"path": f.path, "size": f.size} for f in files]}


@router.get("/drafts/{draft_id}/file")
async def read_file(
    draft_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    path: Annotated[str, Query()],
) -> Response:
    draft = await get_visible_draft(db, draft_id, user)
    content = studio.read_file(draft, path)
    return Response(content=content, media_type="text/plain; charset=utf-8")


# --- Validation -----------------------------------------------------------------


@router.post("/drafts/{draft_id}/validate")
async def validate_draft(draft_id: uuid.UUID, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    draft = await get_visible_draft(db, draft_id, user)
    return studio.validate_draft(draft)


# --- Review workflow --------------------------------------------------------------


@router.post("/drafts/{draft_id}/submit")
async def submit_draft(draft_id: uuid.UUID, user: CurrentUser, db: DbSession) -> dict[str, object]:
    draft = await require_editable_draft(db, draft_id, user)
    if draft.status not in ("draft", "changes_requested"):
        raise AuthError(f"cannot submit a draft in status {draft.status}", 409)
    draft.status = "in_review"
    await studio.record_event(db, draft, "submitted", user.id)
    await db.refresh(draft)
    return public_draft(draft)


@router.post("/drafts/{draft_id}/review")
async def review_draft(
    draft_id: uuid.UUID,
    payload: ReviewIn,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    draft = await db.get(ContentDraft, draft_id)
    if draft is None:
        raise AuthError("draft not found", 404)
    listed = str(user.id) in [str(r) for r in (draft.reviewers or [])]
    if draft.author_id != user.id and not (listed or _can_review(user) or _is_content_admin(user)):
        raise AuthError("draft not found", 404)
    # Two-person rule: authors never review their own submissions.
    if draft.author_id == user.id:
        raise AuthError("authors cannot review their own drafts", 403)
    if draft.status != "in_review":
        raise AuthError(f"cannot review a draft in status {draft.status}", 409)

    review = DraftReview(
        draft_id=draft.id, reviewer_id=user.id, state=payload.state, note=payload.note
    )
    db.add(review)
    draft.status = "approved" if payload.state == "approved" else "changes_requested"
    if not listed:
        draft.reviewers = [*list(draft.reviewers or []), str(user.id)]
    event = "approved" if payload.state == "approved" else "rejected"
    await studio.record_event(
        db, draft, event, user.id, {"state": payload.state, "note": payload.note}
    )
    await db.refresh(draft)
    return public_draft(draft)


@router.post("/drafts/{draft_id}/publish")
async def publish_draft(draft_id: uuid.UUID, user: CurrentUser, db: DbSession) -> dict[str, object]:
    if not user.has_permission("content:publish"):
        raise AuthError("publishing requires the content:publish permission", 403)
    draft = await get_visible_draft(db, draft_id, user)
    if draft.status == "published":
        raise AuthError("draft is already published", 409)
    if draft.status != "approved":
        raise AuthError("draft must be approved before publishing", 409)
    if not await studio.has_approved_review(db, draft.id):
        raise AuthError("at least one approved review is required before publishing", 409)

    result = studio.validate_draft(draft)
    if not result["ok"]:
        raise AuthError("draft failed validation; fix findings before publishing", 409)
    published = await studio.publish_draft(db, draft, user.id)
    draft.status = "published"
    await db.flush()
    await db.refresh(draft)
    return {**public_draft(draft), **published}


@router.get("/drafts/{draft_id}/events")
async def list_events(
    draft_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> list[dict[str, object]]:
    draft = await get_visible_draft(db, draft_id, user)
    events = await db.execute(
        select(PublishEvent)
        .where(PublishEvent.draft_id == draft.id)
        .order_by(PublishEvent.created_at)
    )
    return [public_event(e) for e in events.scalars().all()]
