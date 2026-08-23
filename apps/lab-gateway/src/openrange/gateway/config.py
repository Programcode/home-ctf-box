"""Environment-driven gateway settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Settings resolved from the environment.

    Every variable is documented in docs/contracts/gateway-api.md.
    """

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore", populate_by_name=True)

    gateway_secret: str = Field(default="", validation_alias="OPENRANGE_GATEWAY_SECRET")
    runner_url: str = Field(default="http://127.0.0.1:8771", validation_alias="RUNNER_URL")
    runner_service_token: str = Field(default="", validation_alias="RUNNER_SERVICE_TOKEN")
    max_sessions_per_lab: int = Field(
        default=4, ge=1, validation_alias="OPENRANGE_GATEWAY_MAX_SESSIONS"
    )
    resume_ttl_seconds: float = Field(
        default=60.0, gt=0, validation_alias="OPENRANGE_GATEWAY_RESUME_TTL_SECONDS"
    )
    ssh_port: int = Field(default=22, ge=1, le=65535, validation_alias="OPENRANGE_GATEWAY_SSH_PORT")
    ssh_user: str = Field(default="lab", validation_alias="OPENRANGE_GATEWAY_SSH_USER")
    ssh_password: str = Field(default="", validation_alias="OPENRANGE_GATEWAY_SSH_PASSWORD")
    host: str = Field(default="127.0.0.1", validation_alias="OPENRANGE_GATEWAY_HOST")
    port: int = Field(default=8772, ge=1, le=65535, validation_alias="OPENRANGE_GATEWAY_PORT")


@lru_cache(maxsize=1)
def get_settings() -> GatewaySettings:
    """Return the process-wide settings instance."""
    return GatewaySettings()
