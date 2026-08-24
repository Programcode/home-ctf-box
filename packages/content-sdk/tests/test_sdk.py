"""Unit tests for the content SDK core."""

from __future__ import annotations

from pathlib import Path

import pytest
from openrange.content.harness import expected_flag
from openrange.content.linting import lint_room
from openrange.content.loader import LoadError, load_bundle
from openrange.content.models import RoomBundle, Task, Validator
from openrange.content.solver import (
    SolveContext,
    derive_flag,
    find_flags,
    validate_answer,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "content" / "rooms" / "busted-login"


def test_load_exemplar_room() -> None:
    bundle = load_bundle(FIXTURE / "room.yaml")
    assert isinstance(bundle, RoomBundle)
    assert bundle.metadata.slug == "busted-login"
    assert bundle.total_points == bundle.metadata.points == 100


def test_flag_derivation_is_deterministic_and_scoped() -> None:
    a = derive_flag(b"k", instance_id="i1", content_slug="room", task_id="t1")
    b = derive_flag(b"k", instance_id="i1", content_slug="room", task_id="t1")
    c = derive_flag(b"k", instance_id="i2", content_slug="room", task_id="t1")
    d = derive_flag(b"other", instance_id="i1", content_slug="room", task_id="t1")
    assert a == b and a != c and a != d
    assert find_flags(f"noise {a} noise") == [a]


def test_validators() -> None:
    flag = derive_flag(b"k", instance_id="i", content_slug="r", task_id="t")
    assert validate_answer(Validator(type="per_session_flag"), flag, flag)
    assert not validate_answer(Validator(type="per_session_flag"), flag + "X", flag)
    assert validate_answer(Validator(type="exact", value="Hunter2"), "Hunter2", flag)
    assert validate_answer(Validator(type="normalized", value="Admin User"), "admin  user", flag)
    assert validate_answer(Validator(type="regex", value=r"\d{3}-\d{4}"), "123-4567", flag)
    assert validate_answer(Validator(type="numeric_range", min=1, max=10), "7.5", flag)
    assert validate_answer(Validator(type="set", values=["a", "b"]), "B, a", flag)
    import hashlib

    sha = hashlib.sha256(b"blob").hexdigest()
    assert validate_answer(Validator(type="file_hash", value=sha), "blob", flag)
    assert not validate_answer(Validator(type="manual"), "anything", flag)
    from openrange.content.solver import ValidatorError

    bogus = Validator(type="exact")  # exact without a value
    assert not validate_answer(bogus, "x", flag)
    with pytest.raises(ValidatorError):
        validate_answer(Validator(type="numeric_range"), "not-a-number", flag)


def test_lint_catches_missing_solver(tmp_path: Path) -> None:
    (tmp_path / "room.yaml").write_text((FIXTURE / "room.yaml").read_text())
    findings = lint_room(tmp_path)
    rules = {f.rule for f in findings}
    assert "solver" in rules
    assert "target" in rules


def test_lint_flags_style_and_branding(tmp_path: Path) -> None:
    import shutil

    shutil.copytree(FIXTURE, tmp_path / "room", dirs_exist_ok=True)
    lesson = tmp_path / "room" / "lesson" / "01-brief.md"
    lesson.write_text("# Delve into this\n\nA pivotal moment — tryhackme style. ![](x.png)\n")
    findings = lint_room(tmp_path / "room")
    rules = {f.rule for f in findings}
    assert "style-slop" in rules
    assert "style-dash" in rules
    assert "branding" in rules
    assert "a11y-image-alt" in rules


def test_load_error_is_actionable(tmp_path: Path) -> None:
    bad = tmp_path / "room.yaml"
    bad.write_text("apiVersion: openrange.io/v1\nkind: Room\nmetadata: {}\nspec: {}\n")
    with pytest.raises(LoadError) as excinfo:
        load_bundle(bad)
    assert "room.yaml" in str(excinfo.value)


def test_solve_context_shape() -> None:
    ctx = SolveContext(base_urls={"target": "http://x"}, expected_flags={"t": "FLAG{A}"})
    assert ctx.url() == "http://x"


def test_privilege_profile_default_is_locked() -> None:
    bundle = load_bundle(FIXTURE / "room.yaml")
    assert bundle.spec.target.privilege_profile == "locked"


def test_elevated_target_requires_reviewer_justification(tmp_path: Path) -> None:
    import shutil

    shutil.copytree(FIXTURE, tmp_path / "room", dirs_exist_ok=True)
    manifest = tmp_path / "room" / "room.yaml"
    text = manifest.read_text().replace(
        "  target:",
        "  target:\n    privilege_profile: elevated",
        1,
    )
    text = text.replace(
        "reviewer_notes: 'SQLite-backed Flask app; injection stays inside the room network.'",
        "reviewer_notes: short",
    )
    manifest.write_text(text)
    findings = lint_room(tmp_path / "room")
    assert "privilege-profile" in {f.rule for f in findings}

    notes = (
        "sshd needs setuid for privilege separation and the learner shell; "
        "caps are bounded to the ssh server profile."
    )
    manifest.write_text(
        manifest.read_text().replace("reviewer_notes: short", f"reviewer_notes: {notes}")
    )
    findings = lint_room(tmp_path / "room")
    assert "privilege-profile" not in {f.rule for f in findings}


EXTERNAL_YAML = """apiVersion: openrange.io/v1
kind: Room
metadata:
  slug: ext-wrapper
  title: 'External Wrapper'
  version: 1.0.0
  difficulty: beginner
  points: 75
  estimated_minutes: 15
spec:
  track: web-foundations
  type: guided
  summary: >-
    Wrapper room around an official upstream lab image pulled by digest,
    with authored lessons and a fixed public completion answer.
  objectives:
    - 'Complete the upstream lab objective through its own interface.'
    - 'Submit the documented public completion artifact.'
  scope:
    allowed_targets: ['http://target:3000']
  safety:
    simulated_only: true
    no_real_malware: true
    reviewer_notes: 'Runs the official unmodified upstream image on an isolated internal network.'
  target:
    external_image: example/upstream:latest@sha256:{digest}
    sidecars:
      - name: db
        image: example/companion:latest@sha256:{digest}
        env:
          EXAMPLE_PASSWORD: hunter2
    ports: [3000]
    healthcheck:
      http_path: /
      timeout_seconds: 120
    flag_delivery: static
  workstation: terminal
  tasks:
    - id: find-it
      title: 'Find the hidden page'
      prompt: >-
        Reach the documented upstream endpoint and submit its path as the
        public completion answer for this wrapper room.
      points: 75
      solution: |
        Open the upstream app, locate the documented hidden endpoint through
        its own interface, then submit its path as the completion answer.
      validator:
        type: exact
        value: '/score-board'
"""

_DIGEST = "a" * 64


def _write_external_room(tmp_path: Path, yaml_text: str) -> Path:
    room = tmp_path / "ext-wrapper"
    (room / "lesson").mkdir(parents=True)
    (room / "solver").mkdir()
    (room / "solver" / "solver.py").write_text("def solve(ctx):\n    raise RuntimeError\n")
    (room / "room.yaml").write_text(yaml_text.format(digest=_DIGEST))
    return room


def test_external_target_model_and_lint(tmp_path: Path) -> None:
    room = _write_external_room(tmp_path, EXTERNAL_YAML)
    bundle = load_bundle(room / "room.yaml")
    assert isinstance(bundle, RoomBundle)
    target = bundle.spec.target
    assert target.external_image == f"example/upstream:latest@sha256:{_DIGEST}"
    assert target.build_context == "./target"
    assert target.sidecars[0].name == "db"
    assert target.sidecars[0].env == {"EXAMPLE_PASSWORD": "hunter2"}

    rules = {f.rule: f.severity for f in lint_room(room)}
    assert "target" not in rules


def test_static_delivery_requires_declared_validator_values(tmp_path: Path) -> None:
    room = _write_external_room(tmp_path, EXTERNAL_YAML)
    manifest = room / "room.yaml"
    manifest.write_text(
        manifest.read_text().replace(
            "      validator:\n        type: exact\n        value: '/score-board'",
            "      validator:\n        type: per_session_flag",
        )
    )
    assert "static-flag-delivery" in {f.rule for f in lint_room(room)}


def test_expected_flag_static_answer_vs_derived() -> None:
    task = Task(
        id="find-it",
        title="Find the hidden page",
        prompt="Reach the documented upstream endpoint and submit its path.",
        points=10,
        solution="Browse the app until the hidden page renders, then submit its path.",
        validator=Validator(type="exact", value="/score-board"),
    )
    static = expected_flag(
        task, static_delivery=True, master_key=b"k", instance_id="i", content_slug="c"
    )
    derived = expected_flag(
        task, static_delivery=False, master_key=b"k", instance_id="i", content_slug="c"
    )
    assert static == "/score-board"
    assert derived.startswith("FLAG{")
