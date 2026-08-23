"""Token validation matrix for the lab-v1 compact token format."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from openrange.gateway.tokens import TokenError, mint_token, verify_token

SECRET = "test-gateway-secret"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _signed_token(secret: str, payload: dict[str, object]) -> str:
    encoded = _b64(json.dumps(payload).encode())
    signature = hmac.new(secret.encode(), f"lab-v1.{encoded}".encode(), hashlib.sha256).digest()
    return f"lab-v1.{encoded}.{_b64(signature)}"


def _future_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sub": "user-9",
        "lab": "lab-xyz",
        "exp": int(time.time()) + 600,
        "ports": [8000],
        "ssh": False,
    }
    payload.update(overrides)
    return payload


def test_roundtrip_preserves_claims() -> None:
    token = mint_token(
        secret=SECRET,
        sub="user-9",
        lab="lab-xyz",
        ports=[8000, 9000],
        ssh=True,
        ssh_user="alice",
        ssh_pass="wonderland",
        ttl_seconds=120,
    )
    claims = verify_token(token, SECRET)
    assert claims.sub == "user-9"
    assert claims.lab == "lab-xyz"
    assert claims.ports == (8000, 9000)
    assert claims.ssh is True
    assert claims.ssh_user == "alice"
    assert claims.ssh_pass == "wonderland"
    assert claims.exp > int(time.time())


def test_payload_is_deterministic_and_sorted() -> None:
    first = mint_token(secret=SECRET, sub="u", lab="l", ports=[2, 1], ttl_seconds=60, now=100)
    second = mint_token(secret=SECRET, sub="u", lab="l", ports=[1, 2], ttl_seconds=60, now=100)
    assert first == second


def test_wrong_secret_rejected() -> None:
    token = mint_token(secret=SECRET, sub="u", lab="l", ports=[1])
    with pytest.raises(TokenError, match="bad signature"):
        verify_token(token, "not-the-secret")


def test_tampered_payload_rejected() -> None:
    token = mint_token(secret=SECRET, sub="u", lab="l", ports=[1])
    scheme, _, signature = token.split(".")
    tampered_body = _b64(json.dumps(_future_payload(ports=[22])).encode())
    with pytest.raises(TokenError, match="bad signature"):
        verify_token(f"{scheme}.{tampered_body}.{signature}", SECRET)


def test_expired_token_rejected() -> None:
    token = mint_token(secret=SECRET, sub="u", lab="l", ports=[1], ttl_seconds=-10)
    with pytest.raises(TokenError, match="expired"):
        verify_token(token, SECRET)


def test_expiry_boundary_is_inclusive() -> None:
    now = 1_000_000
    token = mint_token(secret=SECRET, sub="u", lab="l", ports=[1], ttl_seconds=60, now=now)
    with pytest.raises(TokenError, match="expired"):
        verify_token(token, SECRET, now=now + 60)


def test_malformed_tokens_rejected() -> None:
    for bad in ["", "lab-v1", "lab-v1.onlytwo", "wrong-v1.a.b", "lab-v1.."]:
        with pytest.raises(TokenError):
            verify_token(bad, SECRET)


def test_non_json_payload_rejected() -> None:
    token = f"lab-v1.{_b64(b'not-json')}.{_b64(b'x')}"
    with pytest.raises(TokenError):
        verify_token(token, SECRET)


def test_non_object_payload_rejected() -> None:
    token = f"lab-v1.{_b64(b'[1,2]')}.{_b64(b'x')}"
    with pytest.raises(TokenError):
        verify_token(token, SECRET)


def test_signed_bad_claim_types_rejected() -> None:
    cases: list[dict[str, object]] = [
        {"sub": ""},
        {"sub": 7},
        {"lab": ""},
        {"exp": "soon"},
        {"ports": "8000"},
        {"ports": [True]},
        {"ports": [1.5]},
        {"ssh": "yes"},
        {"ssh_user": 3},
        {"ssh_pass": []},
    ]
    for override in cases:
        token = _signed_token(SECRET, _future_payload(**override))
        with pytest.raises(TokenError) as excinfo:
            verify_token(token, SECRET)
        assert "expired" not in str(excinfo.value)


def test_allows_port() -> None:
    claims = verify_token(mint_token(secret=SECRET, sub="u", lab="l", ports=[8000]), SECRET)
    assert claims.allows_port(8000)
    assert not claims.allows_port(22)
