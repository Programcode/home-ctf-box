"""First-admin setup wizard.

No default credentials ever ship. A fresh installation prints a one-time
setup URL containing a random token; whoever completes it becomes admin
and the setup mode closes.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter
from openrange.api.auth import service
from openrange.api.auth.dependencies import DbSession
from openrange.api.auth.service import AuthError
from openrange.api.auth.tokens import generate_token
from openrange.api.config import get_settings
from openrange.api.setup.tokens import get_pending_setup_token, store_setup_token
from pydantic import BaseModel

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SetupStatus(BaseModel):
    required: bool


class SetupComplete(BaseModel):
    username: str
    password: str
    token: str


@router.get("/status", response_model=SetupStatus)
async def status(db: DbSession) -> SetupStatus:
    return SetupStatus(required=await service.user_count(db) == 0)


@router.post("/begin")
async def begin_setup(db: DbSession) -> dict[str, str]:
    """Generate a fresh one-time setup token.

    Only allowed while no admin exists. Installations fetch this from the
    server console (docker compose exec) rather than over the network in
    production; the endpoint exists for the local wizard flow.
    """
    if not get_settings().setup_mode or await service.user_count(db) > 0:
        raise AuthError("setup already completed", 409)
    token = generate_token(32)
    store_setup_token(token)
    return {"setup_url": f"{get_settings().public_url}/setup?token={token}"}


@router.post("/complete")
async def complete_setup(payload: SetupComplete, db: DbSession) -> dict[str, str]:
    if await service.user_count(db) > 0:
        raise AuthError("setup already completed", 409)
    expected = get_pending_setup_token()
    if expected is None or payload.token != expected:
        raise AuthError("invalid setup token", 403)
    user = await service.create_user(
        db,
        username=payload.username,
        password=payload.password,
        roles=("admin",),
    )
    await service.seed_roles(db)
    store_setup_token(None)
    return {"admin_id": str(user.id)}


def setup_token_ttl() -> timedelta:
    return timedelta(hours=24)
