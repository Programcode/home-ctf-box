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
import time
from collections.abc import Mapping
from dataclasses import dataclass, field


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
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    encoded = "".join(alphabet[b % 32] for b in digest[:20])
    return f"FLAG{{{encoded}}}"


class ValidatorError(ValueError):
    pass


def validate_answer(validator: object, submitted: str, expected_flag: str) -> bool:
    """Shared validator implementation; the API and harness both call it."""
    vtype = getattr(validator, "type", "")
    value = getattr(validator, "value", None)

    if vtype == "per_session_flag":
        return hmac.compare_digest(submitted.strip(), expected_flag)
    if vtype == "exact":
        return bool(value) and hmac.compare_digest(submitted.strip(), str(value))
    if vtype == "normalized":
        norm = re.sub(r"\s+", " ", submitted.strip().lower())
        target = re.sub(r"\s+", " ", str(value or "").strip().lower())
        return bool(value) and hmac.compare_digest(norm, target)
    if vtype == "regex":
        pattern = re.compile(str(value))
        deadline = time.monotonic() + 0.25
        match = pattern.fullmatch(submitted)
        if time.monotonic() > deadline:
            raise ValidatorError("regex validation timed out")
        return match is not None
    if vtype == "numeric_range":
        try:
            number = float(submitted.strip())
        except ValueError as exc:
            raise ValidatorError("answer is not numeric") from exc
        lo = getattr(validator, "min", None)
        hi = getattr(validator, "max", None)
        return (lo is None or number >= lo) and (hi is None or number <= hi)
    if vtype == "set":
        allowed = set(getattr(validator, "values", None) or [])
        want = {s.strip().lower() for s in submitted.split(",") if s.strip()}
        return want == allowed
    if vtype == "file_hash":
        digest = hashlib.sha256(submitted.encode()).hexdigest()
        return bool(value) and hmac.compare_digest(digest, str(value))
    if vtype == "manual":
        # Manual-review answers never auto-pass.
        return False
    raise ValidatorError(f"unknown validator type {vtype!r}")


def find_flags(text: str) -> list[str]:
    """Extract FLAG{...} tokens matching the platform format."""
    return FLAG_RE.findall(text)


def first_url(context: SolveContext, *names: str) -> Mapping[str, str]:
    return context.base_urls
