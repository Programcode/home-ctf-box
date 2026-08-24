"""Content bundle models.

The Pydantic models here are authoritative for the Python side; the JSON
Schemas under schemas/ are generated from them for tooling and CI so the
two can never drift.
"""

from __future__ import annotations

import re
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

Difficulty = Literal["beginner", "easy", "medium", "hard", "insane"]
RoomType = Literal["guided", "challenge", "box", "investigation", "range"]
Track = Literal[
    "web-foundations",
    "linux-networking",
    "windows-ad",
    "crypto-binary",
    "defense-cloud",
]
WorkstationKind = Literal["none", "terminal", "desktop"]
FlagDelivery = Literal["env", "file", "static"]

ValidatorType = Literal[
    "exact",
    "normalized",
    "regex",
    "numeric_range",
    "set",
    "per_session_flag",
    "file_hash",
    "manual",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LicenseInfo(StrictModel):
    code: Literal["AGPL-3.0-or-later"] = "AGPL-3.0-or-later"
    content: Literal["CC-BY-SA-4.0", "CC-BY-4.0", "MIT"] = "CC-BY-SA-4.0"


class Metadata(StrictModel):
    slug: Annotated[str, Field(min_length=3, max_length=64)]
    title: Annotated[str, Field(min_length=3, max_length=96)]
    version: str
    difficulty: Difficulty
    points: Annotated[int, Field(ge=10, le=1000)]
    estimated_minutes: Annotated[int, Field(ge=5, le=600)]
    tags: list[Annotated[str, Field(max_length=32)]] = Field(default_factory=list, max_length=12)
    license: LicenseInfo = Field(default_factory=LicenseInfo)

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not SLUG_RE.match(v):
            raise ValueError(f"slug must match {SLUG_RE.pattern}")
        return v

    @field_validator("version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not SEMVER_RE.match(v):
            raise ValueError("version must be semver (major.minor.patch)")
        return v


class Hint(StrictModel):
    cost: int = 0
    text: Annotated[str, Field(min_length=8)]


class Validator(StrictModel):
    type: ValidatorType
    value: str | None = None
    min: float | None = None
    max: float | None = None
    values: list[str] | None = None


class Task(StrictModel):
    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")]
    title: Annotated[str, Field(min_length=4, max_length=140)]
    prompt: Annotated[str, Field(min_length=16)]
    points: Annotated[int, Field(ge=10, le=500)]
    hints: list[Hint] = Field(default_factory=list)
    solution: Annotated[str, Field(min_length=40)]
    validator: Validator


class Healthcheck(StrictModel):
    http_path: str | None = "/healthz"
    tcp_port: int | None = None
    timeout_seconds: int = 30

    def one_of(self) -> bool:
        return bool(self.http_path or self.tcp_port)


class SidecarSpec(StrictModel):
    name: Annotated[str, Field(min_length=2, max_length=64)]
    image: Annotated[
        str,
        Field(description="official companion image ref, digest-pinned"),
    ]
    env: dict[str, str] = Field(default_factory=dict)


class TargetSpec(StrictModel):
    build_context: Annotated[
        str, Field(default="./target", description="relative dir containing Dockerfile")
    ]
    image_name: str | None = None  # derived from slug when absent
    external_image: Annotated[
        str | None,
        Field(
            description=(
                "official upstream image ref (digest-pinned). When set, the "
                "harness pulls and runs it instead of building build_context."
            )
        ),
    ] = None
    sidecars: Annotated[
        list[SidecarSpec],
        Field(
            default_factory=list,
            max_length=2,
            description=(
                "companion containers from the upstream deployment topology "
                "(e.g. the database service an upstream compose file expects)"
            ),
        ),
    ]
    env: Annotated[
        dict[str, str],
        Field(
            default_factory=dict,
            description=(
                "target container environment; external rooms use the "
                "variables upstream documents for their image"
            ),
        ),
    ]
    ports: list[Annotated[int, Field(ge=1, le=65535)]] = Field(min_length=1, max_length=16)
    healthcheck: Healthcheck
    flag_delivery: FlagDelivery = "env"
    flag_env: str = "ROOM_FLAG"
    flag_path: str | None = None
    egress_allowlist: list[str] = Field(default_factory=list)
    privilege_profile: Annotated[
        Literal["locked", "elevated"],
        Field(
            description=(
                "locked: cap_drop ALL + no-new-privileges (default, web targets). "
                "elevated: bounded capability set without no-new-privileges for "
                "targets that need setuid (sshd privsep, sudo, SUID binaries)."
            )
        ),
    ] = "locked"

    @field_validator("healthcheck")
    @classmethod
    def _hc_valid(cls, v: Healthcheck) -> Healthcheck:
        if not v.one_of():
            raise ValueError("healthcheck needs http_path or tcp_port")
        return v


class SafetyDeclaration(StrictModel):
    simulated_only: bool = True
    no_real_malware: bool = True
    reviewer_notes: str = ""


class ScopeSpec(StrictModel):
    allowed_targets: list[str] = Field(min_length=1)
    forbidden: list[str] = Field(
        default_factory=lambda: ["control-plane", "other-labs", "internet", "host"]
    )


class RoomSpec(StrictModel):
    track: Track
    type: RoomType
    summary: Annotated[str, Field(min_length=40)]
    objectives: list[Annotated[str, Field(min_length=16)]] = Field(min_length=2, max_length=10)
    prerequisites: list[str] = Field(default_factory=list)
    scope: ScopeSpec
    safety: SafetyDeclaration = Field(default_factory=SafetyDeclaration)
    target: TargetSpec
    workstation: WorkstationKind = "terminal"
    tasks: Annotated[list[Task], Field(min_length=1, max_length=12)]

    @field_validator("tasks")
    @classmethod
    def _unique_tasks(cls, tasks: list[Task]) -> list[Task]:
        ids = [t.id for t in tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("task ids must be unique")
        return tasks


class RoomBundle(StrictModel):
    api_version: Literal["openrange.io/v1"] = Field(alias="apiVersion")
    kind: Literal["Room"]
    metadata: Metadata
    spec: RoomSpec

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def _points_total_consistent(self) -> RoomBundle:
        task_total = sum(t.points for t in self.spec.tasks)
        if task_total != self.metadata.points:
            raise ValueError(
                f"metadata.points ({self.metadata.points}) != sum of task points ({task_total})"
            )
        return self

    @property
    def total_points(self) -> int:
        return sum(t.points for t in self.spec.tasks)


# --- Module and path bundles (learning engine contracts) ---


class BlockBase(StrictModel):
    type: ClassVar[str]


class ProseBlock(BlockBase):
    type: Literal["prose"]
    markdown: str


class CalloutBlock(BlockBase):
    type: Literal["callout"]
    tone: Literal["info", "warning", "danger", "tip"]
    markdown: str


class CodeBlock(BlockBase):
    type: Literal["code"]
    language: str
    code: str


class QuizOption(StrictModel):
    id: str
    text: str


class QuizBlock(BlockBase):
    type: Literal["quiz"]
    question_id: str
    question: str
    options: list[QuizOption]
    answer_ids: list[str]
    explanation: str


SectionBlock = Annotated[
    ProseBlock | CalloutBlock | CodeBlock | QuizBlock, Field(discriminator="type")
]


class Section(StrictModel):
    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")]
    title: Annotated[str, Field(min_length=4, max_length=120)]
    blocks: list[SectionBlock] = Field(min_length=1)


class ModuleSpec(StrictModel):
    track: Track
    summary: Annotated[str, Field(min_length=40)]
    objectives: list[Annotated[str, Field(min_length=16)]] = Field(min_length=2, max_length=10)
    sections: Annotated[list[Section], Field(min_length=1, max_length=24)]
    cheat_sheet: str | None = None
    labs: list[str] = Field(default_factory=list)


class ModuleBundle(StrictModel):
    api_version: Literal["openrange.io/v1"] = Field(alias="apiVersion")
    kind: Literal["Module"]
    metadata: Metadata
    spec: ModuleSpec

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PathModuleRef(StrictModel):
    slug: str
    optional_branch: bool = False


class PathSpec(StrictModel):
    track: Track
    summary: Annotated[str, Field(min_length=40)]
    modules: list[PathModuleRef] = Field(min_length=1)
    capstones: list[str] = Field(default_factory=list)
    certificate: bool = True


class PathBundle(StrictModel):
    api_version: Literal["openrange.io/v1"] = Field(alias="apiVersion")
    kind: Literal["Path"]
    metadata: Metadata
    spec: PathSpec

    model_config = ConfigDict(populate_by_name=True, extra="forbid")
