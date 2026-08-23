"""Solver protocol and validators.

A solver is `solver/solver.py` exposing:

    def solve(ctx: SolveContext) -> SolveResult

It must complete every task through the intended path using only the
declared scope, and derive flags from `ctx.expected_flags` rather than
hardcoding them.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openrange.content.models import Validator

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
_REGEX_TIMEOUT_SECONDS = 0.5
_REGEX_MAX_LENGTH = 4096
_POOL = ThreadPoolExecutor(max_workers=2)


@dataclass(slots=True)
class SolveContext:
    base_urls: dict[str, str]  # service name -> base url (e.g. {"target": "http://..."})
    expected_flags: dict[str, str]  # task id -> expected flag for this run
    timeout_seconds: float = 60.0

    def url(self, name: str = "target") -> str:
        return self.base_urls[name]


@dataclass(slots=True)
class TaskResult:
    task_id: str
    ok: bool
    captured: str | None = None
    detail: str | None = None


@dataclass(slots=True)
class SolveResult:
    results: list[TaskResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.results) and all(r.ok for r in self.results)


FLAG_RE = re.compile(r"FLAG\{[A-Z2-7=+]{16,}\}")


def derive_flag(
    master_key: bytes,
    *,
    instance_id: str,
    content_slug: str,
    task_id: str,
) -> str:
    """The single canonical per-session flag derivation (ADR 0007)."""
    material = f"{instance_id}|{content_slug}|{task_id}".encode()
    digest = hmac.new(master_key, material, hashlib.sha256).digest()
    encoded = "".join(_ALPHABET[b % 32] for b in digest[:20])
    return f"FLAG{{{encoded}}}"


class ValidatorError(ValueError):
    pass


def _digest_equal(left: str, right: str) -> bool:
    """compare_digest over UTF-8 bytes: safe for any submission text."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def _regex_fullmatch_with_timeout(pattern: re.Pattern[str], submitted: str) -> bool:
    future = _POOL.submit(pattern.fullmatch, submitted)
    try:
        return future.result(timeout=_REGEX_TIMEOUT_SECONDS) is not None
    except FutureTimeout as exc:
        future.cancel()
        raise ValidatorError("regex validation timed out") from exc


def validate_answer(validator: Validator, submitted: str, expected_flag: str) -> bool:
    """Shared validator implementation; the API and harness both call it."""
    vtype = validator.type
    value = validator.value

    if vtype == "per_session_flag":
        return _digest_equal(submitted.strip(), expected_flag)
    if vtype == "exact":
        return value is not None and _digest_equal(submitted.strip(), str(value))
    if vtype == "normalized":
        if value is None:
            return False
        norm = re.sub(r"\s+", " ", submitted.strip().lower())
        target = re.sub(r"\s+", " ", str(value).strip().lower())
        return _digest_equal(norm, target)
    if vtype == "regex":
        if not value or len(submitted) > _REGEX_MAX_LENGTH:
            return False
        try:
            pattern = re.compile(str(value))
        except re.error as exc:
            raise ValidatorError("invalid validator regex") from exc
        return _regex_fullmatch_with_timeout(pattern, submitted)
    if vtype == "numeric_range":
        try:
            number = float(submitted.strip())
        except ValueError as exc:
            raise ValidatorError("answer is not numeric") from exc
        lo = validator.min
        hi = validator.max
        return (lo is None or number >= lo) and (hi is None or number <= hi)
    if vtype == "set":
        allowed = {s.strip().lower() for s in (validator.values or [])}
        want = {s.strip().lower() for s in submitted.split(",") if s.strip()}
        return want == allowed
    if vtype == "file_hash":
        digest = hashlib.sha256(submitted.encode("utf-8")).hexdigest()
        return value is not None and _digest_equal(digest, str(value))
    if vtype == "manual":
        # Manual-review answers never auto-pass.
        return False
    raise ValidatorError(f"unknown validator type {vtype!r}")


def find_flags(text: str) -> list[str]:
    """Extract FLAG{...} tokens matching the platform format."""
    return FLAG_RE.findall(text)
