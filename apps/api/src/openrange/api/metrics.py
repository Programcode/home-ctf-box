"""Prometheus text-format metrics and request-counting middleware.

/api/metrics is intentionally unauthenticated: the exposition carries no
user data, only path templates, methods, status codes, and process-level
gauges. Cardinality is capped at MAX_SERIES_PATHS distinct path labels;
anything beyond collapses into a single "_overflow" bucket. The endpoint
is rate limited through the shared sliding-window limiter so a scraper
cannot turn an open port into free load.
"""

from __future__ import annotations

import gc
import time
from typing import Any

from fastapi import APIRouter, Request, Response
from openrange.api.auth.ratelimit import check_rate_limit
from sqlalchemy import func, select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

PROCESS_START = time.time()

_METRICS_PATH = "/api/metrics"
_MAX_SERIES_PATHS = 200
_RATE_LIMIT = 60  # scrapes per window; Prometheus defaults to one per 15s
_RATE_LIMIT_WINDOW = 60

_counts: dict[tuple[str, str, str], int] = {}
_duration_seconds: dict[tuple[str, str], float] = {}
_paths_seen: set[str] = set()


def escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _bounded_path(path: str) -> str:
    if path not in _paths_seen:
        if len(_paths_seen) >= _MAX_SERIES_PATHS:
            return "_overflow"
        _paths_seen.add(path)
    return path


def record_request(method: str, path: str, status: int, elapsed_seconds: float) -> None:
    bounded = _bounded_path(path)
    key = (method, bounded, str(status))
    _counts[key] = _counts.get(key, 0) + 1
    duration_key = (method, bounded)
    _duration_seconds[duration_key] = _duration_seconds.get(duration_key, 0.0) + elapsed_seconds


def _template_path(path: str, path_params: dict[str, Any] | None) -> str:
    """Rebuild the route template from the concrete path.

    scope["route"].path carries no include_router prefix, so templates are
    derived from the observed path instead: each matched parameter value is
    swapped back to its placeholder. Longest values first so nested
    substitutions cannot truncate each other.
    """
    template = path
    for key, value in sorted((path_params or {}).items(), key=lambda item: -len(str(item[1]))):
        template = template.replace(str(value), f"{{{key}}}", 1)
    return template


