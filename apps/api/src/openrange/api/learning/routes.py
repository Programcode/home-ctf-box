"""Learning HTTP routes: /api/learning."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from openrange.api.auth.dependencies import CurrentUser, DbSession
from openrange.api.auth.service import AuthError
from openrange.api.learning import content as learning_content
from openrange.api.learning import service as learning
from openrange.content.i18n import resolve_locale
from openrange.content.loader import (
    apply_section_overrides,
    available_locales,
    load_locale_overrides,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/learning", tags=["learning"])


def _progress_permission(user: CurrentUser) -> None:
    if not user.has_permission("progress:own"):
        raise AuthError("missing permission progress:own", 403)


class QuizAttemptIn(BaseModel):
    answers: dict[str, list[str]]
    module: str | None = None


class NoteIn(BaseModel):
    scope: str
    ref: str
    body: str


@router.get("/paths")
async def list_paths(user: CurrentUser, db: DbSession) -> list[dict[str, object]]:
    _progress_permission(user)
    return await learning.paths_overview(db, user.id)


@router.get("/paths/{slug}")
async def path_detail(slug: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    _progress_permission(user)
    return await learning.path_detail(db, user.id, slug)


@router.post("/paths/{slug}/enroll")
async def enroll(slug: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    _progress_permission(user)
    enrollment = await learning.enroll(db, user.id, slug)
    return {
        "enrollment_id": str(enrollment.id),
        "path_slug": enrollment.path_slug,
        "state": enrollment.state,
    }


@router.post("/paths/{slug}/pause")
async def pause(slug: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    _progress_permission(user)
    enrollment = await learning.pause(db, user.id, slug)
    return {"path_slug": enrollment.path_slug, "state": enrollment.state}


@router.post("/paths/{slug}/resume")
async def resume(slug: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    _progress_permission(user)
    enrollment = await learning.resume(db, user.id, slug)
    return {"path_slug": enrollment.path_slug, "state": enrollment.state}


@router.get("/modules/{slug}")
async def module_detail(
    slug: str,
    user: CurrentUser,
    lang: Annotated[str, Query(max_length=16)] = "en",
) -> dict[str, object]:
    _progress_permission(user)
    module = learning_content.get_module_bundle(slug)
    if module is None:
        raise AuthError("unknown module", 404)
    module_dir = learning_content.content_root() / "modules" / slug
    resolved = resolve_locale(lang, available_locales(module_dir))
    payload = learning.public_module(module)
    if resolved != "en":
        overrides = load_locale_overrides(module_dir, resolved)
        if overrides is not None:
            payload = learning.public_module(apply_section_overrides(module, overrides))
    payload["locale"] = resolved
    return payload


@router.post("/modules/{slug}/sections/{section_id}/complete")
async def complete_section(
    slug: str, section_id: str, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    _progress_permission(user)
    return await learning.complete_section(db, user.id, slug, section_id)


@router.post("/quiz/{section_id}/attempt")
async def quiz_attempt(
    section_id: str, payload: QuizAttemptIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    _progress_permission(user)
    return await learning.quiz_attempt(db, user.id, section_id, payload.answers, payload.module)


@router.get("/notes/search")
async def search_notes(
    user: CurrentUser,
    db: DbSession,
    q: Annotated[str, Query(min_length=1)],
) -> list[dict[str, object]]:
    _progress_permission(user)
    return await learning.search_notes(db, user.id, q)


@router.get("/notes")
async def get_note(
    user: CurrentUser,
    db: DbSession,
    scope: str = Query(),
    ref: str = Query(),
) -> dict[str, object]:
    _progress_permission(user)
    return await learning.get_note(db, user.id, scope, ref)


@router.put("/notes")
async def put_note(payload: NoteIn, user: CurrentUser, db: DbSession) -> dict[str, object]:
    _progress_permission(user)
    note = await learning.put_note(db, user.id, payload.scope, payload.ref, payload.body)
    return learning.public_note(note)


@router.post("/hints/{room_slug}/{task_ref}")
async def hint(
    room_slug: str, task_ref: str, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    _progress_permission(user)
    return await learning.hint_reveal(db, user.id, room_slug, task_ref)


@router.get("/certificates/{path_slug}")
async def certificate(path_slug: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    _progress_permission(user)
    return await learning.issue_certificate(db, user.id, path_slug)


@router.get("/me/progress")
async def my_progress(user: CurrentUser, db: DbSession) -> dict[str, object]:
    _progress_permission(user)
    return await learning.my_progress(db, user.id)


@router.get("/enrollments/{enrollment_id}")
async def enrollment_detail(
    enrollment_id: str, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    # Learners read their own records; instructors/admins (reports:read)
    # may read any. Ownership is enforced against the record itself.
    try:
        eid = uuid.UUID(enrollment_id)
    except ValueError as exc:
        raise AuthError("unknown enrollment", 404) from exc
    if not user.has_permission("progress:own") and not user.has_permission("reports:read"):
        raise AuthError("missing permission progress:own", 403)
    can_read_any = user.has_permission("reports:read")
    return await learning.enrollment_progress(db, user.id, can_read_any, eid)
