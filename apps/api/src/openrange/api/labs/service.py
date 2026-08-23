"""Lab lifecycle orchestration (plan Phase 6).

The API owns desired state and bookkeeping; the runner owns Docker.
Every transition writes a RuntimeEvent. Flags are derived per user and
per instance (ADR 0007) and only ever travel to the runner.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from openrange.api.config import get_settings
from openrange.api.labs.models import CleanupJob, LabInstance, RuntimeEvent
from openrange.api.labs.runner_client import RunnerClient, RunnerError
from openrange.api.solver_bridge import derive_flag
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class LabError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(slots=True)
class RoomTargetInfo:
    slug: str
    version: str
    ports: list[int]
    build_context: Any  # Path when running from a repo checkout
    image: str | None = None
    task_ids: list[str] | None = None


async def active_instance_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(LabInstance)
        .where(
            LabInstance.user_id == user_id,
            LabInstance.state.in_(["requested", "scheduled", "starting", "ready"]),
        )
    )
    return int((await db.execute(stmt)).scalar_one())


async def _record(db: AsyncSession, instance_id: uuid.UUID, event: str, detail: str = "") -> None:
    db.add(RuntimeEvent(instance_id=instance_id, event=event[:32], detail=detail[:2000]))


def _derive_flags(user_id: uuid.UUID, info: RoomTargetInfo, instance_id: str) -> dict[str, str]:
    settings = get_settings()
    master = settings.flag_master_key.encode()
    task_ids = info.task_ids or ["default"]
    if len(task_ids) == 1:
        return {
            "default": derive_flag(
                master,
                instance_id=instance_id,
                content_slug=f"{info.slug}@{info.version}",
                task_id=task_ids[0],
            )
        }
    return {
        tid: derive_flag(
            master,
            instance_id=instance_id,
            content_slug=f"{info.slug}@{info.version}",
            task_id=tid,
        )
        for tid in task_ids
    }


async def start_lab(
    db: AsyncSession,
    runner: RunnerClient,
    *,
    user_id: uuid.UUID,
    info: RoomTargetInfo,
) -> LabInstance:
    settings = get_settings()
    if await active_instance_count(db, user_id) >= settings.lab_max_concurrency_per_user:
        raise LabError("lab concurrency limit reached; stop a lab first", 409)

    instance = LabInstance(
        user_id=user_id,
        room_slug=info.slug,
        content_version=info.version,
        state="scheduled",
        ttl_minutes=settings.lab_default_ttl_minutes,
    )
    db.add(instance)
    await db.flush()
    await _record(db, instance.id, "scheduled")

    runner_instance_id = str(uuid.uuid4())
    flags = _derive_flags(user_id, info, runner_instance_id)
    try:
        packed = None
        if info.build_context is not None:
            from openrange.api.labs.runner_client import RunnerClient as _RC

            packed = _RC.pack_context(info.build_context)
        env = (
            {"ROOM_FLAG": flags["default"]}
            if info.task_ids is None or len(info.task_ids) <= 1
            else {
                **{"ROOM_FLAG": flags["default"]},
                **{
                    f"ROOM_FLAG_{tid.upper().replace('-', '_')}": flags[tid]
                    for tid in info.task_ids
                },
            }
        )
        handle = await runner.create_instance(
            instance_id=runner_instance_id,
            # Runner builds from the bundle context; prebuilt registry
            # images are the alternative path, never combined.
            image=None if info.build_context is not None else info.image,
            env=env,
            ports=info.ports,
            ttl_seconds=settings.lab_default_ttl_minutes * 60,
            labels={"room": info.slug},
            build_context_tar_gz_base64=packed,
        )
    except RunnerError as exc:
        instance.state = "failed"
        instance.failure_reason = exc.detail[:2000]
        await _record(db, instance.id, "failed", exc.detail)
        raise LabError("runner failed to start the lab", 502) from exc

    instance.runner_instance_id = uuid.UUID(runner_instance_id)
    instance.network_name = handle.network
    instance.state = "ready"
    instance.started_at = datetime.now(UTC)
    instance.expires_at = datetime.now(UTC) + timedelta(minutes=instance.ttl_minutes)
    instance.targets_json = json.dumps(handle.targets)
    instance.flags_json = json.dumps(flags)
    await _record(db, instance.id, "ready")
    await db.flush()
    return instance


async def reset_lab(db: AsyncSession, runner: RunnerClient, instance: LabInstance) -> None:
    if instance.state != "ready" or instance.runner_instance_id is None:
        raise LabError("only ready labs can be reset", 409)
    instance.state = "resetting"
    await db.flush()
    try:
        await runner.restart(str(instance.runner_instance_id))
    except RunnerError as exc:
        instance.state = "failed"
        instance.failure_reason = exc.detail[:2000]
        await _record(db, instance.id, "failed", exc.detail)
        raise LabError("runner reset failed", 502) from exc
    instance.state = "ready"
    instance.expires_at = datetime.now(UTC) + timedelta(minutes=instance.ttl_minutes)
    await _record(db, instance.id, "reset")


async def extend_lab(db: AsyncSession, instance: LabInstance, minutes: int) -> None:
    settings = get_settings()
    if instance.state != "ready":
        raise LabError("only ready labs can be extended", 409)
    if minutes not in (15, 30, 60):
        raise LabError("extend by 15, 30 or 60 minutes", 422)
    base = instance.expires_at or datetime.now(UTC)
    capped = min(
        (base - datetime.now(UTC)).total_seconds() / 60 + minutes,
        settings.lab_default_ttl_minutes * 4,
    )
    instance.expires_at = datetime.now(UTC) + timedelta(minutes=capped)
    await _record(db, instance.id, "extended", f"+{minutes}m")


async def stop_lab(
    db: AsyncSession, runner: RunnerClient, instance: LabInstance, reason: str
) -> None:
    if instance.state in ("cleaned", "expired", "stopping"):
        return
    instance.state = "stopping"
    await db.flush()
    if instance.runner_instance_id is not None:
        try:
            await runner.delete(str(instance.runner_instance_id))
        except RunnerError as exc:
            # Queue cleanup instead of failing the user request.
            db.add(CleanupJob(instance_id=instance.id, reason=reason))
            await _record(db, instance.id, "cleanup-queued", exc.detail)
    instance.state = "cleaned" if reason != "expired" else "expired"
    instance.stopped_at = datetime.now(UTC)
    await _record(db, instance.id, "stopped", reason)


async def expire_due_labs(db: AsyncSession, runner: RunnerClient) -> list[uuid.UUID]:
    """Reaper pass: expire anything past its lease."""
    now = datetime.now(UTC)
    due = (
        (
            await db.execute(
                select(LabInstance).where(
                    LabInstance.state == "ready",
                    LabInstance.expires_at.is_not(None),
                    LabInstance.expires_at < now,
                )
            )
        )
        .scalars()
        .all()
    )
    for instance in due:
        await stop_lab(db, runner, instance, "expired")
    return [i.id for i in due]


async def reconcile_with_runner(db: AsyncSession, runner: RunnerClient) -> dict[str, list[str]]:
    """Remove runner-side resources the database no longer knows about."""
    known_rows = (
        await db.execute(
            select(LabInstance.runner_instance_id).where(
                LabInstance.runner_instance_id.is_not(None)
            )
        )
    ).scalars()
    known = [str(r) for r in known_rows]
    removed: dict[str, list[str]] = await runner.reconcile(known)
    return removed


def public_view(instance: LabInstance) -> dict[str, Any]:
    return {
        "id": str(instance.id),
        "room": instance.room_slug,
        "state": instance.state,
        "expires_at": instance.expires_at.isoformat() if instance.expires_at else None,
        "targets": json.loads(instance.targets_json or "{}"),
        "created_at": instance.created_at.isoformat(),
    }
