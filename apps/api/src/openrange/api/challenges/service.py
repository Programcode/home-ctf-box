"""Jeopardy challenge domain logic.

Containerless challenges complement lab-backed rooms: players download
attachments, submit flags, and score from static or dynamically decaying
point tables. Scoring is computed AT solve time from the solve count
BEFORE the current solve, so earlier solvers always earn more.

Cross-module policy: this module writes only its own tables. Anti-spray
reporting calls the scoring service's ``record_signal`` through an
in-function import; no score events are emitted here (the leaderboard
integration stays a separate concern).
"""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from openrange.api.auth.service import AuthError
from openrange.api.challenges.models import (
    Challenge,
    ChallengeFile,
    ChallengeSolve,
    ChallengeSubmission,
)
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

CATEGORIES: tuple[str, ...] = ("web", "crypto", "pwn", "rev", "forensics", "misc", "osint")
STATES: tuple[str, ...] = ("hidden", "visible")
SCORING_MODES: tuple[str, ...] = ("static", "dynamic")

SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{2,63}$"

FILES_ROOT_ENV = "OPENRANGE_CHALLENGE_FILES_ROOT"
DEFAULT_FILES_ROOT = "./challenge-files"

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_FILES_PER_CHALLENGE = 20

SUBMIT_RATE_LIMIT = 60
SUBMIT_RATE_WINDOW_SECONDS = 60

# More than this many WRONG submissions inside the window records an
# answer_spray anti-cheat signal for human review.
SPRAY_THRESHOLD = 30
SPRAY_WINDOW = timedelta(seconds=60)

FIRST_BLOOD_BONUS_FRACTION = 0.10

MAX_FLAG_LENGTH = 256


def _now() -> datetime:
    return datetime.now(UTC)


# --- Pure scoring helpers ----------------------------------------------------


def normalize_flag(flag: str, *, case_sensitive: bool) -> str:
    """Comparison form: strip surrounding whitespace, lowercase unless the
    challenge opted into case sensitivity."""
    stripped = flag.strip()
    return stripped if case_sensitive else stripped.lower()


def flag_hash(flag: str, *, case_sensitive: bool) -> str:
    return hashlib.sha256(normalize_flag(flag, case_sensitive=case_sensitive).encode()).hexdigest()


def validate_decay(decay: dict[str, Any] | None) -> dict[str, int]:
    """Normalized {initial, minimum, solves_to_floor}; raises 422 when unusable."""
    if not isinstance(decay, dict):
        raise AuthError("dynamic challenges require dynamic_decay", 422)
    normalized: dict[str, int] = {}
    for key in ("initial", "minimum", "solves_to_floor"):
        value = decay.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise AuthError(f"dynamic_decay.{key} must be an integer", 422)
        if value < 1:
            raise AuthError(f"dynamic_decay.{key} must be positive", 422)
        normalized[key] = value
    if normalized["initial"] <= normalized["minimum"]:
        raise AuthError("dynamic_decay.initial must exceed dynamic_decay.minimum", 422)
    return normalized


def compute_points(
    *,
    scoring: str,
    points_base: int,
    dynamic_decay: dict[str, Any] | None,
    solve_count_before: int,
) -> int:
    """Points a solve earns given how many players solved BEFORE it.

    Dynamic: floor(initial - step * n) clamped at minimum, where
    step = (initial - minimum) / solves_to_floor. Static: points_base.
    """
    if scoring != "dynamic":
        return points_base
    decay = validate_decay(dynamic_decay)
    step = (decay["initial"] - decay["minimum"]) / decay["solves_to_floor"]
    raw = math.floor(decay["initial"] - step * solve_count_before)
    return max(decay["minimum"], raw)


def apply_first_blood(points: int, *, is_first_blood: bool) -> int:
    """One-time +10% flat bump for the first solver."""
    if not is_first_blood:
        return points
    return points + math.floor(points * FIRST_BLOOD_BONUS_FRACTION)


# --- Queries -----------------------------------------------------------------


async def get_by_slug(db: AsyncSession, slug: str) -> Challenge | None:
    return (await db.execute(select(Challenge).where(Challenge.slug == slug))).scalar_one_or_none()


async def require_challenge(db: AsyncSession, slug: str) -> Challenge:
    challenge = await get_by_slug(db, slug)
    if challenge is None:
        raise AuthError("unknown challenge", 404)
    return challenge