class MetricsMiddleware(BaseHTTPMiddleware):
    """Counts every request by method, route template, and status code.

    Registered outermost so rate-limited 429s and auth failures are
    counted too. The metrics endpoint itself is skipped: scraping would
    otherwise inflate its own counters every interval.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == _METRICS_PATH:
            return await call_next(request)
        started = time.perf_counter()
        response = await call_next(request)
        if request.scope.get("route") is not None:
            path = _template_path(request.url.path, request.scope.get("path_params"))
        else:
            path = "unmatched"
        elapsed = time.perf_counter() - started
        record_request(request.method, path, response.status_code, elapsed)
        return response


def render_process_gauges() -> list[tuple[str, dict[str, str], float]]:
    gauges: list[tuple[str, dict[str, str], float]] = [
        ("openrange_process_uptime_seconds", {}, time.time() - PROCESS_START),
    ]
    for generation, stats in enumerate(gc.get_stats()):
        gauges.append(
            (
                "openrange_gc_collections_total",
                {"generation": str(generation)},
                float(stats["collections"]),
            )
        )
    return gauges


def render_db_pool_gauges() -> list[tuple[str, dict[str, str], float]]:
    try:
        from openrange.api.db import engine

        pool = getattr(engine, "pool", None)
        size = getattr(pool, "size", None)
        checked_out = getattr(pool, "checkedout", None)
        if not callable(size) or not callable(checked_out):
            return []
        return [
            ("openrange_db_pool_size", {}, float(size())),
            ("openrange_db_pool_checked_out", {}, float(checked_out())),
        ]
    except Exception:
        # Metrics must survive a broken database; pool series are optional.
        return []


async def lab_instance_gauges() -> list[tuple[str, float]]:
    """Per-state lab instance counts; omitted when labs or db are unavailable."""
    try:
        from openrange.api.db import session_factory
        from openrange.api.labs.models import LabInstance
    except ImportError:  # pragma: no cover - labs always ships with the api
        return []
    if session_factory is None:
        return []
    try:
        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(LabInstance.state, func.count()).group_by(LabInstance.state)
                )
            ).all()
    except Exception:
        return []
    return [(str(state), float(count)) for state, count in rows]


def _family(lines: list[str], name: str, metric_type: str, help_text: str) -> None:
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} {metric_type}")


def _series(name: str, labels: dict[str, str], value: float) -> str:
    label_text = ""
    if labels:
        rendered = ",".join(f'{key}="{escape_label(val)}"' for key, val in sorted(labels.items()))
        label_text = f"{{{rendered}}}"
    return f"{name}{label_text} {value}"


def render_metrics_text() -> str:
    """Render the exposition without the async lab gauges."""
    lines: list[str] = []

    _family(
        lines, "openrange_process_uptime_seconds", "gauge", "Seconds since the api process started."
    )
    _family(lines, "openrange_gc_collections_total", "counter", "GC collections per generation.")
    _family(lines, "openrange_db_pool_size", "gauge", "SQLAlchemy connection pool size.")
    _family(
        lines,
        "openrange_db_pool_checked_out",
        "gauge",
        "Connections currently checked out of the SQLAlchemy pool.",
    )
    _family(
        lines,
        "openrange_http_requests_total",
        "counter",
        "Requests counted by method, route path template, and status code.",
    )
    _family(
        lines,
        "openrange_http_request_duration_seconds_sum",
        "counter",
        "Cumulative request duration; divide by _count for the average.",
    )
    _family(
        lines,
        "openrange_http_request_duration_seconds_count",
        "counter",
        "Number of timed requests; identical cardinality to requests_total.",
    )

    for name, labels, value in render_process_gauges():
        lines.append(_series(name, labels, value))
    for name, labels, value in render_db_pool_gauges():
        lines.append(_series(name, labels, value))
    for (method, path, status), count in sorted(_counts.items()):
        lines.append(
            _series(
                "openrange_http_requests_total",
                {"method": method, "path": path, "status": status},
                float(count),
            )
        )
        duration_key = (method, path)
        seconds = _duration_seconds.get(duration_key, 0.0)
        labels = {"method": method, "path": path}
        lines.append(_series("openrange_http_request_duration_seconds_sum", labels, seconds))
        lines.append(_series("openrange_http_request_duration_seconds_count", labels, float(count)))
    return "\n".join(lines) + "\n"


async def render_lab_metrics_text() -> str:
    lines: list[str] = []
    gauges = await lab_instance_gauges()
    if gauges:
        _family(
            lines, "openrange_lab_instances", "gauge", "Lab instances grouped by lifecycle state."
        )
        for state, count in gauges:
            lines.append(_series("openrange_lab_instances", {"state": state}, count))
    return "\n".join(lines)


router = APIRouter(tags=["system"])


@router.get("/metrics")
async def metrics(request: Request) -> Response:
    allowed = await check_rate_limit(request, "metrics-scrape", _RATE_LIMIT, _RATE_LIMIT_WINDOW)
    if not allowed:
        return Response(
            content='{"type":"about:blank","title":"Too Many Requests","status":429,'
            '"detail":"metrics scrape rate limit exceeded"}',
            status_code=429,
            media_type="application/problem+json",
            headers={"retry-after": str(_RATE_LIMIT_WINDOW)},
        )
    body = render_metrics_text()
    lab_section = await render_lab_metrics_text()
    if lab_section:
        body += lab_section
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")


__all__ = ["MetricsMiddleware", "record_request", "render_metrics_text", "router"]
