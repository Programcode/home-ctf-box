"""Metrics exposition shape, middleware counting, and readiness semantics."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


def parse_exposition(body: str) -> dict[str, int]:
    """Every sample line must end in a float; returns family -> sample count."""
    families: dict[str, int] = {}
    for line in body.splitlines():
        if not line or line.startswith("#"):
            continue
        name_and_labels, _, raw_value = line.rpartition(" ")
        assert raw_value, f"sample without value: {line!r}"
        assert float(raw_value) >= 0.0, f"unparseable value: {line!r}"
        family = name_and_labels.split("{", 1)[0]
        families[family] = families.get(family, 0) + 1
    return families


def counter_value(body: str, method: str, path: str, status: str) -> int:
    prefix = f'openrange_http_requests_total{{method="{method}",path="{path}",status="{status}"}}'
    for line in body.splitlines():
        if line.startswith(prefix):
            return int(float(line.rsplit(" ", 1)[1]))
    return 0


async def test_metrics_exposition_parses(client: AsyncClient) -> None:
    await client.get("/api/healthz")
    response = await client.get("/api/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    families = parse_exposition(response.text)
    for expected in (
        "openrange_process_uptime_seconds",
        "openrange_gc_collections_total",
        "openrange_http_requests_total",
        "openrange_http_request_duration_seconds_sum",
        "openrange_http_request_duration_seconds_count",
    ):
        assert expected in families, f"missing family {expected} in {sorted(families)}"
    for declared in (
        "openrange_db_pool_size",
        "openrange_db_pool_checked_out",
    ):
        # Declared even when the engine is down; samples appear only then.
        assert f"# TYPE {declared} gauge" in response.text


async def test_middleware_counters_increment(client: AsyncClient) -> None:
    await client.get("/api/healthz")
    first = counter_value((await client.get("/api/metrics")).text, "GET", "/api/healthz", "200")
    assert first >= 1
    await client.get("/api/healthz")
    second = counter_value((await client.get("/api/metrics")).text, "GET", "/api/healthz", "200")
    assert second == first + 1


async def test_metrics_endpoint_not_self_counted(client: AsyncClient) -> None:
    await client.get("/api/metrics")
    body = (await client.get("/api/metrics")).text
    assert counter_value(body, "GET", "/api/metrics", "200") == 0


async def test_unmatched_requests_share_single_bucket(client: AsyncClient) -> None:
    await client.get("/definitely-not-a-route")
    body = (await client.get("/api/metrics")).text
    assert counter_value(body, "GET", "unmatched", "404") >= 1


@pytest.mark.integration
async def test_readyz_200_when_services_up(client: AsyncClient) -> None:
    response = await client.get("/api/readyz")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ready"
    for component in ("database", "redis", "content_dir", "migrations"):
        check = payload["checks"][component]
        assert check["ok"], f"{component} reported down: {check}"