async def get_solve_count(db: AsyncSession, challenge_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(ChallengeSolve)
                .where(ChallengeSolve.challenge_id == challenge_id)
            )
        ).scalar_one()
    )


async def solve_counts(db: AsyncSession) -> dict[uuid.UUID, int]:
    rows = await db.execute(
        select(ChallengeSolve.challenge_id, func.count()).group_by(ChallengeSolve.challenge_id)
    )
    return {challenge_id: int(count) for challenge_id, count in rows.all()}


async def has_solved(db: AsyncSession, challenge_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return (
        await db.execute(
            select(ChallengeSolve.id).where(
                ChallengeSolve.challenge_id == challenge_id,
                ChallengeSolve.user_id == user_id,
            )
        )
    ).first() is not None


# --- Admin CRUD ----------------------------------------------------------------


async def create_challenge(
    db: AsyncSession,
    *,
    author_id: uuid.UUID,
    slug: str,
    name: str,
    category: str,
    description: str,
    difficulty: int,
    points_base: int,
    scoring: str,
    dynamic_decay: dict[str, Any] | None,
    flag: str,
    flag_case_sensitive: bool,
    state: str,
) -> Challenge:
    if await get_by_slug(db, slug) is not None:
        raise AuthError("challenge slug already taken", 409)
    decay = validate_decay(dynamic_decay) if scoring == "dynamic" else None
    challenge = Challenge(
        slug=slug,
        name=name,
        category=category,
        description=description,
        difficulty=difficulty,
        points_base=points_base,
        scoring=scoring,
        dynamic_decay=decay,
        flag_hash=flag_hash(flag, case_sensitive=flag_case_sensitive),
        flag_case_sensitive=flag_case_sensitive,
        state=state,
        author_id=author_id,
    )
    db.add(challenge)
    await db.flush()
    return challenge


async def update_challenge(
    db: AsyncSession,
    challenge: Challenge,
    *,
    name: str | None = None,
    category: str | None = None,
    description: str | None = None,
    difficulty: int | None = None,
    points_base: int | None = None,
    scoring: str | None = None,
    dynamic_decay: dict[str, Any] | None = None,
    flag: str | None = None,
    flag_case_sensitive: bool | None = None,
    state: str | None = None,
) -> Challenge:
    if name is not None:
        challenge.name = name
    if category is not None:
        challenge.category = category
    if description is not None:
        challenge.description = description
    if difficulty is not None:
        challenge.difficulty = difficulty
    if points_base is not None:
        challenge.points_base = points_base
    if scoring is not None:
        challenge.scoring = scoring
    # A patch without a decay payload keeps the stored decay table; a
    # scoring flip to dynamic therefore requires decay present already
    # or supplied in the same request.
    if dynamic_decay is not None:
        challenge.dynamic_decay = validate_decay(dynamic_decay)
    if scoring == "dynamic":
        validate_decay(challenge.dynamic_decay)
    if flag is not None:
        case_sensitive = (
            challenge.flag_case_sensitive if flag_case_sensitive is None else (flag_case_sensitive)
        )
        challenge.flag_hash = flag_hash(flag, case_sensitive=case_sensitive)
    if flag_case_sensitive is not None:
        challenge.flag_case_sensitive = flag_case_sensitive
    if state is not None:
        challenge.state = state
    await db.flush()
    return challenge


# --- Flag submission ------------------------------------------------------------


async def submit_flag(
    db: AsyncSession, *, user_id: uuid.UUID, challenge: Challenge, flag: str
) -> dict[str, Any]:
    """Verify one guess. Returns correctness, awarded points (only for the
    solving attempt), and whether the solve already existed.

    Idempotent: repeat solves never re-award or recompute points, and
    the UNIQUE(challenge, user) constraint closes double-award races.
    """
    existing = (
        await db.execute(
            select(ChallengeSolve.id).where(
                ChallengeSolve.challenge_id == challenge.id,
                ChallengeSolve.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {"correct": True, "already_solved": True, "points": None, "first_blood": False}

    normalized = normalize_flag(flag, case_sensitive=challenge.flag_case_sensitive)
    candidate = hashlib.sha256(normalized.encode()).hexdigest()
    correct = hmac.compare_digest(candidate, challenge.flag_hash)
    db.add(
        ChallengeSubmission(
            challenge_id=challenge.id,
            user_id=user_id,
            submission_norm=normalized[:2048],
            correct=correct,
        )
    )
    await db.flush()

    if not correct:
        await _maybe_record_spray(db, user_id=user_id, challenge=challenge)
        return {"correct": False, "already_solved": False, "points": None, "first_blood": False}

    count_before = await get_solve_count(db, challenge.id)
    base = compute_points(
        scoring=challenge.scoring,
        points_base=challenge.points_base,
        dynamic_decay=challenge.dynamic_decay,
        solve_count_before=count_before,
    )
    points = apply_first_blood(base, is_first_blood=count_before == 0)
    stmt = (
        pg_insert(ChallengeSolve)
        .values(challenge_id=challenge.id, user_id=user_id)
        .on_conflict_do_nothing(
            index_elements=[
                ChallengeSolve.__table__.c.challenge_id,
                ChallengeSolve.__table__.c.user_id,
            ]
        )
        .returning(ChallengeSolve.id)
    )
    inserted = (await db.execute(stmt)).scalar_one_or_none()
    await db.flush()
    if inserted is None:  # concurrent duplicate solve; nobody re-awards
        return {"correct": True, "already_solved": True, "points": None, "first_blood": False}
    return {
        "correct": True,
        "already_solved": False,
        "points": points,
        "first_blood": count_before == 0,
    }


async def _maybe_record_spray(
    db: AsyncSession, *, user_id: uuid.UUID, challenge: Challenge
) -> None:
    """Flag answer spraying into the shared anti-cheat review queue.

    The scoring import lives inside the function so this module can load
    in isolation (unit tests, tooling) even if the scoring package moves.
    """
    window_start = _now() - SPRAY_WINDOW
    wrong = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ChallengeSubmission)
                .where(
                    ChallengeSubmission.user_id == user_id,
                    ChallengeSubmission.correct.is_(False),
                    ChallengeSubmission.created_at >= window_start,
                )
            )
        ).scalar_one()
    )
    if wrong <= SPRAY_THRESHOLD:
        return
    from openrange.api.scoring.service import record_signal

    await record_signal(
        db,
        user_id=user_id,
        kind="answer_spray",
        details={
            "window_seconds": int(SPRAY_WINDOW.total_seconds()),
            "threshold": SPRAY_THRESHOLD,
            "observed": wrong,
            "challenge_slug": challenge.slug,
        },
    )


