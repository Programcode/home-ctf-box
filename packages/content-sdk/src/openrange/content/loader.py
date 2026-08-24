"""Bundle loading with actionable errors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from openrange.content.models import ModuleBundle, PathBundle, RoomBundle, Section, SectionBlock
from pydantic import ValidationError


@dataclass(slots=True)
class LoadError(Exception):
    path: Path
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def load_yaml(path: Path) -> dict[str, object]:
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise LoadError(path, f"invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise LoadError(path, "top level must be a mapping")
    return raw


def load_bundle(path: Path) -> RoomBundle | ModuleBundle | PathBundle:
    raw = load_yaml(path)
    kind = str(raw.get("kind", ""))
    models = {"Room": RoomBundle, "Module": ModuleBundle, "Path": PathBundle}
    model = models.get(kind)
    if model is None:
        raise LoadError(path, f"unknown or missing kind: {kind!r}")
    try:
        bundle = model.model_validate(raw)
        assert isinstance(bundle, (RoomBundle, ModuleBundle, PathBundle))
        return bundle
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first.get("loc", []))
        raise LoadError(path, f"{loc}: {first['msg']}") from exc
    except AssertionError as exc:  # pragma: no cover - defensive
        raise LoadError(path, "model produced unexpected bundle type") from exc


def load_room(room_dir: Path) -> tuple[RoomBundle, Path]:
    manifest = room_dir / "room.yaml"
    if not manifest.exists():
        raise LoadError(manifest, "room.yaml missing")
    bundle = load_bundle(manifest)
    if not isinstance(bundle, RoomBundle):
        raise LoadError(manifest, f"manifest declares kind {type(bundle).__name__}, expected Room")
    return bundle, manifest


# --- Per-locale section overrides (i18n) ---

TRANSLATABLE_BLOCK_TYPES = frozenset({"prose", "callout"})
OVERRIDE_FILENAME = "sections.{locale}.yaml"
_LOCALE_FILE_RE = re.compile(r"^sections\.([a-z]{2,8}(?:-[A-Za-z0-9]+)*)\.ya?ml$")


@dataclass(slots=True)
class SectionOverride:
    """Translated title plus translatable blocks for one section id."""

    section_id: str
    title: str
    blocks: list[SectionBlock]


@dataclass(slots=True)
class LocaleOverrides:
    """Parsed sections.<locale>.yaml for one module."""

    locale: str
    path: Path
    sections: dict[str, SectionOverride] = field(default_factory=dict)


def available_locales(module_dir: Path) -> list[str]:
    """Locales with override files under module_dir; English is always there."""
    found = {"en"}
    if module_dir.is_dir():
        for child in sorted(module_dir.iterdir()):
            match = _LOCALE_FILE_RE.match(child.name)
            if match is not None:
                found.add(match.group(1).lower())
    return sorted(found)


def load_locale_overrides(module_dir: Path, locale: str) -> LocaleOverrides | None:
    """Load sections.<locale>.yaml from a module directory, or None."""
    path = module_dir / OVERRIDE_FILENAME.format(locale=locale)
    if not path.exists():
        return None
    raw = load_yaml(path)
    unknown = set(raw) - {"locale", "sections"}
    if unknown:
        raise LoadError(path, f"unknown keys: {sorted(str(k) for k in unknown)}")
    declared = raw.get("locale")
    if declared != locale:
        raise LoadError(path, f"'locale' must be {locale!r}, got {declared!r}")
    entries = raw.get("sections")
    if not isinstance(entries, list):
        raise LoadError(path, "'sections' must be a list")
    overrides = LocaleOverrides(locale=locale, path=path)
    for entry in entries:
        if not isinstance(entry, dict):
            raise LoadError(path, "every override section must be a mapping")
        try:
            parsed = Section.model_validate(entry)
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = ".".join(str(p) for p in first.get("loc", []))
            raise LoadError(path, f"{loc}: {first['msg']}") from exc
        if parsed.id in overrides.sections:
            raise LoadError(path, f"duplicate section id {parsed.id!r}")
        bad = [b.type for b in parsed.blocks if b.type not in TRANSLATABLE_BLOCK_TYPES]
        if bad:
            raise LoadError(
                path,
                f"section {parsed.id!r}: non-translatable block types {bad}; "
                "code and quiz blocks stay English-owned",
            )
        overrides.sections[parsed.id] = SectionOverride(
            section_id=parsed.id, title=parsed.title, blocks=list(parsed.blocks)
        )
    return overrides


def apply_section_overrides(bundle: ModuleBundle, overrides: LocaleOverrides) -> ModuleBundle:
    """Return a copy of the bundle with translated prose swapped in.

    For each overridden section id the translated blocks replace the
    original prose/callout slots in document order; code and quiz blocks
    are kept from the English source so structure stays intact.
    """
    replaced: list[Section] = []
    for section in bundle.spec.sections:
        override = overrides.sections.get(section.id)
        if override is None:
            replaced.append(section)
            continue
        slots = [i for i, b in enumerate(section.blocks) if b.type in TRANSLATABLE_BLOCK_TYPES]
        if len(slots) != len(override.blocks):
            raise LoadError(
                overrides.path,
                f"section {section.id!r}: {len(override.blocks)} translatable override "
                f"blocks do not match {len(slots)} prose/callout blocks in source",
            )
        blocks = list(section.blocks)
        for index, block in zip(slots, override.blocks, strict=True):
            blocks[index] = block
        replaced.append(Section(id=section.id, title=override.title, blocks=blocks))
    spec = bundle.spec.model_copy(update={"sections": replaced})
    return bundle.model_copy(update={"spec": spec})
