"""Request/response schemas for the runner API (docs/contracts/runner-api.md)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

Port = Annotated[int, Field(ge=1, le=65535)]

RESERVED_LABEL_PREFIX = "openrange."


class CreateInstanceRequest(BaseModel):
    instance_id: str = Field(min_length=1)
    image: str | None = None
    build_context_tar_gz_base64: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    cpus: float = Field(default=1.0, gt=0)
    mem_mb: int = Field(default=512, gt=0)
    pids_limit: int = Field(default=256, gt=0)
    ports: list[Port] = Field(min_length=1)
    ttl_seconds: int = Field(default=5400, gt=0)
    labels: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_source_and_labels(self) -> CreateInstanceRequest:
        if self.image is None and self.build_context_tar_gz_base64 is None:
            raise ValueError("either image or build_context_tar_gz_base64 is required")
        if self.image is not None and self.build_context_tar_gz_base64 is not None:
            raise ValueError("image and build_context_tar_gz_base64 are mutually exclusive")
        for key in self.labels:
            if key.startswith(RESERVED_LABEL_PREFIX):
                raise ValueError(f"label prefix {RESERVED_LABEL_PREFIX}* is reserved")
        return self


class InstanceTarget(BaseModel):
    name: str
    url: str


class CreateInstanceResponse(BaseModel):
    state: Literal["ready"]
    network: str
    targets: list[InstanceTarget]


class RestartInstanceResponse(BaseModel):
    state: Literal["ready"]


class GetInstanceResponse(BaseModel):
    state: Literal["ready", "starting", "stopped", "missing"]
    started_at: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class ReconcileRequest(BaseModel):
    known_instance_ids: list[str] = Field(default_factory=list)


class ReconcileResponse(BaseModel):
    removed_containers: list[str] = Field(default_factory=list)
    removed_networks: list[str] = Field(default_factory=list)


class HealthzResponse(BaseModel):
    status: Literal["ok"]
    docker: bool
