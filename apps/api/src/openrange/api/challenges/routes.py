"""Jeopardy challenge HTTP routes: /api/challenges.

Authorization model:
- any authenticated player sees visible challenges and can submit flags
  or download attachments;
- hidden challenges are 404-invisible to non-admins (list, detail,
  submit, download);
- challenge administration (create, patch, state flips, file uploads)
  needs the content:manage permission.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse
from openrange.api.auth.dependencies import CurrentUser, DbSession
from openrange.api.auth.ratelimit import check_rate_limit
from openrange.api.auth.service import AuthError
from openrange.api.challenges import service as challenges
from openrange.api.challenges.models import Challenge, ChallengeFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

ADMIN_PERMISSION = "content:manage"

Category = Literal["web", "crypto", "pwn", "rev", "forensics", "misc", "osint"]


class DecayIn(BaseModel):
    initial: int = Field(ge=1)
    minimum: int = Field(ge=1)
    solves_to_floor: int = Field(ge=1)


class ChallengeCreateIn(BaseModel):
    slug: str = Field(pattern=challenges.SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=128)
    category: Category
    description: str = ""
    difficulty: int = Field(default=5, ge=1, le=10)
    points_base: int = Field(default=100, ge=1)
    scoring: Literal["static", "dynamic"] = "static"
    dynamic_decay: DecayIn | None = None
    flag: str = Field(min_length=1, max_length=challenges.MAX_FLAG_LENGTH)
    flag_case_sensitive: bool = False
    state: Literal["hidden", "visible"] = "hidden"


class ChallengePatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    category: Category | None = None
    description: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=10)
    points_base: int | None = Field(default=None, ge=1)
    scoring: Literal["static", "dynamic"] | None = None
    dynamic_decay: DecayIn | None = None
    flag: str | None = Field(default=None, min_length=1, max_length=challenges.MAX_FLAG_LENGTH)
    flag_case_sensitive: bool | None = None
    state: Literal["hidden", "visible"] | None = None


class FlagIn(BaseModel):
    flag: str = Field(min_length=1, max_length=challenges.MAX_FLAG_LENGTH)


def _is_admin(user: Any) -> bool:
    return bool(user.has_permission(ADMIN_PERMISSION))


async def _require_visible(
    db: AsyncSession, slug: str, user: Any, *, for_admin_bypass: bool = False
) -> Challenge:
    """Load a challenge the caller may interact with as a player."""
    challenge = await challenges.require_challenge(db, slug)
    if challenge.state != "visible" and not (_is_admin(user) and for_admin_bypass):
        raise AuthError("unknown challenge", 404)
    return challenge


def public_challenge(
    challenge: Challenge,
    *,
    include_state: bool,
    points: int,
    solve_count: int,
    solved_by_me: bool | None = None,
) -> dict[str, object]:
    view: dict[str, object] = {
        "slug": challenge.slug,
        "name": challenge.name,
        "category": challenge.category,
        "difficulty": challenge.difficulty,
        "scoring": challenge.scoring,
        "points": points,
        "solve_count": solve_count,
    }
    if include_state:
        view["state"] = challenge.state
    if solved_by_me is not None:
        view["solved_by_me"] = solved_by_me
    return view


def admin_decay_view(challenge: Challenge) -> dict[str, int] | None:
    decay = challenge.dynamic_decay
    if decay is None:
        return None
    return {
        "initial": int(decay["initial"]),
        "minimum": int(decay["minimum"]),
        "solves_to_floor": int(decay["solves_to_floor"]),
    }


# --- Player endpoints -----------------------------------------------------------


@router.get("")
async def list_challenges(user: CurrentUser, db: DbSession) -> list[dict[str, object]]:
    admin = _is_admin(user)
    rows = (
        (await db.execute(select(Challenge).order_by(Challenge.difficulty, Challenge.slug)))
        .scalars()
        .all()
    )
    counts = await challenges.solve_counts(db)
    out: list[dict[str, object]] = []
    for challenge in rows:
        if challenge.state != "visible" and not admin:
            continue
        count = counts.get(challenge.id, 0)
        points = challenges.compute_points(
            scoring=challenge.scoring,
            points_base=challenge.points_base,
            dynamic_decay=challenge.dynamic_decay,
            solve_count_before=count,
        )
        out.append(
            public_challenge(challenge, include_state=admin, points=points, solve_count=count)
        )
    return out


@router.get("/{slug}")
async def get_challenge(slug: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    challenge = await _require_visible(db, slug, user, for_admin_bypass=True)
    admin = _is_admin(user)
    count = await challenges.get_solve_count(db, challenge.id)
    points = challenges.compute_points(
        scoring=challenge.scoring,
        points_base=challenge.points_base,
        dynamic_decay=challenge.dynamic_decay,
        solve_count_before=count,
    )
    view = public_challenge(
        challenge,
        include_state=admin,
        points=points,
        solve_count=count,
        solved_by_me=await challenges.has_solved(db, challenge.id, user.id),
    )
    view["description"] = challenge.description
    file_rows = (
        (await db.execute(select(ChallengeFile).where(ChallengeFile.challenge_id == challenge.id)))
        .scalars()
        .all()
    )
    view["files"] = [
        {"id": str(f.id), "filename": f.filename, "size": f.size, "sha256": f.sha256}
        for f in file_rows
    ]
    return view


@router.post("/{slug}/submit")
async def submit_flag(
    slug: str, payload: FlagIn, request: Request, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    allowed = await check_rate_limit(
        request,
        "challenge-submit",
        challenges.SUBMIT_RATE_LIMIT,
        challenges.SUBMIT_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise AuthError("too many submissions; slow down", 429)
    challenge = await _require_visible(db, slug, user, for_admin_bypass=True)
    result = await challenges.submit_flag(
        db, user_id=user.id, challenge=challenge, flag=payload.flag
    )
    return result


@router.get("/{slug}/files/{file_id}")
async def download_file(
    slug: str, file_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> FileResponse:
    challenge = await _require_visible(db, slug, user, for_admin_bypass=True)
    row = await challenges.get_file(db, challenge, file_id)
    path = challenges.safe_resolve(row.storage_path)
    if not path.is_file():
        raise AuthError("attachment missing from storage", 404)
    return FileResponse(path, filename=row.filename, media_type="application/octet-stream")


# --- Admin endpoints --------------------------------------------------------------


@router.post("", status_code=201)
async def create_challenge(
    payload: ChallengeCreateIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    if not _is_admin(user):
        raise AuthError("challenge administration requires content:manage", 403)
    decay = payload.dynamic_decay.model_dump() if payload.dynamic_decay is not None else None
    challenge = await challenges.create_challenge(
        db,
        author_id=user.id,
        slug=payload.slug,
        name=payload.name,
        category=payload.category,
        description=payload.description,
        difficulty=payload.difficulty,
        points_base=payload.points_base,
        scoring=payload.scoring,
        dynamic_decay=decay,
        flag=payload.flag,
        flag_case_sensitive=payload.flag_case_sensitive,
        state=payload.state,
    )
    count = await challenges.get_solve_count(db, challenge.id)
    view = public_challenge(
        challenge, include_state=True, points=challenge.points_base, solve_count=count
    )
    view["dynamic_decay"] = admin_decay_view(challenge)
    return view


@router.patch("/{slug}")
async def patch_challenge(
    slug: str, payload: ChallengePatchIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    if not _is_admin(user):
        raise AuthError("challenge administration requires content:manage", 403)
    challenge = await challenges.require_challenge(db, slug)
    decay = payload.dynamic_decay.model_dump() if payload.dynamic_decay is not None else None
    challenge = await challenges.update_challenge(
        db,
        challenge,
        name=payload.name,
        category=payload.category,
        description=payload.description,
        difficulty=payload.difficulty,
        points_base=payload.points_base,
        scoring=payload.scoring,
        dynamic_decay=decay,
        flag=payload.flag,
        flag_case_sensitive=payload.flag_case_sensitive,
        state=payload.state,
    )
    count = await challenges.get_solve_count(db, challenge.id)
    points = challenges.compute_points(
        scoring=challenge.scoring,
        points_base=challenge.points_base,
        dynamic_decay=challenge.dynamic_decay,
        solve_count_before=count,
    )
    view = public_challenge(challenge, include_state=True, points=points, solve_count=count)
    view["dynamic_decay"] = admin_decay_view(challenge)
    return view


@router.post("/{slug}/files", status_code=201)
async def upload_file(
    slug: str,
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(description="challenge attachment")],
) -> dict[str, object]:
    if not _is_admin(user):
        raise AuthError("challenge administration requires content:manage", 403)
    challenge = await challenges.require_challenge(db, slug)
    assert file.file is not None
    content = await file.read()
    row = await challenges.add_file(db, challenge, filename=file.filename or "", content=content)
    return {
        "id": str(row.id),
        "filename": row.filename,
        "size": row.size,
        "sha256": row.sha256,
    }
