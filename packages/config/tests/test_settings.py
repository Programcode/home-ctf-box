import pytest
from openrange.config import ConfigError, Settings


def test_dev_mode_fills_safe_defaults() -> None:
    s = Settings(env="dev", secret_key="dev-only-secret", flag_master_key="dev-only-flags")
    assert s.lab_default_ttl_minutes == 90
    assert s.edition == "community"


def test_production_rejects_missing_runner_token() -> None:
    with pytest.raises(ConfigError, match="runner_api_token"):
        Settings(
            env="production",
            secret_key="x" * 40,
            flag_master_key="y" * 40,
            s3_access_key="ak",
            s3_secret_key="sk",
            meili_master_key="mk",
        )


def test_production_rejects_dev_placeholder_secrets() -> None:
    with pytest.raises(ConfigError, match="placeholder"):
        Settings(
            env="production",
            secret_key="dev-only-not-really-a-secret",
            flag_master_key="y" * 40,
            runner_api_token="t" * 24,
            s3_access_key="ak",
            s3_secret_key="sk",
            meili_master_key="mk",
        )


def test_production_rejects_documented_dev_s3_credentials() -> None:
    with pytest.raises(ConfigError, match="dev defaults"):
        Settings(
            env="production",
            secret_key="x" * 40,
            flag_master_key="y" * 40,
            runner_api_token="t" * 24,
            s3_access_key="openrange-dev",
            s3_secret_key=openrange_dev_secret(),
            meili_master_key="mk",
        )


def openrange_dev_secret() -> str:
    return "openrange-dev-secret"


def test_production_accepts_real_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENRANGE_ENV", "production")
    s = Settings(
        secret_key="a" * 40,
        flag_master_key="b" * 40,
        runner_api_token="t" * 24,
        s3_access_key="AKIA-REAL",
        s3_secret_key="real-secret-value",
        meili_master_key="mk",
    )
    assert s.env == "production"
