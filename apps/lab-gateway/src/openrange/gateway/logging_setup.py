"""JSON logging to stdout with request-id correlation.

structlog-style output: one JSON object per line. The middleware assigns a
request id, returns it as ``X-Request-ID``, and logs exactly one line per
HTTP request. Paths are logged WITHOUT query strings because terminal and
proxy URLs carry the lab token. Authorization headers, token bodies, and
SSH credentials are never logged.
"""

from __future__ import annotations

import contextvars
import datetime as dt
import json
import logging
import sys
import time
import uuid
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "openrange_request_id", default=None
)

_RESERVED_LOG_ATTRS = frozenset[Any](
    set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime", "taskName"}
)


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            entry["request_id"] = request_id
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON handler on the root logger; drop uvicorn's access log."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Our middleware emits one JSON line per request instead.
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False


class RequestContextMiddleware:
    """Assigns request ids, sets X-Request-ID, and logs one line per HTTP call."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex
        token = request_id_var.set(request_id)
        logger = logging.getLogger(scope.get("root_path", "") or "openrange.gateway.request")
        started_at = time.perf_counter()
        status_seen: list[int] = []

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_seen.append(message["status"])
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", request_id)
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            # Path only: the query string can carry the lab token.
            extra = {
                "path": scope.get("path", ""),
                "method": scope.get("method", ""),
                "duration_ms": elapsed_ms,
                "request_id": request_id,
            }
            if scope["type"] == "http":
                extra["status"] = status_seen[0] if status_seen else None
                logger.info("http_request", extra=extra)
            else:
                logger.info("ws_connect", extra=extra)
            request_id_var.reset(token)
