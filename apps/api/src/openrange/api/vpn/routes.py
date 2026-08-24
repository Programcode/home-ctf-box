"""VPN HTTP routes: /api/vpn, /api/vpn/admin, and /internal/vpn heartbeat."""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from openrange.api.auth.dependencies import CurrentUser, DbSession, require_permission
from openrange.api.auth.service import AuthError
from openrange.api.errors import problem_response
from openrange.api.users.models import User
from openrange.api.vpn import service as vpnsvc
from openrange.api.vpn.models import VpnDevice, VpnLease
from openrange.api.vpn.service import VpnProblem
from openrange.api.vpn.settings import VpnSettings, get_vpn_settings
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/vpn", tags=["vpn"])
admin_router = APIRouter(prefix="/api/vpn/admin", tags=["vpn"])
internal_router = APIRouter(prefix="/internal/vpn", tags=["vpn"])

VpnSettingsDep = Annotated[VpnSettings, Depends(get_vpn_settings)]
VpnAdminUser = Annotated[User, Depends(require_permission("lab:manage-any"))]


class DeviceCreateIn(BaseModel):
    # Canonical base64 of a 32-byte WireGuard public key: exactly 44 chars,
    # standard alphabet, padded.
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    public_key: str = Field(pattern=r"^[A-Za-z0-9+/]{43}=$")


def _problem(problem: VpnProblem) -> PlainTextResponse | Any:
    return problem_response(problem.status, problem.title, problem.detail)


async def _own_device(db: AsyncSession, user: User, device_id: str) -> VpnDevice:
    try:
        did = uuid.UUID(device_id)
    except ValueError as exc:
        raise AuthError("unknown device", 404) from exc
    device = await db.get(VpnDevice, did)
    if device is None:
        raise AuthError("unknown device", 404)
    # Existence of other users' devices stays hidden from non-operators.
    if device.user_id != user.id and not user.has_permission("lab:manage-any"):
        raise AuthError("unknown device", 404)
    return device


@router.post("/devices")
async def create_device(
    payload: DeviceCreateIn, user: CurrentUser, db: DbSession, settings: VpnSettingsDep
) -> Any:
    if not user.has_permission("vpn:issue"):
        raise AuthError("missing permission vpn:issue", 403)
    try:
        device, lease, config = await vpnsvc.register_device(
            db,
            user_id=user.id,
            name=payload.name,
            public_key=payload.public_key,
            settings=settings,
        )
    except VpnProblem as problem:
        return _problem(problem)
    return {
        "device": vpnsvc.device_view(device, address=lease.address),
        "config": config,
    }


@router.get("/devices")
async def list_devices(user: CurrentUser, db: DbSession) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(VpnDevice, VpnLease.address)
            .outerjoin(VpnLease, VpnLease.device_id == VpnDevice.id)
            .where(VpnDevice.user_id == user.id)
            .order_by(VpnDevice.created_at.desc())
            .limit(100)
        )
    ).all()
    return [vpnsvc.device_view(device, address=address) for device, address in rows]


@router.delete("/devices/{device_id}")
async def revoke_device(device_id: str, user: CurrentUser, db: DbSession) -> Any:
    device = await _own_device(db, user, device_id)
    await vpnsvc.revoke_device(db, device)
    return {"revoked": True}


@router.get("/devices/{device_id}/config.qr")
async def device_config(
    device_id: str,
    user: CurrentUser,
    db: DbSession,
    settings: VpnSettingsDep,
    format: str = Query(default="text"),
) -> Any:
    device = await _own_device(db, user, device_id)
    if format != "text":
        return _problem(
            VpnProblem(
                400,
                "Bad Request",
                "only format=text is supported; render the QR code client-side",
            )
        )
    if device.revoked_at is not None:
        return _problem(VpnProblem(410, "Gone", "device revoked; register a new device"))
    lease = await db.get(VpnLease, device.id)
    if lease is None:
        return _problem(VpnProblem(409, "Conflict", "device has no active address lease"))
    return PlainTextResponse(
        vpnsvc.render_client_config(address=str(lease.address), settings=settings)
    )


@router.get("/devices/{device_id}/status")
async def device_status(device_id: str, user: CurrentUser, db: DbSession) -> Any:
    device = await _own_device(db, user, device_id)
    return vpnsvc.device_view(device)


@admin_router.get("/devices")
async def admin_list_devices(_admin: VpnAdminUser, db: DbSession) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(VpnDevice, VpnLease.address)
            .outerjoin(VpnLease, VpnLease.device_id == VpnDevice.id)
            .order_by(VpnDevice.created_at.desc())
            .limit(200)
        )
    ).all()
    views = []
    for device, address in rows:
        view = vpnsvc.device_view(device, address=address)
        view["user_id"] = str(device.user_id)
        views.append(view)
    return views


@internal_router.post("/heartbeat")
async def heartbeat(request: Request, db: DbSession, settings: VpnSettingsDep) -> Any:
    body = await request.body()
    try:
        vpnsvc.verify_gateway_signature(
            timestamp=request.headers.get("x-gateway-timestamp"),
            signature=request.headers.get("x-gateway-signature"),
            body=body,
            secret=settings.gateway_secret,
            replay_window_seconds=settings.replay_window_seconds,
        )
    except VpnProblem as problem:
        return _problem(problem)
    try:
        payload: Any = json.loads(body)
    except ValueError:
        return _problem(VpnProblem(400, "Bad Request", "body must be JSON"))
    key = payload.get("device_public_key") if isinstance(payload, dict) else None
    if not isinstance(key, str) or not key:
        return _problem(VpnProblem(400, "Bad Request", "device_public_key is required"))
    try:
        await vpnsvc.record_heartbeat(db, device_public_key=key)
    except VpnProblem as problem:
        return _problem(problem)
    return {"ok": True}
