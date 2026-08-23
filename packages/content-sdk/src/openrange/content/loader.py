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
    kind = str(load_yaml(path).get("apiVersion", "")) and str(load_yaml(path).get("kind", ""))
    models = {"Room": RoomBundle, "Module": ModuleBundle, "Path": PathBundle}
    model = models.get(kind)
    if model is None:
        raise LoadError(path, f"unknown or missing kind: {kind!r}")
    try:
        return model.model_validate(load_yaml(path))  # type: ignore[return-value]
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first.get("loc", []))
        raise LoadError(path, f"{loc}: {first['msg']}") from exc


def load_room(room_dir: Path) -> tuple[RoomBundle, Path]:
    manifest = room_dir / "room.yaml"
    if not manifest.exists():
        raise LoadError(manifest, "room.yaml missing")
    return load_bundle(manifest), manifest
