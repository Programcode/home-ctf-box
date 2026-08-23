"""Bundle loading with actionable errors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from openrange.content.models import ModuleBundle, PathBundle, RoomBundle
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
