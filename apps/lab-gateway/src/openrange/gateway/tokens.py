"""Short-lived, lab-scoped gateway tokens.

Compact format: ``lab-v1.<base64url(payload)>.<base64url(hmac)>``

The payload is compact JSON with sorted keys. The HMAC-SHA256 signature is
computed over ``b"lab-v1." + <base64url(payload)>`` with the shared
``OPENRANGE_GATEWAY_SECRET``. The API mints these tokens (minting endpoint
lands in a later branch); the gateway only verifies them. Verification uses
constant-time comparison and rejects expired tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

TOKEN_SCHEME = "lab-v1"  # noqa: S105 - scheme label, not a credential
DEFAULT_TTL_SECONDS = 300


class TokenError(Exception):
    """Raised when a token fails validation. Messages are safe to log."""


@dataclass(frozen=True)
class LabTokenClaims:
    """Validated claims carried by a lab token."""

    sub: str
    lab: str
    exp: int
    ports: tuple[int, ...]
    ssh: bool = False
    ssh_user: str | None = None
    ssh_pass: str | None = None

    def allows_port(self, port: int) -> bool:
        """Return whether the token may reach ``port`` on its lab."""
        return port in self.ports


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError as exc:
        raise TokenError("malformed token encoding") from exc


def _require_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise TokenError(f"missing or invalid claim: {key}")
    return value


def mint_token(
    *,
    secret: str,
    sub: str,
    lab: str,
    ports: list[int] | tuple[int, ...],
    ssh: bool = False,
    ssh_user: str | None = None,
    ssh_pass: str | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> str:
    """Mint a lab token. Used by the API and reused by the test suite."""
    issued_at = int(time.time() if now is None else now)
    payload: dict[str, object] = {
        "sub": sub,
        "lab": lab,
        "exp": issued_at + int(ttl_seconds),
        "ports": sorted(ports),
        "ssh": ssh,
    }
    if ssh_user is not None:
        payload["ssh_user"] = ssh_user
    if ssh_pass is not None:
        payload["ssh_pass"] = ssh_pass
    encoded_payload = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )
    signing_input = f"{TOKEN_SCHEME}.{encoded_payload}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{TOKEN_SCHEME}.{encoded_payload}.{_b64encode(signature)}"


def verify_token(token: str, secret: str, *, now: float | None = None) -> LabTokenClaims:
    """Verify signature and expiry, returning typed claims.

    Raises TokenError for any structural, signature, or expiry problem.
    """
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != TOKEN_SCHEME or not parts[1] or not parts[2]:
        raise TokenError("malformed token")
    expected_signature = hmac.new(
        secret.encode(), f"{TOKEN_SCHEME}.{parts[1]}".encode(), hashlib.sha256
    ).digest()
    # Constant-time compare; never leak how much of the signature matched.
    if not hmac.compare_digest(expected_signature, _b64decode(parts[2])):
        raise TokenError("bad signature")
    try:
        payload = json.loads(_b64decode(parts[1]))
    except ValueError as exc:
        raise TokenError("malformed payload") from exc
    if not isinstance(payload, dict):
        raise TokenError("payload is not an object")

    exp = payload.get("exp")
    if not isinstance(exp, int) or isinstance(exp, bool):
        raise TokenError("missing or invalid claim: exp")
    if int(now if now is not None else time.time()) >= exp:
        raise TokenError("token expired")
    raw_ports = payload.get("ports")
    if not isinstance(raw_ports, list) or any(
        isinstance(p, bool) or not isinstance(p, int) for p in raw_ports
    ):
        raise TokenError("missing or invalid claim: ports")
    ssh_claim = payload.get("ssh", False)
    if not isinstance(ssh_claim, bool):
        raise TokenError("invalid claim: ssh")
    optional_user = payload.get("ssh_user")
    optional_pass = payload.get("ssh_pass")
    if optional_user is not None and not isinstance(optional_user, str):
        raise TokenError("invalid claim: ssh_user")
    if optional_pass is not None and not isinstance(optional_pass, str):
        raise TokenError("invalid claim: ssh_pass")

    return LabTokenClaims(
        sub=_require_str(payload, "sub"),
        lab=_require_str(payload, "lab"),
        exp=exp,
        ports=tuple(int(p) for p in raw_ports),
        ssh=ssh_claim,
        ssh_user=optional_user,
        ssh_pass=optional_pass,
    )
