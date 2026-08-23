"""WebSocket-to-SSH bridge: browser terminal into lab instances.

Protocol (after the WebSocket opens):
- The gateway immediately sends ``{"type":"session","session_id":"..."}``.
- Binary frames flow verbatim to/from the SSH PTY.
- Text frames are control JSON: ``{"type":"resize","cols":..,"rows":..}``
  resizes the PTY; ``{"type":"close"}`` ends the session cleanly.
- Reconnect: reopen with ``?resume=<session-id>`` within the grace TTL to
  reattach to the live SSH channel.

Close codes: 1000 normal/end of SSH, 1008 policy violation (bad token,
wrong lab, ssh not permitted, unknown/expired resume), 1013 per-lab
concurrency cap reached, 1011 upstream failure. Credentials are never
logged.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from typing import TypeGuard

import asyncssh
from fastapi import APIRouter, WebSocket
from openrange.gateway.config import GatewaySettings
from openrange.gateway.runner import InstanceNotFoundError, RunnerUnavailableError
from openrange.gateway.sessions import (
    SessionCapReached,
    SessionRegistry,
    SessionUnavailable,
    TerminalSession,
)
from openrange.gateway.tokens import LabTokenClaims, TokenError, verify_token
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

CLOSE_NORMAL = 1000
CLOSE_POLICY_VIOLATION = 1008
CLOSE_INTERNAL_ERROR = 1011
CLOSE_TRY_AGAIN_LATER = 1013

_SSH_LOGIN_TIMEOUT_SECONDS = 10.0
_MAX_RESIZE_DIMENSION = 1000


async def _open_ssh_connection(
    settings: GatewaySettings, host: str, claims: LabTokenClaims
) -> asyncssh.SSHClientConnection:
    return await asyncssh.connect(
        host=host,
        port=settings.ssh_port,
        username=claims.ssh_user or settings.ssh_user,
        password=claims.ssh_pass or settings.ssh_password,
        known_hosts=None,
        login_timeout=_SSH_LOGIN_TIMEOUT_SECONDS,
    )


async def _open_ssh_session(
    settings: GatewaySettings, host: str, claims: LabTokenClaims
) -> tuple[asyncssh.SSHClientConnection, asyncssh.SSHClientProcess[bytes]]:
    """Connect and open a PTY; closes the connection if the PTY fails."""
    connection = await _open_ssh_connection(settings, host, claims)
    try:
        process: asyncssh.SSHClientProcess[bytes] = await connection.create_process(
            term_type="xterm-256color", encoding=None
        )
    except (OSError, asyncssh.Error):
        connection.close()
        raise
    return connection, process


def _valid_dimension(value: object) -> TypeGuard[int]:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 1 <= value <= _MAX_RESIZE_DIMENSION
    )


async def _pump(session: TerminalSession) -> None:
    """Move PTY output into the session queue until the channel ends."""
    try:
        while True:
            chunk = await session.process.stdout.read(8192)
            if not chunk:
                break
            session.offer(chunk)
    except asyncssh.Error as exc:
        logger.warning(
            "ssh_read_failed",
            extra={"session_id": session.session_id, "error_class": type(exc).__name__},
        )
    finally:
        session.closed = True
        session.offer(None)


async def _inbound(ws: WebSocket, session: TerminalSession) -> bool:
    """Browser -> SSH. Returns True when the client asked for a clean close."""
    while True:
        try:
            message = await ws.receive()
        except WebSocketDisconnect:
            return False
        payload = message.get("bytes")
        text = message.get("text")
        if payload is not None:
            session.process.stdin.write(payload)
            continue
        if text is None:
            continue
        try:
            control = json.loads(text)
        except ValueError:
            continue
        if not isinstance(control, dict):
            continue
        if control.get("type") == "close":
            return True
        if control.get("type") == "resize":
            cols = control.get("cols")
            rows = control.get("rows")
            if _valid_dimension(cols) and _valid_dimension(rows):
                try:
                    session.resize(cols, rows)
                except asyncssh.Error:
                    logger.warning("resize_failed", extra={"session_id": session.session_id})


async def _outbound(ws: WebSocket, session: TerminalSession) -> bool:
    """SSH -> browser; returns False when the PTY hits EOF."""
    while True:
        item = await session.queue.get()
        if item is None:
            return False
        await ws.send_bytes(item)


async def _run_attached(ws: WebSocket, session: TerminalSession) -> None:
    """Run both directions until either side ends; then start the grace window."""
    session.attached = True
    session.detached_at = None
    inbound_task: asyncio.Task[bool] = asyncio.create_task(_inbound(ws, session))
    outbound_task: asyncio.Task[bool] = asyncio.create_task(_outbound(ws, session))
    clean_close = False
    ssh_ended = False
    failure: BaseException | None = None
    try:
        done, pending = await asyncio.wait(
            {inbound_task, outbound_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            if task.cancelled():
                continue
            exc = task.exception()
            if exc is not None:
                failure = exc
            elif task is outbound_task:
                ssh_ended = not outbound_task.result()
            elif task is inbound_task:
                clean_close = inbound_task.result()
    finally:
        session.attached = False
        session.detached_at = time.monotonic()

    if failure is not None:
        logger.warning(
            "terminal_bridge_error",
            extra={"session_id": session.session_id, "error_class": type(failure).__name__},
            exc_info=failure,
        )
        with contextlib.suppress(Exception):
            await ws.close(code=CLOSE_INTERNAL_ERROR, reason="bridge error")
    elif clean_close or ssh_ended:
        with contextlib.suppress(Exception):
            await ws.close(code=CLOSE_NORMAL, reason="session ended")


@router.websocket("/terminal/{instance_id}")
async def terminal_endpoint(websocket: WebSocket, instance_id: str) -> None:
    app_state = websocket.app.state
    settings: GatewaySettings = app_state.settings
    registry: SessionRegistry = app_state.sessions

    async def deny(code: int, reason: str) -> None:
        logger.info("terminal_denied", extra={"reason": reason})
        with contextlib.suppress(Exception):
            await websocket.close(code=code, reason=reason)

    await websocket.accept()

    try:
        claims = verify_token(websocket.query_params.get("token") or "", settings.gateway_secret)
    except TokenError as exc:
        await deny(CLOSE_POLICY_VIOLATION, str(exc))
        return
    if claims.lab != instance_id:
        await deny(CLOSE_POLICY_VIOLATION, "token scoped to another lab")
        return
    if not claims.ssh:
        await deny(CLOSE_POLICY_VIOLATION, "ssh not permitted by token")
        return

    resume_id = websocket.query_params.get("resume")
    if resume_id:
        try:
            session = registry.get_for_resume(resume_id, instance_id, claims.sub)
        except SessionUnavailable:
            await deny(CLOSE_POLICY_VIOLATION, "resume unavailable")
            return
        logger.info("terminal_resumed", extra={"session_id": session.session_id})
        await websocket.send_text(json.dumps({"type": "session", "session_id": session.session_id}))
        await _run_attached(websocket, session)
        return

    try:
        address = await app_state.runner.instance_address(instance_id)
    except InstanceNotFoundError:
        await deny(CLOSE_POLICY_VIOLATION, "unknown lab instance")
        return
    except RunnerUnavailableError:
        await deny(CLOSE_INTERNAL_ERROR, "runner unavailable")
        return

    try:
        connection, process = await _open_ssh_session(settings, address.host, claims)
    except (OSError, asyncssh.Error) as exc:
        logger.warning(
            "ssh_connect_failed",
            extra={"lab_instance_id": instance_id, "error_class": type(exc).__name__},
        )
        await deny(CLOSE_INTERNAL_ERROR, "ssh unavailable")
        return

    try:
        session = registry.create(
            lab_instance_id=instance_id,
            user_id=claims.sub,
            process=process,
            connection=connection,
        )
    except SessionCapReached:
        process.close()
        connection.close()
        await deny(CLOSE_TRY_AGAIN_LATER, "per-lab session limit reached")
        return

    logger.info("terminal_opened", extra={"session_id": session.session_id})
    session.pump_task = asyncio.create_task(_pump(session))
    await websocket.send_text(json.dumps({"type": "session", "session_id": session.session_id}))
    await _run_attached(websocket, session)
