"""Bridge to the content SDK: flag derivation and bundle lookup.

The API never imports solver code at runtime; it reads manifests and
reuses the SDK's pure helpers.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from openrange.content.solver import derive_flag  # re-exported for the labs service

__all__ = ["bundles_root", "derive_flag", "find_bundle_dir"]

_BUNDLES_ENV = "OPENRANGE_CONTENT_ROOT"


def bundles_root() -> Path:
    return Path(__import__("os").environ.get(_BUNDLES_ENV, "content/rooms"))


def find_bundle_dir(slug: str) -> Path | None:
    candidate = bundles_root() / slug
    if (candidate / "room.yaml").exists():
        return candidate
    return None


def flag_fingerprint(flag: str) -> str:
    """Stable non-reversible id for logging/audit without exposing flags."""
    return hashlib.sha256(flag.encode()).hexdigest()[:12]
