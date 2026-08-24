"""Content Studio domain logic (plan Phase 10).

Workspace model: every draft owns an isolated directory under
OPENRANGE_STUDIO_CONTENT_ROOT (default ./content-staging) laid out as
<staging>/<draft-id>/<kind>s/<slug>/. Authors write files through the
API; validation runs the content-sdk loader and linters against that
directory on demand.

Publishing copies a validated bundle into the real content tree
(OPENRANGE_CONTENT_DIR, default ./content) with an atomic directory
swap: the new bundle is staged next to its destination, the old bundle
moves aside with os.replace, then the linter runs against the real
target. Any lint failure rolls the original bundle back untouched.
"""

from __future__ import annotations

import io
import os
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openrange.api.auth.service import AuthError
from openrange.api.studio.models import ContentDraft, DraftReview, PublishEvent
from openrange.content.linting import Finding, lint_path, lint_room
from openrange.content.loader import LoadError, load_bundle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

STAGING_ROOT_ENV = "OPENRANGE_STUDIO_CONTENT_ROOT"
DEFAULT_STAGING_ROOT = "./content-staging"
CONTENT_DIR_ENV = "OPENRANGE_CONTENT_DIR"
DEFAULT_CONTENT_DIR = "./content"

KIND_DIRS = {"room": "rooms", "module": "modules", "path": "paths"}
SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{2,63}$"

MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_ZIP_MEMBERS = 2000
MAX_ZIP_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024
MAX_FILE_BYTES = 10 * 1024 * 1024

MANIFEST_NAMES = {"room": "room.yaml", "module": "module.yaml", "path": "path.yaml"}


@dataclass(slots=True)
class StudioFile:
    path: str
    size: int


def staging_root() -> Path:
    return Path(os.environ.get(STAGING_ROOT_ENV, DEFAULT_STAGING_ROOT))


def real_content_root() -> Path:
    return Path(os.environ.get(CONTENT_DIR_ENV, DEFAULT_CONTENT_DIR))


def draft_workspace(draft: ContentDraft) -> Path:
    return Path(draft.content_root)


def draft_bundle_dir(draft: ContentDraft) -> Path:
    return draft_workspace(draft) / KIND_DIRS[draft.kind] / draft.slug


def safe_join(root: Path, relative: str) -> Path:
    """Resolve *relative* under *root*, rejecting escapes of any kind."""
    if not relative or relative.strip() == "":
        raise AuthError("file path must not be empty", 422)
    if "\x00" in relative:
        raise AuthError("file path contains invalid characters", 422)
    candidate = Path(relative)
    if candidate.is_absolute() or relative.startswith("\\") or "\\" in relative:
        raise AuthError("file path separators must use forward slashes", 422)
    if ":" in relative.split("/")[0]:
        raise AuthError("windows-style file paths are not allowed", 422)
    if ".." in candidate.parts:
        raise AuthError("file path traversal is not allowed", 422)
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise AuthError("file path escapes the draft workspace", 422)
    return resolved


def create_workspace(draft_id: uuid.UUID, kind: str, slug: str) -> str:
    root = staging_root() / str(draft_id) / KIND_DIRS[kind] / slug
    root.mkdir(parents=True, exist_ok=True)
    # content_root points at the draft's own dir so kind/slug renames
    # cannot be smuggled through stored paths.
    return str((staging_root() / str(draft_id)).resolve())


def remove_workspace(draft: ContentDraft) -> None:
    """Best-effort removal, refusing to touch dirs outside staging."""
    root = draft_workspace(draft).resolve()
    if root.is_relative_to(staging_root().resolve()):
        shutil.rmtree(root, ignore_errors=True)


def write_file(draft: ContentDraft, relative: str, content: bytes) -> StudioFile:
    if len(content) > MAX_FILE_BYTES:
        raise AuthError("file exceeds size limit", 413)
    target = safe_join(draft_workspace(draft), relative)
    if target.is_dir():
        raise AuthError("path is a directory", 409)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return StudioFile(path=relative, size=len(content))


def read_file(draft: ContentDraft, relative: str) -> bytes:
    target = safe_join(draft_workspace(draft), relative)
    if not target.is_file():
        raise AuthError("file not found in draft", 404)
    if target.is_symlink():
        raise AuthError("symlinked files cannot be read", 422)
    return target.read_bytes()


def list_files(draft: ContentDraft) -> list[StudioFile]:
    root = draft_workspace(draft)
    if not root.is_dir():
        return []
    files: list[StudioFile] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            continue
        if path.is_file():
            files.append(
                StudioFile(path=path.relative_to(root).as_posix(), size=path.stat().st_size)
            )
    return files


