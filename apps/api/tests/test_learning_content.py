"""Content loading unit tests: bundle discovery, ordering, prereq
computation, mtime cache invalidation. No database required."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from openrange.api.learning import content
from testshelpers.curriculum import write_curriculum


@pytest.fixture(autouse=True)
def curriculum_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    root = write_curriculum(tmp_path / "content")
    monkeypatch.setenv(content.CONTENT_DIR_ENV, str(root))
    content.clear_caches()
    yield root
    content.clear_caches()


def test_discovers_paths_and_modules() -> None:
    paths = content.list_path_bundles()
    assert [p.metadata.slug for p in paths] == ["foundations-path"]
    modules = content.list_module_bundles()
    assert set(modules) == {"learning-basics", "advanced-bits", "capstone-prep"}
    assert content.get_room_bundle("hint-lab-room") is not None
    assert content.get_room_bundle("nope") is None


def test_outline_orders_sections_and_computes_prereqs() -> None:
    bundle = content.get_path_bundle("foundations-path")
    assert bundle is not None
    outline = content.path_outline(bundle)
    assert outline.required_modules == ("learning-basics", "capstone-prep")
    assert outline.optional_modules == ("advanced-bits",)
    by_id = {(s.module_slug, s.section_id): s for s in outline.sections}
    intro = by_id[("learning-basics", "intro")]
    assert intro.prerequisites == ()
    check = by_id[("learning-basics", "quiz-check")]
    assert check.prerequisites == (("learning-basics", "intro"),)
    capstone = by_id[("capstone-prep", "capstone-intro")]
    assert ("learning-basics", "wrap-up") in capstone.prerequisites
    deep = by_id[("advanced-bits", "deep-dive")]
    # Optional-branch sections never gate and are never gated.
    assert deep.optional_branch is True
    assert deep.prerequisites == ()
    assert all(("advanced-bits", "deep-dive") not in s.prerequisites for s in outline.sections)


def test_cache_invalidates_on_mtime_change() -> None:
    bundle = content.get_path_bundle("foundations-path")
    assert bundle is not None
    assert bundle.metadata.version == "2.1.0"
    manifest = Path(os.environ[content.CONTENT_DIR_ENV]) / ("paths/foundations-path/path.yaml")
    manifest.write_text(manifest.read_text().replace("2.1.0", "9.9.9"))
    updated = content.get_path_bundle("foundations-path")
    assert updated is not None
    assert updated.metadata.version == "9.9.9"


def test_find_quiz_section_resolution() -> None:
    module, section = content.find_quiz_section("quiz-check", None)
    assert module.metadata.slug == "learning-basics"
    assert section.title == "Knowledge check"
    with pytest.raises(LookupError):
        content.find_quiz_section("missing-section", None)
    # Non-quiz sections never match.
    with pytest.raises(LookupError):
        content.find_quiz_section("intro", "advanced-bits")