# --- Attachment storage -----------------------------------------------------------


def files_root() -> Path:
    return Path(os.environ.get(FILES_ROOT_ENV, DEFAULT_FILES_ROOT))


def safe_resolve(storage_path: str) -> Path:
    """Resolve a stored path under the files root, refusing any escape.

    Mirrors the orgs/studio path-guard: forward slashes only, no
    traversal segments, final containment check on resolved paths.
    """
    if not storage_path or "\x00" in storage_path:
        raise AuthError("invalid storage path", 422)
    candidate = Path(storage_path)
    if candidate.is_absolute() or "\\" in storage_path or ".." in candidate.parts:
        raise AuthError("invalid storage path", 422)
    root = files_root().resolve()
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise AuthError("storage path escapes the files root", 422)
    return resolved


def sanitize_filename(filename: str) -> str:
    """Client-supplied names are reduced to a bare basename."""
    base = os.path.basename(filename.replace("\\", "/")).strip()
    if base in ("", ".", ".."):
        raise AuthError("filename is required", 422)
    return base[:255]


async def add_file(
    db: AsyncSession, challenge: Challenge, *, filename: str, content: bytes
) -> ChallengeFile:
    if len(content) > MAX_FILE_BYTES:
        raise AuthError("file exceeds the 25MB size limit", 413)
    used = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ChallengeFile)
                .where(ChallengeFile.challenge_id == challenge.id)
            )
        ).scalar_one()
    )
    if used >= MAX_FILES_PER_CHALLENGE:
        raise AuthError(f"challenge already has {MAX_FILES_PER_CHALLENGE} files", 413)
    clean_name = sanitize_filename(filename)
    file_id = uuid.uuid4()
    relative = f"{challenge.id}/{file_id}"
    target = safe_resolve(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    row = ChallengeFile(
        id=file_id,
        challenge_id=challenge.id,
        filename=clean_name,
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        storage_path=relative,
    )
    db.add(row)
    await db.flush()
    return row


async def get_file(db: AsyncSession, challenge: Challenge, file_id: uuid.UUID) -> ChallengeFile:
    row = (
        await db.execute(
            select(ChallengeFile).where(
                ChallengeFile.id == file_id, ChallengeFile.challenge_id == challenge.id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise AuthError("attachment not found", 404)
    return row
