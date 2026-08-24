"""API settings: deployment config plus API-specific knobs."""

from __future__ import annotations

from functools import lru_cache

from openrange.config import Settings
from pydantic import Field


class ApiSettings(Settings):
    model_config = Settings.model_config

    session_cookie_name: str = "openrange_session"
    session_lifetime_minutes: int = 60 * 24 * 14
    csrf_cookie_name: str = "openrange_csrf"
    password_min_length: int = 10
    password_breached_check: bool = False  # opt-in k-anonymity HIBP-style hook
    login_max_attempts: int = 10
    login_lockout_minutes: int = 15
    setup_mode: bool = True  # setup wizard allowed until first admin exists
    oidc_issuer: str = ""  # empty disables OIDC
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    team_max_size: int = Field(default=8, ge=2, le=64)


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings()
