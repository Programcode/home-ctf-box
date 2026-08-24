"""Localization primitives: locale resolution and protected-span validation.

English content is the source of truth. Translations ship as optional
override files (see loader.load_locale_overrides) and may only carry
translatable blocks. Anything that machines must read verbatim — fenced
code blocks, inline code, command lines, CLI flags, filesystem paths —
is a protected span: validate_translation proves a translation copied
every protected span from the source block unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher

DEFAULT_LOCALE = "en"

MODIFIED_SIMILARITY = 0.8

KIND_CODE_BLOCK = "code_block"
KIND_COMMAND_LINE = "command_line"
KIND_FLAG = "flag"
KIND_INLINE_CODE = "inline_code"
KIND_PATH = "path"

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
# Inline code may wrap across source lines (yaml block scalars fold long
# markdown), so backticks pair across newlines.
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_COMMAND_LINE_RE = re.compile(r"(?m)^[ \t]*\$[ \t](.+?)[ \t]*$", re.MULTILINE)
# One or two dashes then a letter: matches -v and --force, skips -5 and
# hyphenated words whose dash follows a word character (rwxr-x---, e-mail).
_FLAG_RE = re.compile(r"(?<![\w./-])(-{1,2}[A-Za-z][A-Za-z0-9-]*)")
# Absolute, ./relative and ~/home paths; the lookbehind keeps mid-word
# slashes (and/or, https://) from matching.
_PATH_RE = re.compile(r"(?<![\w.\-/~])((?:~|\.{1,2})?/(?:[\w.@%-]+/)*[\w.@%-]+)")


@dataclass(frozen=True, slots=True)
class ProtectedSpan:
    """A fragment that translations must copy verbatim."""

    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class Violation:
    """One protected span the translation dropped or altered."""

    kind: str
    span_kind: str
    expected: str
    detail: str


def resolve_locale(
    requested: str | None,
    available: Iterable[str],
    default: str = DEFAULT_LOCALE,
) -> str:
    """Pick the served locale: exact tag, then language fallback, then default.

    ``hu-HU`` resolves to ``hu`` when ``hu`` is available; anything
    unmatched falls back to ``default`` (English base content).
    """
    pool = {tag.lower() for tag in available}
    want = (requested or "").strip().lower() or default.lower()
    if want in pool:
        return want
    primary = want.split("-", 1)[0]
    if primary in pool:
        return primary
    return default


def extract_protected_spans(text: str) -> list[ProtectedSpan]:
    """Collect protected spans from a markdown block in a stable order."""
    spans: list[ProtectedSpan] = []
    parts: list[str] = []
    cursor = 0
    for match in _FENCE_RE.finditer(text):
        parts.append(text[cursor : match.start()])
        cursor = match.end()
        spans.append(ProtectedSpan(KIND_CODE_BLOCK, match.group(1)))
    parts.append(text[cursor:])
    remainder = "".join(parts)

    for pattern, kind in (
        (_COMMAND_LINE_RE, KIND_COMMAND_LINE),
        (_INLINE_CODE_RE, KIND_INLINE_CODE),
        (_FLAG_RE, KIND_FLAG),
        (_PATH_RE, KIND_PATH),
    ):
        spans.extend(ProtectedSpan(kind, m.group(1)) for m in pattern.finditer(remainder))
    return spans


def validate_translation(original_block: str, translated_block: str) -> list[Violation]:
    """Compare a translated markdown block against its English source.

    Every protected span extracted from the original must appear verbatim
    in the translation. Inline code is compared whitespace-insensitively
    because source wrapping inside backticks is formatting, not content;
    fenced blocks, command lines, flags, and paths must match exactly. A
    near-identical counterpart reports ``modified``; a vanished span
    reports ``missing``.
    """
    violations: list[Violation] = []
    translated_spans = extract_protected_spans(translated_block)
    normalized_haystack = " ".join(translated_block.split())
    for span in extract_protected_spans(original_block):
        if span.kind == KIND_INLINE_CODE:
            found = " ".join(span.value.split()) in normalized_haystack
        else:
            found = span.value in translated_block
        if found:
            continue
        candidates = [s.value for s in translated_spans if s.kind == span.kind]
        kind, detail = _classify(span.value, candidates)
        violations.append(Violation(kind, span.kind, span.value, detail))
    return violations


def _classify(expected: str, candidates: list[str]) -> tuple[str, str]:
    normalized = " ".join(expected.split())
    for candidate in candidates:
        if " ".join(candidate.split()) == normalized:
            return "modified", "whitespace-only change"
    best_ratio = 0.0
    best_value = ""
    for candidate in candidates:
        ratio = SequenceMatcher(None, expected, candidate).ratio()
        if ratio > best_ratio:
            best_ratio, best_value = ratio, candidate
    if best_ratio >= MODIFIED_SIMILARITY:
        return "modified", f"closest match {best_value!r} (similarity {best_ratio:.2f})"
    return "missing", "span not present verbatim in translation"