def extract_bundle(draft: ContentDraft, archive: bytes) -> list[str]:
    """Extract a zip into the draft workspace, zip-slip guarded."""
    if len(archive) > MAX_ZIP_BYTES:
        raise AuthError("bundle exceeds size limit", 413)
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            members = zf.infolist()
            if len(members) > MAX_ZIP_MEMBERS:
                raise AuthError("bundle has too many entries", 413)
            total = sum(info.file_size for info in members)
            if total > MAX_ZIP_TOTAL_UNCOMPRESSED:
                raise AuthError("bundle uncompressed size exceeds limit", 413)
            written: list[str] = []
            for info in members:
                name = info.filename
                mode = info.external_attr >> 16
                if mode & 0o170000 == 0o120000:  # symlink member
                    raise AuthError(f"bundle entry {name!r} is a symlink", 422)
                if name.startswith("/") or "\\" in name or ":" in name.split("/")[0]:
                    raise AuthError(f"bundle entry {name!r} has an unsafe path", 422)
                parts = Path(name).parts
                if ".." in parts:
                    raise AuthError(f"bundle entry {name!r} escapes the draft", 422)
                target = safe_join(draft_workspace(draft), name)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                written.append(name)
            return written
    except zipfile.BadZipFile as exc:
        raise AuthError("uploaded file is not a valid zip archive", 422) from exc


def _findings_to_dicts(findings: list[Finding]) -> list[dict[str, str]]:
    return [{"severity": f.severity, "rule": f.rule, "message": f.message} for f in findings]


def validate_draft(draft: ContentDraft) -> dict[str, Any]:
    """Run loader + linter for the draft's kind against its bundle dir."""
    bundle_dir = draft_bundle_dir(draft)
    findings: list[Finding] = []
    manifest = bundle_dir / MANIFEST_NAMES[draft.kind]
    try:
        load_bundle(manifest)
    except LoadError as exc:
        findings.append(Finding("error", "schema", str(exc)))
    except OSError as exc:
        findings.append(Finding("error", "schema", f"{manifest}: {exc}"))

    if draft.kind == "room" and manifest.exists():
        findings.extend(lint_room(bundle_dir))
    elif draft.kind == "path" and manifest.exists():
        findings.extend(lint_path(bundle_dir))

    errors = [f for f in findings if f.severity == "error"]
    return {"ok": not errors, "findings": _findings_to_dicts(findings)}


def lint_published_bundle(kind: str, bundle_dir: Path) -> list[Finding]:
    """Lint hook used after publishing lands files in the real tree.

    Module-level indirection so tests can inject failures here.
    """
    if kind == "room":
        return lint_room(bundle_dir)
    if kind == "path":
        return lint_path(bundle_dir)
    try:
        load_bundle(bundle_dir / MANIFEST_NAMES[kind])
    except Exception as exc:
        return [Finding("error", "schema", str(exc))]
    return []


async def record_event(
    db: AsyncSession,
    draft: ContentDraft,
    event: str,
    actor_id: uuid.UUID | None,
    detail: dict[str, Any] | None = None,
) -> PublishEvent:
    row = PublishEvent(draft_id=draft.id, event=event, actor_id=actor_id, detail=detail or {})
    db.add(row)
    await db.flush()
    return row


async def has_approved_review(db: AsyncSession, draft_id: uuid.UUID) -> bool:
    review = await db.execute(
        select(DraftReview.id).where(
            DraftReview.draft_id == draft_id, DraftReview.state == "approved"
        )
    )
    return review.first() is not None


async def publish_draft(
    db: AsyncSession, draft: ContentDraft, actor_id: uuid.UUID | None
) -> dict[str, Any]:
    """Copy the validated bundle into the real tree atomically.

    Sequence per bundle: stage a copy beside the destination, move any
    existing bundle aside with os.replace, swap the new one in, then
    lint the real target. Lint failure restores the original bytes.
    """
    source = draft_bundle_dir(draft)
    if not source.is_dir():
        raise AuthError("draft has no bundle to publish", 409)

    kinds_dir = real_content_root() / KIND_DIRS[draft.kind]
    destination = kinds_dir / draft.slug
    kinds_dir.mkdir(parents=True, exist_ok=True)

    token = uuid.uuid4().hex
    staged = kinds_dir / f".{draft.slug}.new-{token}"
    backup = kinds_dir / f".{draft.slug}.old-{token}"

    shutil.copytree(source, staged)
    had_previous = False
    if destination.exists():
        os.replace(destination, backup)
        had_previous = True
    try:
        os.replace(staged, destination)
    except OSError:
        if had_previous:
            os.replace(backup, destination)
            shutil.rmtree(backup, ignore_errors=True)
        else:
            shutil.rmtree(staged, ignore_errors=True)
        raise

    findings = lint_published_bundle(draft.kind, destination)
    if any(f.severity == "error" for f in findings):
        shutil.rmtree(destination)
        if had_previous:
            os.replace(backup, destination)
        raise AuthError(
            "published bundle failed lint on the real content tree; rolled back",
            409,
        )
    if had_previous:
        shutil.rmtree(backup, ignore_errors=True)

    detail = {
        "target": str(destination),
        "findings": [f.message for f in findings if f.severity == "warning"],
    }
    await record_event(db, draft, "published", actor_id, detail)
    return {"published": True, "target": str(destination), **detail}
