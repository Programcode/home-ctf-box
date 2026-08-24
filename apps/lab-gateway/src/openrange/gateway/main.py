"""OpenRange lab gateway application factory."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import APIRouter, FastAPI, Request
from openrange.gateway.config import GatewaySettings, get_settings
from openrange.gateway.desktop import (
    DesktopRegistry,
    HttpVpnHeartbeatClient,
)
from openrange.gateway.desktop import (
    reap_loop as desktop_reap_loop,
)
from openrange.gateway.desktop import router as desktop_router
from openrange.gateway.logging_setup import RequestContextMiddleware, configure_logging
from openrange.gateway.models import HealthResponse
from openrange.gateway.problems import register_error_handlers
from openrange.gateway.proxy import router as proxy_router
from openrange.gateway.runner import HttpRunnerClient, RunnerClient
from openrange.gateway.sessions import SessionRegistry, reap_loop
from openrange.gateway.terminal import router as terminal_router

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
async def healthz(request: Request) -> HealthResponse:
    settings: GatewaySettings = request.app.state.settings
    runner_ok = await request.app.state.runner.ping()
    secret_ok = bool(settings.gateway_secret)
    return HealthResponse(
        status="ok" if runner_ok and secret_ok else "degraded",
        runner=runner_ok,
        secret=secret_ok,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: GatewaySettings = app.state.settings
    configure_logging()
    app.state.http = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=None, write=None, pool=10.0)
    )
    reaper = asyncio.create_task(reap_loop(app.state.sessions))
    desktop_reaper = asyncio.create_task(desktop_reap_loop(app.state.desktops))
    logger.info(
        "gateway_started",
        extra={
            "runner_url": settings.runner_url,
            "max_sessions_per_lab": settings.max_sessions_per_lab,
        },
    )
    try:
        yield
    finally:
        reaper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reaper
        desktop_reaper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await desktop_reaper
        await app.state.sessions.aclose_all()
        await app.state.desktops.aclose_all()
        await app.state.http.aclose()
        logger.info("gateway_stopped")


def create_app(
    settings: GatewaySettings | None = None, runner: RunnerClient | None = None
) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(
        title="OpenRange Lab Gateway",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.runner = runner or HttpRunnerClient(
        resolved.runner_url, resolved.runner_service_token
    )
    app.state.sessions = SessionRegistry(
        max_per_lab=resolved.max_sessions_per_lab,
        resume_ttl_seconds=resolved.resume_ttl_seconds,
    )
    app.state.desktops = DesktopRegistry(
        max_per_lab=resolved.max_sessions_per_lab,
        resume_ttl_seconds=resolved.resume_ttl_seconds,
    )
    # Invoked by a later WireGuard peer watcher; wired now so deployment
    # config (OPENRANGE_API_URL + gateway secret) is stable.
    app.state.vpn_heartbeat = HttpVpnHeartbeatClient(secret=resolved.gateway_secret)
    register_error_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(proxy_router)
    app.include_router(terminal_router)
    app.include_router(desktop_router)
    app.include_router(router)
    return app


app = create_app()


def main() -> None:
    """Run the gateway server."""
    settings = get_settings()
    configure_logging()
    uvicorn.run(create_app(), host=settings.host, port=settings.port, access_log=False)
