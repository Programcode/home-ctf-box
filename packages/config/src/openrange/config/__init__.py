"""Typed configuration for every OpenRange service.

Rules:
- dev mode may fall back to safe local defaults;
- staging/production fail closed: any missing or dev-defaulted secret
  raises ConfigError at startup instead of serving traffic.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Env = Literal["dev", "staging", "production"]
Edition = Literal["community", "cluster"]

_DEV_SECRET_MARKERS = ("dev-only", "change-me")


class ConfigError(Exception):
    """Raised when configuration is unsafe for the target environment."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENRANGE_",
        env_file=".env",
        extra="ignore",
    )

    env: Env = "dev"
    edition: Edition = "community"
    public_url: str = "http://localhost:3000"

    secret_key: str = ""
    flag_master_key: str = ""

    database_url: str = "postgresql+asyncpg://openrange:openrange@localhost:15432/openrange"
    redis_url: str = "redis://localhost:16379/0"

    s3_endpoint: str = "http://localhost:19000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "openrange"

    meili_url: str = "http://localhost:17700"
    meili_master_key: str = ""

    runner_api_url: str = "http://localhost:8771"
    runner_api_token: str = ""
    lab_network_prefix: str = "172.30.0.0/16"
    lab_default_ttl_minutes: int = Field(default=90, ge=5, le=24 * 60)
    lab_max_concurrency_per_user: int = Field(default=2, ge=1, le=20)

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "no-reply@openrange.local"
    smtp_tls: bool = False

    @model_validator(mode="after")
    def _fail_closed(self) -> Settings:
        if self.env == "dev":
            return self
        problems = []
        for name in ("secret_key", "flag_master_key", "runner_api_token"):
            value: str = getattr(self, name)
            if not value:
                problems.append(f"{name} is required outside dev")
            elif any(marker in value for marker in _DEV_SECRET_MARKERS):
                problems.append(f"{name} still carries a dev placeholder")
        if not self.s3_access_key or not self.s3_secret_key:
            problems.append("s3 credentials are required outside dev")
        elif self.s3_access_key == "openrange-dev" or self.s3_secret_key == "openrange-dev-secret":
            problems.append("s3 credentials still carry the documented dev defaults")
        if not self.meili_master_key:
            problems.append("meili_master_key is required outside dev")
        if problems:
            raise ConfigError("; ".join(problems))
        return self


def load_settings() -> Settings:
    return Settings()
