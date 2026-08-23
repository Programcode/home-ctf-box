"""Lab HTTP routes: /api/labs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from openrange.api.auth.dependencies import CurrentUser, DbSession
from openrange.api.auth.service import AuthError
from openrange.api.labs import service as labsvc
from openrange.api.labs.models import LabInstance
from openrange.api.labs.runner_client import RunnerClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/labs", tags=["labs"])


def get_runner() -> RunnerClient:
    return RunnerClient()


RunnerDep = Annotated[RunnerClient, Depends(get_runner)]


class StartLabIn(BaseModel):
    room: str


class ExtendIn(BaseModel):
    minutes: int


async def _own_instance(db: AsyncSession, user: CurrentUser, lab_id: str) -> LabInstance:
    try:
        iid = uuid.UUID(lab_id)
    except ValueError as exc:
        raise AuthError("unknown lab", 404) from exc
    instance = await db.get(LabInstance, iid)
    if instance is None:
        raise AuthError("unknown lab", 404)
    if instance.user_id != user.id and not user.has_permission("lab:manage-any"):
        # Existence of other users' labs stays hidden.
        raise AuthError("unknown lab", 404)
    return instance


@router.post("")
async def start(
    payload: StartLabIn, user: CurrentUser, db: DbSession, runner: RunnerDep
) -> dict[str, object]:
    if not user.has_permission("lab:start"):
        raise AuthError("missing permission lab:start", 403)
    bundle_dir = labsvc_bundle_dir(payload.room)
    if bundle_dir is None:
        raise AuthError("unknown room", 404)
    from openrange.content.loader import load_room

    bundle, _manifest = load_room(bundle_dir)
    info = labsvc.RoomTargetInfo(
        slug=bundle.metadata.slug,
        version=bundle.metadata.version,
        ports=list(bundle.spec.target.ports),
        build_context=(bundle_dir / bundle.spec.target.build_context).resolve(),
        task_ids=[t.id for t in bundle.spec.tasks],
    )
    instance = await labsvc.start_lab(db, runner, user_id=user.id, info=info)
    return labsvc.public_view(instance)


def labsvc_bundle_dir(room: str) -> Path | None:
    from openrange.api.solver_bridge import find_bundle_dir

    return find_bundle_dir(room)


@router.get("")
async def list_mine(user: CurrentUser, db: DbSession) -> list[dict[str, object]]:
    rows = (
        (
            await db.execute(
                select(LabInstance)
                .where(LabInstance.user_id == user.id)
                .order_by(LabInstance.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [labsvc.public_view(r) for r in rows]


@router.get("/{lab_id}")
async def detail(lab_id: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    instance = await _own_instance(db, user, lab_id)
    view = labsvc.public_view(instance)
    expires = instance.expires_at or instance.created_at
    view["time_remaining_minutes"] = max(
        0, round((expires - datetime.now(UTC)).total_seconds() / 60)
    )
    return view


@router.post("/{lab_id}/extend")
async def extend(
    lab_id: str, payload: ExtendIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    instance = await _own_instance(db, user, lab_id)
    await labsvc.extend_lab(db, instance, payload.minutes)
    return labsvc.public_view(instance)


@router.post("/{lab_id}/reset")
async def reset(
    lab_id: str, user: CurrentUser, db: DbSession, runner: RunnerDep
) -> dict[str, object]:
    instance = await _own_instance(db, user, lab_id)
    await labsvc.reset_lab(db, runner, instance)
    return labsvc.public_view(instance)


@router.delete("/{lab_id}")
async def stop(lab_id: str, user: CurrentUser, db: DbSession, runner: RunnerDep) -> dict[str, bool]:
    instance = await _own_instance(db, user, lab_id)
    await labsvc.stop_lab(db, runner, instance, "user-stop")
    return {"stopped": True}
