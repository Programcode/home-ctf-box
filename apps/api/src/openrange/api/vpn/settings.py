"""VPN issuance settings, resolved from OPENRANGE_VPN_* environment variables."""

from __future__ import annotations

from functools import lru_cache
from ipaddress import IPv4Network, ip_network

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VpnSettings(BaseSettings):
    """Settings for WireGuard device issuance and gateway heartbeat auth.

    Kept inside the vpn package so every variable stays next to the code
    that consumes it (see docs/contracts/vpn-api.md).
    """

    model_config = SettingsConfigDict(
        env_prefix="OPENRANGE_", extra="ignore", populate_by_name=True
    )

    vpn_pool: str = Field(default="10.99.0.0/16", validation_alias="OPENRANGE_VPN_POOL")
    vpn_server_public_key: str = Field(
        default="", validation_alias="OPENRANGE_VPN_SERVER_PUBLIC_KEY"
    )
    vpn_endpoint: str = Field(default="", validation_alias="OPENRANGE_VPN_ENDPOINT")
    # Comma-separated lab subnets; never 0.0.0.0/0.
    vpn_allowed_subnets: str = Field(
        default="172.30.0.0/16", validation_alias="OPENRANGE_VPN_ALLOWED_SUBNETS"
    )
    gateway_secret: str = Field(default="", validation_alias="OPENRANGE_GATEWAY_SECRET")
    replay_window_seconds: int = Field(default=300, ge=1)

    def pool_network(self) -> IPv4Network:
        network = ip_network(self.vpn_pool, strict=False)
        if not isinstance(network, IPv4Network):
            raise ValueError("vpn pool must be an IPv4 network")
        return network

    def allowed_subnets(self) -> list[str]:
        return [s.strip() for s in self.vpn_allowed_subnets.split(",") if s.strip()]


@lru_cache(maxsize=1)
def get_vpn_settings() -> VpnSettings:
    return VpnSettings()
