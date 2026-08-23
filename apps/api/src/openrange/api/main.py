"""OpenRange control-plane API application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from openrange.api.auth.oidc_routes import router as oidc_router
from openrange.api.auth.routes import me as auth_me_router
from openrange.api.auth.routes import router as auth_router
from openrange.api.auth.webauthn_routes import router as webauthn_router
from openrange.api.db import dispose_engine, init_engine
from openrange.api.errors import register_error_handlers
from openrange.api.health import router as health_router
from openrange.api.labs.routes import router as labs_router
from openrange.api.learning.routes import router as learning_router
from openrange.api.metrics import MetricsMiddleware
from openrange.api.metrics import router as metrics_router
from openrange.api.middleware import RateLimitMiddleware, RequestContextMiddleware
from openrange.api.orgs.routes import api_router as orgs_router
from openrange.api.readiness import router as readiness_router
from openrange.api.scoring.routes import router as scoring_router
from openrange.api.setup.routes import router as setup_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_engine()
    try:
        yield
    finally:
        await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenRange API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.include_router(readiness_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router)
    app.include_router(auth_me_router)
    app.include_router(labs_router)
    app.include_router(learning_router)
    app.include_router(orgs_router)
    app.include_router(scoring_router)
    app.include_router(webauthn_router)
    app.include_router(oidc_router)
    app.include_router(setup_router)
    app.include_router(metrics_router, prefix="/api")
    register_error_handlers(app)
    return app


app = create_app()
