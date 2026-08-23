"""HMAC request authentication per docs/contracts/runner-api.md."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from collections.abc import Awaitable, Callable
from functools import lru_cache

from openrange.config import ConfigError, load_settings
from openrange.runner.problems import problem_body
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REPLAY_WINDOW_SECONDS = 300

_TOKEN_ENV_VAR = "OPENRANGE_RUNNER_API_TOKEN"  # noqa: S105 - env var name, not a credential


@lru_cache(maxsize=1)
def _settings_token_fallback() -> str:
    try:
        return load_settings().runner_api_token
    except ConfigError:
        return ""


def resolve_runner_token() -> str:
    """Runner API token: environment variable first, then openrange.config settings."""
    token = os.environ.get(_TOKEN_ENV_VAR)
    if token:
        return token
    return _settings_token_fallback()


def _deny(status: int, title: str, detail: str) -> Callable[[Send], Awaitable[None]]:
    payload = json.dumps(problem_body(status, title, detail)).encode()

    async def send_denial(send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/problem+json"),
                    (b"content-length", str(len(payload)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})

    return send_denial


class HmacAuthMiddleware:
    """Pure ASGI HMAC verifier.

    Buffers the request body so the signature covers f"{timestamp}:{body}"
    exactly as sent; /healthz is exempt.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == "/healthz":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        more_body = True
        while more_body:
            message = await receive()
            body.extend(message.get("body", b""))
            more_body = bool(message.get("more_body", False))
        denial = self._verify(scope, bytes(body))
        if denial is not None:
            await denial(send)
            return

        async def replay_receive() -> Message:
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay_receive, send)

    def _verify(self, scope: Scope, body: bytes) -> Callable[[Send], Awaitable[None]] | None:
        headers = Headers(scope=scope)
        timestamp = headers.get("x-runner-timestamp")
        signature = headers.get("x-runner-signature")
        if timestamp is None or signature is None:
            return _deny(401, "Unauthorized", "missing X-Runner-Timestamp/X-Runner-Signature")
        token = resolve_runner_token()
        if not token:
            return _deny(401, "Unauthorized", "runner api token is not configured")
        try:
            issued_at = int(timestamp)
        except ValueError:
            return _deny(401, "Unauthorized", "X-Runner-Timestamp must be unix seconds")
        if abs(time.time() - issued_at) > REPLAY_WINDOW_SECONDS:
            return _deny(401, "Unauthorized", "timestamp outside the replay window")
        expected = hmac.new(
            token.encode(), timestamp.encode() + b":" + body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected.encode(), signature.encode()):
            return _deny(401, "Unauthorized", "invalid signature")
        return None
