"""Learning engine domain logic (plan Phase 8).

Enrollment lifecycle, prerequisite-ordered section progress, server-side
quiz grading against bundle answer keys, progressive hint reveals with
cost events, autosaved notes, and signed completion certificates.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from openrange.api.auth.service import AuthError
from openrange.api.config import get_settings
from openrange.api.learning import content as learning_content
from openrange.api.learning.models import (
    Certificate,
    Enrollment,
    HintEvent,
    Note,
    QuizAttempt,
    SectionProgress,
)
from openrange.content.models import ModuleBundle, PathBundle, QuizBlock, RoomBundle, Section
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ACTIVE = "active"
PAUSED = "paused"
COMPLETED = "completed"


def _require_path(slug: str) -> PathBundle:
    bundle = learning_content.get_path_bundle(slug)
    if bundle is None:
        raise AuthError("unknown path", 404)
    return bundle


async def _user_enrollments(db: AsyncSession, user_id: uuid.UUID) -> list[Enrollment]:
    rows = await db.execute(
        select(Enrollment)
        .where(Enrollment.user_id == user_id)
        .order_by(Enrollment.created_at.desc())
    )
    return list(rows.scalars().all())


async def _completed_pairs(db: AsyncSession, enrollment_id: uuid.UUID) -> set[tuple[str, str]]:
    rows = await db.execute(
        select(SectionProgress.module_slug, SectionProgress.section_id).where(
            SectionProgress.enrollment_id == enrollment_id,
            SectionProgress.status == "completed",
        )
    )
    return {(module, section) for module, section in rows.all()}


# --- Enrollment lifecycle -------------------------------------------------


async def enroll(db: AsyncSession, user_id: uuid.UUID, path_slug: str) -> Enrollment:
    _require_path(path_slug)
    existing = (
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
    for enrollment in existing:
        if enrollment.state in (ACTIVE, PAUSED):
            raise AuthError("already enrolled", 409)
    # A completed run may be restarted; the fresh enrollment starts clean.
    bundle = learning_content.get_path_bundle(path_slug)
    assert bundle is not None
    enrollment = Enrollment(
        user_id=user_id, path_slug=path_slug, path_version=bundle.metadata.version
    )
    db.add(enrollment)
    await db.flush()
    return enrollment


async def _own_enrollment_for_path(
    db: AsyncSession, user_id: uuid.UUID, path_slug: str
) -> Enrollment:
    row = (
        await db.execute(
            select(Enrollment)
            .where(
                Enrollment.user_id == user_id,
                Enrollment.path_slug == path_slug,
                Enrollment.state.in_([ACTIVE, PAUSED]),
            )
            .order_by(Enrollment.created_at.desc())
        )
    ).scalar_one_or_none()
    if row is None:
        raise AuthError("not enrolled", 404)
    return row


async def pause(db: AsyncSession, user_id: uuid.UUID, path_slug: str) -> Enrollment:
    enrollment = await _own_enrollment_for_path(db, user_id, path_slug)
    if enrollment.state != ACTIVE:
        raise AuthError("only active enrollments can be paused", 409)
    enrollment.state = PAUSED
    await db.flush()
    return enrollment


async def resume(db: AsyncSession, user_id: uuid.UUID, path_slug: str) -> Enrollment:
    enrollment = await _own_enrollment_for_path(db, user_id, path_slug)
    if enrollment.state != PAUSED:
        raise AuthError("only paused enrollments can be resumed", 409)
    enrollment.state = ACTIVE
    await db.flush()
    return enrollment


# --- Views ---------------------------------------------------------------


def public_block(block: Any) -> dict[str, object]:
    """Client-safe block view. Answer keys and explanations never leave."""
    data: dict[str, object] = {"type": block.type}
    if block.type in {"prose", "callout"}:
        data["markdown"] = block.markdown
        if block.type == "callout":
            data["tone"] = block.tone
    elif block.type == "code":
        data["language"] = block.language
        data["code"] = block.code
    elif isinstance(block, QuizBlock):
        data["question_id"] = block.question_id
        data["question"] = block.question
        data["options"] = [{"id": o.id, "text": o.text} for o in block.options]
    return data


def public_section(section: Section) -> dict[str, object]:
    return {
        "id": section.id,
        "title": section.title,
        "blocks": [public_block(b) for b in section.blocks],
    }


def public_module(module: ModuleBundle) -> dict[str, object]:
    return {
        "slug": module.metadata.slug,
        "title": module.metadata.title,
        "version": module.metadata.version,
        "summary": module.spec.summary,
        "objectives": list(module.spec.objectives),
        "labs": list(module.spec.labs),
        "cheat_sheet": module.spec.cheat_sheet,
        "sections": [public_section(s) for s in module.spec.sections],
    }


def public_path(bundle: PathBundle) -> dict[str, object]:
    return {
        "slug": bundle.metadata.slug,
        "title": bundle.metadata.title,
        "version": bundle.metadata.version,
        "difficulty": bundle.metadata.difficulty,
        "estimated_minutes": bundle.metadata.estimated_minutes,
        "summary": bundle.spec.summary,
        "capstones": list(bundle.spec.capstones),
        "certificate": bundle.spec.certificate,
    }


async def paths_overview(db: AsyncSession, user_id: uuid.UUID) -> list[dict[str, object]]:
    states = {
        e.path_slug: e.state
        for e in reversed(await _user_enrollments(db, user_id))  # earliest wins display
    }
    overview: list[dict[str, object]] = []
    for bundle in learning_content.list_path_bundles():
        view = public_path(bundle)
        view["enrollment_state"] = states.get(bundle.metadata.slug)
        overview.append(view)
    return overview


async def path_detail(db: AsyncSession, user_id: uuid.UUID, slug: str) -> dict[str, object]:
    bundle = _require_path(slug)
    outline = learning_content.path_outline(bundle)
    completed: set[tuple[str, str]] = set()
    state: str | None = None
    for enrollment in await _user_enrollments(db, user_id):
        if enrollment.path_slug != slug:
            continue
        state = enrollment.state
        if enrollment.state in (ACTIVE, COMPLETED, PAUSED):
            completed |= await _completed_pairs(db, enrollment.id)
    modules_view: list[dict[str, object]] = []
    for ref in bundle.spec.modules:
        module = learning_content.get_module_bundle(ref.slug)
        if module is None:  # pragma: no cover - outline build validates first
            continue
        sections: list[dict[str, object]] = []
        for sref in outline.sections:
            if sref.module_slug != ref.slug:
                continue
            sections.append(
                {
                    "id": sref.section_id,
                    "title": sref.title,
                    "order_index": sref.order_index,
                    "optional_branch": sref.optional_branch,
                    "prerequisites": [{"module": m, "section": s} for m, s in sref.prerequisites],
                    "completed": (ref.slug, sref.section_id) in completed,
                }
            )
        modules_view.append(
            {
                "slug": ref.slug,
                "title": module.metadata.title,
                "optional_branch": ref.optional_branch,
                "sections": sections,
            }
        )
    view = public_path(bundle)
    view.update({"enrollment_state": state, "modules": modules_view})
    return view


# --- Progress -------------------------------------------------------------


async def complete_section(
    db: AsyncSession, user_id: uuid.UUID, module_slug: str, section_id: str
) -> dict[str, object]:
    candidates: list[tuple[Enrollment, learning_content.SectionRef]] = []
    for enrollment in await _user_enrollments(db, user_id):
        if enrollment.state != ACTIVE:
            continue
        bundle = learning_content.get_path_bundle(enrollment.path_slug)
        if bundle is None:
            continue
        outline = learning_content.path_outline(bundle)
        ref = outline.section(module_slug, section_id)
        if ref is not None:
            candidates.append((enrollment, ref))
    if not candidates:
        raise AuthError(
            "no active enrollment contains this section or the enrollment is paused", 409
        )

    unmet_detail: str | None = None
    for enrollment, ref in candidates:
        done = await _completed_pairs(db, enrollment.id)
        missing = [p for p in ref.prerequisites if p not in done]
        if missing:
            m, s = missing[0]
            unmet_detail = f"prerequisite {m}/{s} not completed"
            continue
        existing = (
            await db.execute(
                select(SectionProgress).where(
                    SectionProgress.enrollment_id == enrollment.id,
                    SectionProgress.module_slug == module_slug,
                    SectionProgress.section_id == section_id,
                )
            )
        ).scalar_one_or_none()
        already = existing is not None
        if not already:
            db.add(
                SectionProgress(
                    enrollment_id=enrollment.id,
                    module_slug=module_slug,
                    section_id=section_id,
                )
            )
            await db.flush()
        finished = await _maybe_complete_enrollment(db, enrollment)
        return {
            "enrollment_id": str(enrollment.id),
            "module_slug": module_slug,
            "section_id": section_id,
            "already_completed": already,
            "path_completed": finished,
        }
    raise AuthError(unmet_detail or "prerequisites not met", 409)


async def _maybe_complete_enrollment(db: AsyncSession, enrollment: Enrollment) -> bool:
    bundle = learning_content.get_path_bundle(enrollment.path_slug)
    if bundle is None:
        return False
    outline = learning_content.path_outline(bundle)
    required_sections = [s for s in outline.sections if not s.optional_branch]
    done = await _completed_pairs(db, enrollment.id)
    all_done = all(
        (s.module_slug, s.section_id) in done
        for s in required_sections
        if s.module_slug in outline.required_modules
    )
    if all_done and enrollment.state == ACTIVE:
        enrollment.state = COMPLETED
        await db.flush()
    return enrollment.state == COMPLETED


# --- Quizzes --------------------------------------------------------------


async def quiz_attempt(
    db: AsyncSession,
    user_id: uuid.UUID,
    section_id: str,
    answers: dict[str, list[str]],
    module_slug: str | None,
) -> dict[str, object]:
    try:
        module, section = learning_content.find_quiz_section(section_id, module_slug)
    except LookupError as exc:
        raise AuthError(str(exc), 404) from exc
    enrollment = await _enrollment_for_module(db, user_id, module.metadata.slug)
    quizzes = [b for b in section.blocks if isinstance(b, QuizBlock)]
    results: list[dict[str, object]] = []
    passed_all = True
    for quiz in quizzes:
        selected = sorted(answers.get(quiz.question_id, []))
        correct = sorted(quiz.answer_ids) == selected
        passed_all = passed_all and correct
        results.append({"question_id": quiz.question_id, "correct": correct})
    attempt = QuizAttempt(
        enrollment_id=enrollment.id,
        section_id=section_id,
        module_slug=module.metadata.slug,
        answers={"answers": answers},
        passed=passed_all,
    )
    db.add(attempt)
    await db.flush()
    return {
        "attempt_id": str(attempt.id),
        "section_id": section_id,
        "passed": passed_all,
        "results": results,
    }


async def _enrollment_for_module(
    db: AsyncSession, user_id: uuid.UUID, module_slug: str
) -> Enrollment:
    for enrollment in reversed(await _user_enrollments(db, user_id)):
        if enrollment.state == PAUSED:
            continue
        bundle = learning_content.get_path_bundle(enrollment.path_slug)
        if bundle is None:
            continue
        if any(ref.slug == module_slug for ref in bundle.spec.modules):
            return enrollment
    raise AuthError("no enrollment covers this module or it is paused", 409)


# --- Notes ----------------------------------------------------------------


async def put_note(db: AsyncSession, user_id: uuid.UUID, scope: str, ref: str, body: str) -> Note:
    if scope not in {"room", "module"}:
        raise AuthError("scope must be room or module", 422)
    note = (
        await db.execute(
            select(Note).where(Note.user_id == user_id, Note.scope == scope, Note.ref == ref)
        )
    ).scalar_one_or_none()
    if note is None:
        note = Note(user_id=user_id, scope=scope, ref=ref, body=body)
        db.add(note)
    else:
        note.body = body
    await db.flush()
    # Server-managed timestamps must be reloaded outside the greenlet
    # before they are serialized into the response.
    await db.refresh(note)
    return note


def public_note(note: Note) -> dict[str, object]:
    return {
        "scope": note.scope,
        "ref": note.ref,
        "body": note.body,
        "updated_at": note.updated_at.isoformat(),
    }


async def get_note(db: AsyncSession, user_id: uuid.UUID, scope: str, ref: str) -> dict[str, object]:
    if scope not in {"room", "module"}:
        raise AuthError("scope must be room or module", 422)
    note = (
        await db.execute(
            select(Note).where(Note.user_id == user_id, Note.scope == scope, Note.ref == ref)
        )
    ).scalar_one_or_none()
    if note is None:
        raise AuthError("note not found", 404)
    return public_note(note)


async def search_notes(db: AsyncSession, user_id: uuid.UUID, query: str) -> list[dict[str, object]]:
    rows = await db.execute(
        select(Note)
        .where(Note.user_id == user_id, Note.body.contains(query, autoescape=True))
        .order_by(Note.updated_at.desc())
        .limit(50)
    )
    return [public_note(n) for n in rows.scalars().all()]


# --- Hints ----------------------------------------------------------------


async def hint_reveal(
    db: AsyncSession, user_id: uuid.UUID, room_slug: str, task_ref: str
) -> dict[str, object]:
    room = learning_content.get_room_bundle(room_slug)
    if room is None:
        raise AuthError("unknown room", 404)
    task = next((t for t in room.spec.tasks if t.id == task_ref), None)
    if task is None:
        raise AuthError("unknown task", 404)
    enrollment = await _enrollment_covering_room(db, user_id, room)
    revealed_rows = await db.execute(
        select(HintEvent.tier)
        .where(HintEvent.enrollment_id == enrollment.id, HintEvent.task_ref == task_ref)
        .order_by(HintEvent.tier)
    )
    revealed_tiers = [int(t) for t in revealed_rows.scalars().all()]
    total = len(task.hints)

    response: dict[str, object] = {
        "room": room_slug,
        "task_ref": task_ref,
        "revealed": len(revealed_tiers),
        "total_tiers": total,
        "solution_available": total == 0 or len(revealed_tiers) >= total,
    }
    if total == 0 or len(revealed_tiers) < total:
        tier = len(revealed_tiers) + 1
        hint = task.hints[tier - 1]
        db.add(
            HintEvent(
                enrollment_id=enrollment.id,
                task_ref=task_ref,
                tier=tier,
                cost=hint.cost,
            )
        )
        await db.flush()
        response.update({"tier": tier, "text": hint.text, "cost": hint.cost, "solution": None})
        return response
    # All tiers revealed (or none exist): the full solution unlocks.
    response.update({"tier": None, "text": None, "cost": 0, "solution": task.solution})
    return response


async def _enrollment_covering_room(
    db: AsyncSession, user_id: uuid.UUID, room: RoomBundle
) -> Enrollment:
    for enrollment in reversed(await _user_enrollments(db, user_id)):
        if enrollment.state == PAUSED:
            continue
        bundle = learning_content.get_path_bundle(enrollment.path_slug)
        if bundle is None:
            continue
        if room.metadata.slug in bundle.spec.capstones:
            return enrollment
        for ref in bundle.spec.modules:
            module = learning_content.get_module_bundle(ref.slug)
            if module is not None and room.metadata.slug in module.spec.labs:
                return enrollment
    raise AuthError("no active enrollment covers this room", 409)


# --- Certificates ---------------------------------------------------------


def _canonical_snapshot(
    user_id: uuid.UUID, bundle: PathBundle, completed: list[tuple[str, str]]
) -> str:
    snapshot = {
        "path": bundle.metadata.slug,
        "version": bundle.metadata.version,
        "user": str(user_id),
        "sections": sorted(f"{m}/{s}" for m, s in completed),
        "issued_at": datetime.now(UTC).date().isoformat(),
    }
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"))


def _sign(user_id: uuid.UUID, bundle: PathBundle, completion_hash: str) -> str:
    settings = get_settings()
    key = settings.secret_key or "openrange-dev-certificate-key"
    message = f"{user_id}|{bundle.metadata.slug}|{bundle.metadata.version}|{completion_hash}"
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


async def issue_certificate(
    db: AsyncSession, user_id: uuid.UUID, path_slug: str
) -> dict[str, object]:
    bundle = _require_path(path_slug)
    existing = (
        await db.execute(
            select(Certificate).where(
                Certificate.user_id == user_id, Certificate.path_slug == path_slug
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return _certificate_view(existing)

    enrollments = [e for e in await _user_enrollments(db, user_id) if e.path_slug == path_slug]
    if not enrollments:
        raise AuthError("not enrolled", 404)
    outline = learning_content.path_outline(bundle)
    required = {s.module_slug for s in outline.sections if not s.optional_branch}
    completed: set[tuple[str, str]] = set()
    for enrollment in enrollments:
        completed |= await _completed_pairs(db, enrollment.id)
    required_sections = [
        (s.module_slug, s.section_id) for s in outline.sections if not s.optional_branch
    ]
    missing = [pair for pair in required_sections if pair not in completed]
    if missing:
        m, s = missing[0]
        raise AuthError(f"required module {m} incomplete ({m}/{s} outstanding)", 409)

    canonical = _canonical_snapshot(user_id, bundle, sorted(completed))
    completion_hash = hashlib.sha256(canonical.encode()).hexdigest()
    certificate = Certificate(
        user_id=user_id,
        path_slug=path_slug,
        path_version=bundle.metadata.version,
        payload={
            "completion_hash": completion_hash,
            "signature": _sign(user_id, bundle, completion_hash),
            "required_modules": sorted(required),
            "completed_sections": sorted(f"{m}/{s}" for m, s in completed),
        },
    )
    db.add(certificate)
    await db.flush()
    return _certificate_view(certificate)


def _certificate_view(certificate: Certificate) -> dict[str, object]:
    return {
        "id": str(certificate.id),
        "user_id": str(certificate.user_id),
        "path_slug": certificate.path_slug,
        "path_version": certificate.path_version,
        "issued_at": certificate.issued_at.isoformat(),
        "payload": dict(certificate.payload),
    }


# --- Raw progress ---------------------------------------------------------


async def my_progress(db: AsyncSession, user_id: uuid.UUID) -> dict[str, object]:
    enrollments_view: list[dict[str, object]] = []
    for enrollment in await _user_enrollments(db, user_id):
        bundle = learning_content.get_path_bundle(enrollment.path_slug)
        modules_view: list[dict[str, object]] = []
        if bundle is not None:
            outline = learning_content.path_outline(bundle)
            done = await _completed_pairs(db, enrollment.id)
            per_module: dict[str, tuple[int, int]] = {}
            for sref in outline.sections:
                total, complete = per_module.get(sref.module_slug, (0, 0))
                per_module[sref.module_slug] = (
                    total + 1,
                    complete + ((sref.module_slug, sref.section_id) in done),
                )
            modules_view = [
                {"slug": slug, "sections_total": t, "sections_completed": c}
                for slug, (t, c) in per_module.items()
            ]
        attempts_count = len(
            (
                await db.execute(
                    select(QuizAttempt.id).where(QuizAttempt.enrollment_id == enrollment.id)
                )
            ).all()
        )
        hints_cost = sum(
            (
                await db.execute(
                    select(HintEvent.cost).where(HintEvent.enrollment_id == enrollment.id)
                )
            ).scalars()
        )
        enrollments_view.append(
            {
                "enrollment_id": str(enrollment.id),
                "path_slug": enrollment.path_slug,
                "state": enrollment.state,
                "modules": modules_view,
                "quiz_attempts": attempts_count,
                "hint_cost_total": int(hints_cost),
            }
        )
    certs = await db.execute(select(Certificate).where(Certificate.user_id == user_id))
    return {
        "enrollments": enrollments_view,
        "certificates": [_certificate_view(c) for c in certs.scalars().all()],
    }


async def enrollment_progress(
    db: AsyncSession, requester_id: uuid.UUID, can_read_any: bool, enrollment_id: uuid.UUID
) -> dict[str, object]:
    """Own enrollments always readable; instructors/admins read any."""
    enrollment = await db.get(Enrollment, enrollment_id)
    if enrollment is None or (enrollment.user_id != requester_id and not can_read_any):
        # Existence of other users' enrollments stays hidden without rights.
        raise AuthError("unknown enrollment", 404)
    done = await _completed_pairs(db, enrollment.id)
    sections = sorted(f"{m}/{s}" for m, s in done)
    return {
        "enrollment_id": str(enrollment.id),
        "user_id": str(enrollment.user_id),
        "path_slug": enrollment.path_slug,
        "path_version": enrollment.path_version,
        "state": enrollment.state,
        "completed_sections": sections,
    }
