"""OpenRange lab runner agent application factory."""

from __future__ import annotations

import os
from typing import cast

from fastapi import APIRouter, FastAPI, Request, Response
from openrange.runner.auth import HmacAuthMiddleware
from openrange.runner.models import (
    CreateInstanceRequest,
    CreateInstanceResponse,
    GetInstanceResponse,
    HealthzResponse,
    ReconcileRequest,
    ReconcileResponse,
    RestartInstanceResponse,
)
from openrange.runner.pool import LabDocker
from openrange.runner.problems import register_error_handlers

router = APIRouter()


def _pool(request: Request) -> LabDocker:
    return cast("LabDocker", request.app.state.docker)


@router.post("/v1/instances", response_model=CreateInstanceResponse, status_code=201)
def create_instance(payload: CreateInstanceRequest, request: Request) -> CreateInstanceResponse:
    return _pool(request).create_instance(payload)


@router.post("/v1/instances/{instance_id}/restart", response_model=RestartInstanceResponse)
def restart_instance(instance_id: str, request: Request) -> RestartInstanceResponse:
    return _pool(request).restart_instance(instance_id)


@router.delete("/v1/instances/{instance_id}", status_code=204, response_class=Response)
def delete_instance(instance_id: str, request: Request) -> Response:
    _pool(request).delete_instance(instance_id)
    return Response(status_code=204)


@router.get("/v1/instances/{instance_id}", response_model=GetInstanceResponse)
def get_instance(instance_id: str, request: Request) -> GetInstanceResponse:
    return _pool(request).get_instance(instance_id)


@router.post("/v1/reconcile", response_model=ReconcileResponse)
def reconcile(payload: ReconcileRequest, request: Request) -> ReconcileResponse:
    return _pool(request).reconcile(payload.known_instance_ids)


@router.get("/healthz", response_model=HealthzResponse)
def healthz(request: Request) -> HealthzResponse:
    return HealthzResponse(status="ok", docker=_pool(request).ping())


def create_app(docker_pool: LabDocker | None = None) -> FastAPI:
    app = FastAPI(
        title="OpenRange Runner",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.docker = docker_pool or LabDocker()
    register_error_handlers(app)
    app.add_middleware(HmacAuthMiddleware)
    app.include_router(router)
    return app


app = create_app()


def main() -> None:
    """Run the runner API server."""
    import uvicorn

    uvicorn.run(
        create_app(),
        host=os.environ.get("OPENRANGE_RUNNER_HOST", "127.0.0.1"),
        port=int(os.environ.get("OPENRANGE_RUNNER_PORT", "8771")),
    )
