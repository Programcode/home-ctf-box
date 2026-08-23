"""Curriculum content service.

Loads PathBundle/ModuleBundle (and RoomBundle for hints) from the
content directory declared by CONTENT_DIR (default ./content) through
the content-sdk loader, caching parsed bundles with mtime invalidation
so edits on disk show up without a restart.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from openrange.content.loader import load_bundle, load_room
from openrange.content.models import ModuleBundle, PathBundle, RoomBundle, Section

CONTENT_DIR_ENV = "CONTENT_DIR"
DEFAULT_CONTENT_DIR = "./content"

_cache: dict[str, tuple[int, object]] = {}
_lock = threading.Lock()


def content_root() -> Path:
    return Path(os.environ.get(CONTENT_DIR_ENV, DEFAULT_CONTENT_DIR))


def clear_caches() -> None:
    with _lock:
        _cache.clear()


def _cached(path: Path, parse: Callable[[], object]) -> tuple[int, object]:
    key = str(path)
    stat_mtime = path.stat().st_mtime_ns
    with _lock:
        hit = _cache.get(key)
        if hit is not None and hit[0] == stat_mtime:
            return hit
        value = (stat_mtime, parse())
        _cache[key] = value
        return value


def _manifests(kind_dir: str) -> list[Path]:
    """Manifest files under <root>/<kind_dir>/ as either <kind>/<slug>.yaml
    directories (<dir>/<kind>.yaml) or flat <slug>.yaml files."""
    singular = kind_dir[:-1]
    root = content_root() / kind_dir
    found: list[Path] = []
    if not root.is_dir():
        return found
    for child in sorted(root.iterdir()):
        if child.is_dir():
            for name in (f"{singular}.yaml", f"{singular}.yml"):
                candidate = child / name
                if candidate.exists():
                    found.append(candidate)
                    break
        elif child.suffix in {".yaml", ".yml"}:
            found.append(child)
    return found


def _load_curriculum(path: Path) -> ModuleBundle | PathBundle:
    def parse() -> ModuleBundle | PathBundle:
        bundle = load_bundle(path)
        if not isinstance(bundle, (ModuleBundle, PathBundle)):
            raise RuntimeError(f"{path}: expected a Module or Path bundle")
        return bundle

    _, value = _cached(path, parse)
    assert isinstance(value, (ModuleBundle, PathBundle))
    return value


def list_module_bundles() -> dict[str, ModuleBundle]:
    modules: dict[str, ModuleBundle] = {}
    for manifest in _manifests("modules"):
        bundle = _load_curriculum(manifest)
        if isinstance(bundle, ModuleBundle):
            modules[bundle.metadata.slug] = bundle
    return modules


def get_module_bundle(slug: str) -> ModuleBundle | None:
    return list_module_bundles().get(slug)


def list_path_bundles() -> list[PathBundle]:
    paths: list[PathBundle] = []
    for manifest in _manifests("paths"):
        bundle = _load_curriculum(manifest)
        if isinstance(bundle, PathBundle):
            paths.append(bundle)
    paths.sort(key=lambda b: b.metadata.slug)
    return paths


def get_path_bundle(slug: str) -> PathBundle | None:
    for bundle in list_path_bundles():
        if bundle.metadata.slug == slug:
            return bundle
    return None


def get_room_bundle(slug: str) -> RoomBundle | None:
    manifest = content_root() / "rooms" / slug / "room.yaml"
    if not manifest.exists():
        return None

    def parse() -> RoomBundle:
        bundle, _manifest_path = load_room(manifest.parent)
        return bundle

    _, value = _cached(manifest, parse)
    assert isinstance(value, RoomBundle)
    return value


@dataclass(slots=True, frozen=True)
class SectionRef:
    """A section positioned inside one path's ordered traversal."""

    module_slug: str
    module_title: str
    section_id: str
    title: str
    order_index: int
    optional_branch: bool
    prerequisites: tuple[tuple[str, str], ...]


@dataclass(slots=True, frozen=True)
class PathOutline:
    path: PathBundle
    sections: list[SectionRef] = field(default_factory=list)
    required_modules: tuple[str, ...] = ()
    optional_modules: tuple[str, ...] = ()

    def section(self, module_slug: str, section_id: str) -> SectionRef | None:
        for ref in self.sections:
            if ref.module_slug == module_slug and ref.section_id == section_id:
                return ref
        return None


def path_outline(bundle: PathBundle) -> PathOutline:
    """Ordered sections with optional-branch flags and prerequisites.

    A required section's prerequisites are every required section that
    precedes it in the path's module order. Sections inside an
    optional-branch module never gate and are never gated.
    """
    sections: list[SectionRef] = []
    required_prefix: list[tuple[str, str]] = []
    required: list[str] = []
    optional: list[str] = []
    order = 0
    for ref in bundle.spec.modules:
        module = get_module_bundle(ref.slug)
        if module is None:
            raise RuntimeError(
                f"path {bundle.metadata.slug!r} references unknown module {ref.slug!r}"
            )
        if ref.optional_branch:
            optional.append(ref.slug)
        else:
            required.append(ref.slug)
        for section in module.spec.sections:
            prereqs: tuple[tuple[str, str], ...] = ()
            if not ref.optional_branch:
                prereqs = tuple(required_prefix)
                required_prefix.append((ref.slug, section.id))
            sections.append(
                SectionRef(
                    module_slug=ref.slug,
                    module_title=module.metadata.title,
                    section_id=section.id,
                    title=section.title,
                    order_index=order,
                    optional_branch=ref.optional_branch,
                    prerequisites=prereqs,
                )
            )
            order += 1
    return PathOutline(
        path=bundle,
        sections=sections,
        required_modules=tuple(required),
        optional_modules=tuple(optional),
    )


def find_quiz_section(section_id: str, module_slug: str | None) -> tuple[ModuleBundle, Section]:
    """Locate a quiz-bearing section across loaded modules."""
    matches: list[tuple[ModuleBundle, Section]] = []
    for slug, module in sorted(list_module_bundles().items()):
        if module_slug is not None and slug != module_slug:
            continue
        for section in module.spec.sections:
            if section.id == section_id and any(b.type == "quiz" for b in section.blocks):
                matches.append((module, section))
    if not matches:
        raise LookupError(f"no quiz section {section_id!r}")
    if len(matches) > 1:
        raise LookupError(f"section {section_id!r} is ambiguous; specify module_slug")
    return matches[0]
