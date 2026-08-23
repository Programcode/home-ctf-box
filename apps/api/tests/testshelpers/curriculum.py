"""Fixture curriculum for learning-engine tests.

Writes a strict-model-valid mini curriculum (two required modules, one
optional branch, one room with tiered hints) into a temp directory and
points CONTENT_DIR at it.
"""

from __future__ import annotations

from pathlib import Path

PATH_YAML = """\
apiVersion: openrange.io/v1
kind: Path
metadata:
  slug: foundations-path
  title: Foundations Path
  version: 2.1.0
  difficulty: beginner
  points: 250
  estimated_minutes: 45
spec:
  track: web-foundations
  summary: A tiny curriculum exercising every learning engine behaviour end to end.
  modules:
    - slug: learning-basics
    - slug: advanced-bits
      optional_branch: true
    - slug: capstone-prep
  capstones:
    - hint-lab-room
"""

MODULE_BASICS_YAML = """\
apiVersion: openrange.io/v1
kind: Module
metadata:
  slug: learning-basics
  title: Learning Basics
  version: 1.0.0
  difficulty: beginner
  points: 100
  estimated_minutes: 20
spec:
  track: web-foundations
  summary: Foundations module covering ordered sections and graded quizzes.
  objectives:
    - Understand ordered section progression rules
    - Answer server-graded quiz questions safely
  labs: []
  sections:
    - id: intro
      title: Introduction to ordering
      blocks:
        - type: prose
          markdown: Sections unlock in order once prerequisites are met.
        - type: quiz
          question_id: q-order
          question: What unlocks the next required section?
          options:
            - id: prereq
              text: Completing prerequisites
            - id: luck
              text: Random luck
          answer_ids:
            - prereq
          explanation: Ordered prerequisites gate progress through the path.
    - id: quiz-check
      title: Knowledge check
      blocks:
        - type: quiz
          question_id: q-check
          question: Which option is the correct one?
          options:
            - id: right-opt
              text: The right choice
            - id: wrong-opt
              text: The wrong choice
          answer_ids:
            - right-opt
          explanation: The bundle answer key stays on the server side.
    - id: wrap-up
      title: Wrap up
      blocks:
        - type: prose
          markdown: You finished the basics module.
"""

MODULE_ADVANCED_YAML = """\
apiVersion: openrange.io/v1
kind: Module
metadata:
  slug: advanced-bits
  title: Advanced Bits
  version: 1.1.0
  difficulty: easy
  points: 50
  estimated_minutes: 15
spec:
  track: web-foundations
  summary: Optional branch module that must never gate required progress.
  objectives:
    - Explore optional depth without blocking others
    - Verify optional sections stay ungated
  labs: []
  sections:
    - id: deep-dive
      title: Optional deep dive
      blocks:
        - type: code
          language: python
          code: print("optional")
"""

MODULE_CAPSTONE_YAML = """\
apiVersion: openrange.io/v1
kind: Module
metadata:
  slug: capstone-prep
  title: Capstone Prep
  version: 1.0.2
  difficulty: easy
  points: 100
  estimated_minutes: 10
spec:
  track: web-foundations
  summary: Final required module tying the path to its hands-on lab room.
  objectives:
    - Connect theory to the practical lab room
    - Complete the final required section
  labs:
    - hint-lab-room
  sections:
    - id: capstone-intro
      title: Meet your capstone
      blocks:
        - type: prose
          markdown: Use progressive hints wisely; each tier costs XP-safe points.
"""

ROOM_YAML = """\
apiVersion: openrange.io/v1
kind: Room
metadata:
  slug: hint-lab-room
  title: Hint Lab Room
  version: 3.0.1
  difficulty: beginner
  points: 100
  estimated_minutes: 30
spec:
  track: web-foundations
  type: guided
  summary: Minimal guided room used to exercise progressive hint reveals.
  objectives:
    - Reveal hint tiers one at a time
    - Unlock the solution after all tiers
  scope:
    allowed_targets:
      - http://target:8080
  target:
    build_context: ./target
    ports:
      - 8080
    healthcheck:
      http_path: /healthz
  tasks:
    - id: find-leak
      title: Find the leaked value
      prompt: Locate the secret value exposed by the sample service.
      points: 100
      hints:
        - cost: 5
          text: Look closely at the response headers.
        - cost: 10
          text: The header name rhymes with ghost.
      solution: Send a request and read the X-Secret-Flag response header value.
      validator:
        type: exact
        value: flag-header-value
"""


def write_curriculum(root: Path) -> Path:
    """Materialise the fixture curriculum under *root* and return it."""
    (root / "paths" / "foundations-path").mkdir(parents=True, exist_ok=True)
    (root / "modules" / "learning-basics").mkdir(parents=True, exist_ok=True)
    (root / "modules" / "advanced-bits").mkdir(parents=True, exist_ok=True)
    (root / "modules" / "capstone-prep").mkdir(parents=True, exist_ok=True)
    (root / "rooms" / "hint-lab-room").mkdir(parents=True, exist_ok=True)
    (root / "paths" / "foundations-path" / "path.yaml").write_text(PATH_YAML)
    (root / "modules" / "learning-basics" / "module.yaml").write_text(MODULE_BASICS_YAML)
    (root / "modules" / "advanced-bits" / "module.yaml").write_text(MODULE_ADVANCED_YAML)
    (root / "modules" / "capstone-prep" / "module.yaml").write_text(MODULE_CAPSTONE_YAML)
    (root / "rooms" / "hint-lab-room" / "room.yaml").write_text(ROOM_YAML)
    return root
