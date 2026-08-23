"""Content lints: schema-adjacent rules with human explanations.

A finding is (severity, rule, message). `lint` fails on any error.
The style rule enforces the project's writing standards (see unslop):
no puffery, no em dashes, no decorative emoji in prose.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from openrange.content.loader import load_bundle
from openrange.content.models import PathBundle, RoomBundle

Severity = str  # "error" | "warning"


@dataclass(slots=True)
class Finding:
    severity: Severity
    rule: str
    message: str


LintFn = Callable[[Path], list[Finding]]

_EM_DASH = re.compile(r"\u2014|\u2013")
_EMOJI = re.compile(
    "[\U0001f300-\U0001f9ff\U00002600-\U000027bf\U0001fa00-\U0001faff]", flags=re.UNICODE
)
_SLOP_PHRASES = [
    "delve",
    "tapestry",
    "testament to",
    "pivotal moment",
    "evolving landscape",
    "in today's digital",
    "cyber landscape is constantly",
    "it is important to note",
    "unlock the world of",
    "welcome to the exciting",
]
_BRANDS = ["hackthebox", "hack the box", "tryhackme", "try hack me"]


def _prose_sources(bundle_dir: Path) -> list[Path]:
    out: list[Path] = []
    lesson = bundle_dir / "lesson"
    if lesson.is_dir():
        out.extend(sorted(lesson.glob("**/*.md")))
    readme = bundle_dir / "README.md"
    if readme.exists():
        out.append(readme)
    return out


def lint_room(bundle_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    manifest = bundle_dir / "room.yaml"

    try:
        bundle = load_bundle(manifest)
        if not isinstance(bundle, RoomBundle):
            return [Finding("error", "schema", f"expected kind Room, got {type(bundle).__name__}")]
    except Exception as exc:
        return [Finding("error", "schema", str(exc))]

    spec = bundle.spec
    meta = bundle.metadata

    # Points consistency: metadata.points is the room total.
    task_points = sum(t.points for t in spec.tasks)
    if task_points != meta.points:
        findings.append(
            Finding(
                "error",
                "points-total",
                f"metadata.points ({meta.points}) != sum of task points ({task_points})",
            )
        )

    # Hint tiers must be ordered cheapest-first and cost points.
    for task in spec.tasks:
        costs = [h.cost for h in task.hints]
        if costs != sorted(costs):
            findings.append(
                Finding("error", "hint-order", f"task {task.id}: hints must ascend by cost")
            )

    # Solver presence.
    solver = bundle_dir / "solver" / "solver.py"
    if not solver.exists():
        findings.append(Finding("error", "solver", "solver/solver.py missing"))
    else:
        text = solver.read_text()
        if "def solve(" not in text:
            findings.append(Finding("error", "solver", "solver.py must define solve(ctx)"))
        if "FLAG{" in text and "expected_flags" not in text:
            findings.append(
                Finding(
                    "warning",
                    "solver-static-flag",
                    "solver appears to hardcode a FLAG literal; use ctx.expected_flags instead",
                )
            )

    # Target build context exists.
    target_dir = bundle_dir / spec.target.build_context
    if not (target_dir / "Dockerfile").exists():
        findings.append(
            Finding("error", "target", f"{spec.target.build_context}/Dockerfile missing")
        )

    # Safety declaration must be explicit.
    if not spec.safety.simulated_only or not spec.safety.no_real_malware:
        findings.append(
            Finding(
                "error",
                "safety",
                "bundles must declare simulated_only and no_real_malware as true",
            )
        )

    # Elevated targets need a written justification for reviewers.
    if spec.target.privilege_profile == "elevated" and len(spec.safety.reviewer_notes) < 40:
        findings.append(
            Finding(
                "error",
                "privilege-profile",
                "privilege_profile elevated requires a safety.reviewer_notes "
                "justification of at least 40 characters",
            )
        )

    # Prose quality gates.
    for md in _prose_sources(bundle_dir):
        content = md.read_text()
        rel = md.relative_to(bundle_dir)
        if _EM_DASH.search(content):
            findings.append(
                Finding("warning", "style-dash", f"{rel}: use commas or periods, not dashes")
            )
        if _EMOJI.search(content):
            findings.append(Finding("warning", "style-emoji", f"{rel}: remove decorative emoji"))
        lowered = content.lower()
        for phrase in _SLOP_PHRASES:
            if phrase in lowered:
                findings.append(Finding("warning", "style-slop", f"{rel}: rewrite '{phrase}'"))
        for brand in _BRANDS:
            if brand in lowered:
                findings.append(
                    Finding("error", "branding", f"{rel}: competitor brand reference '{brand}'")
                )
        for i, line in enumerate(content.splitlines(), start=1):
            if re.search(r"!\[[^\]]*\]\(", line) and re.search(r"!\[\s*\]\(", line):
                findings.append(
                    Finding("error", "a11y-image-alt", f"{rel}:{i}: images need alt text")
                )

    # Lesson directory required for guided rooms.
    if spec.type == "guided" and not (bundle_dir / "lesson").is_dir():
        findings.append(Finding("error", "guided-lesson", "guided rooms need a lesson/ directory"))

    return findings


def lint_path(bundle_dir: Path) -> list[Finding]:
    try:
        bundle = load_bundle(bundle_dir / "path.yaml")
    except Exception as exc:
        return [Finding("error", "schema", str(exc))]
    if not isinstance(bundle, PathBundle):
        return [Finding("error", "schema", f"expected kind Path, got {type(bundle).__name__}")]
    findings: list[Finding] = []
    rooms_root = bundle_dir.parents[1] / "rooms"
    missing = [m.slug for m in bundle.spec.modules if not (rooms_root / m.slug).is_dir()]
    for slug in missing:
        findings.append(Finding("error", "module-ref", f"path references unknown module {slug}"))
    return findings
