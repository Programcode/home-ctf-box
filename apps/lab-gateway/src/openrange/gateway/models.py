"""Response models for the gateway API."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Component states reported by /healthz."""

    status: str
    runner: bool
    secret: bool
