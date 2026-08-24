"""WebSocket-to-TCP desktop bridge (VNC/RFB) plus VPN heartbeat reporting.

Protocol (after the WebSocket opens), mirroring the terminal bridge:
- The gateway immediately sends ``{"type":"session","session_id":"..."}``.
- Binary frames pass verbatim between browser and the instance's RFB
  port; RFB negotiates its own resolution, so no resize control exists.
- Text frames are control JSON: ``{"type":"close"}`` ends the session.
- Reconnect: reopen with ``?resume=<session-id>`` within the grace TTL to
  reattach to the live TCP stream.

The target port defaults to 5900 and may be overridden with ``?port=``,
but only when the token explicitly allows that port on its lab
(``ports`` claim), exactly like the HTTP proxy. Close codes match the
terminal bridge: 1000 normal, 1008 policy violation, 1011 upstream
failure, 1013 concurrency cap reached.

The VPN heartbeat client reports live device public keys to the API's
``POST /internal/vpn/heartbeat`` using the shared gateway secret with
runner-style HMAC headers. A later WireGuard peer watcher invokes it;
the client ships now so deployment wiring is stable.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol

import httpx
from fastapi import APIRouter, WebSocket
from openrange.gateway.config import GatewaySettings
from openrange.gateway.runner import InstanceNotFoundError, RunnerUnavailableError
from openrange.gateway.sessions import SessionCapReached, SessionUnavailable
from openrange.gateway.terminal import (
    CLOSE_INTERNAL_ERROR,
    CLOSE_POLICY_VIOLATION,
    CLOSE_TRY_AGAIN_LATER,
)
from openrange.gateway.tokens import TokenError, verify_token
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_VNC_PORT = 5900
_CONNECT_TIMEOUT_SECONDS = 10.0

#: Outbound chunks buffered while detached; each chunk is at most 8 KiB.
MAX_BUFFERED_CHUNKS = 2048


@dataclass
class DesktopSession:
    """One live TCP connection into a lab's RFB port plus reconnect state."""

    session_id: str
    lab_instance_id: str
    user_id: str
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    queue: asyncio.Queue[bytes | None]
    created_at: float = field(default_factory=time.monotonic)
    detached_at: float | None = None
    attached: bool = False
    closed: bool = False
    pump_task: asyncio.Task[None] | None = None

    def offer(self, chunk: bytes | None) -> None:
        """Queue outbound data; when full, drop the oldest chunk."""
        if chunk is not None:
            while self.queue.qsize() >= MAX_BUFFERED_CHUNKS:
                try:
                    self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        try:
            self.queue.put_nowait(chunk)
        except asyncio.QueueFull:
            logger.warning("desktop_output_dropped", extra={"session_id": self.session_id})

    def close_nowait(self) -> None:
        """Synchronous close used for eviction paths."""
        self.closed = True
        self.writer.close()

    async def aclose(self) -> None:
        self.closed = True
        self.writer.close()
        with contextlib.suppress(OSError):
            await asyncio.wait_for(self.writer.wait_closed(), timeout=5)


class DesktopRegistry:
    """Tracks live desktop sessions per lab instance."""

    def __init__(self, max_per_lab: int, resume_ttl_seconds: float) -> None:
        self.max_per_lab = max_per_lab
        self.resume_ttl_seconds = resume_ttl_seconds
        self._sessions: dict[str, DesktopSession] = {}

    @property
    def sessions(self) -> list[DesktopSession]:
        return list(self._sessions.values())

    def create(
        self,
        *,
        lab_instance_id: str,
        user_id: str,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        now: float | None = None,
    ) -> DesktopSession:
        """Register a new session, evicting an old detached one if at cap."""
        current_time = time.monotonic() if now is None else now
        self.drop_expired(now=current_time)
        same_lab = [s for s in self._sessions.values() if s.lab_instance_id == lab_instance_id]
        if len(same_lab) >= self.max_per_lab:
            evictable = sorted(
                (s for s in same_lab if s.detached_at is not None),
                key=lambda s: s.detached_at or 0.0,
            )
            if not evictable:
                raise SessionCapReached(lab_instance_id)
            victim = evictable[0]
            logger.info(
                "desktop_session_evicted",
                extra={"session_id": victim.session_id, "lab_instance_id": lab_instance_id},
            )
            del self._sessions[victim.session_id]
            victim.close_nowait()
        session = DesktopSession(
            session_id=uuid.uuid4().hex,
            lab_instance_id=lab_instance_id,
            user_id=user_id,
            reader=reader,
            writer=writer,
            queue=asyncio.Queue(MAX_BUFFERED_CHUNKS + 1),
        )
        self._sessions[session.session_id] = session
        return session

    def get_for_resume(
        self, session_id: str, lab_instance_id: str, user_id: str, *, now: float | None = None
    ) -> DesktopSession:
        """Return a reattachable session or raise SessionUnavailable."""
        session = self._sessions.get(session_id)
        # Same error for missing/expired/foreign sessions so existence of a
        # session id is never revealed across labs or users.
        if session is None or session.closed or session.attached:
            raise SessionUnavailable(session_id)
        if session.lab_instance_id != lab_instance_id or session.user_id != user_id:
            raise SessionUnavailable(session_id)
        current_time = time.monotonic() if now is None else now
        detached_at = session.detached_at
        if detached_at is None or current_time - detached_at > self.resume_ttl_seconds:
            raise SessionUnavailable(session_id)
        return session

    def remove(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.close_nowait()

    def drop_expired(self, *, now: float) -> list[DesktopSession]:
        expired = [
            s
            for s in self._sessions.values()
            if s.closed
            or (s.detached_at is not None and now - s.detached_at > self.resume_ttl_seconds)
        ]
        for session in expired:
            del self._sessions[session.session_id]
        return expired

    async def aclose_all(self) -> None:
        for session in list(self._sessions.values()):
            await session.aclose()
        self._sessions.clear()


async def reap_loop(registry: DesktopRegistry, interval_seconds: float = 5.0) -> None:
    """Background task closing sessions whose grace window has lapsed."""
    while True:
        await asyncio.sleep(interval_seconds)
        for session in registry.drop_expired(now=time.monotonic()):
            logger.info("desktop_session_expired", extra={"session_id": session.session_id})
            await session.aclose()


def resolve_desktop_port(raw: str | None) -> int:
    """Resolve the ?port= query value (or the default) to a valid port."""
    port_text = raw if raw is not None else str(DEFAULT_VNC_PORT)
    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("port out of range")
    return port


async def _pump(session: DesktopSession) -> None:
    """Move RFB output into the session queue until the stream ends."""
    try:
        while True:
            chunk = await session.reader.read(8192)
            if not chunk:
                break
            session.offer(chunk)
    except OSError as exc:
        logger.warning(
            "rfb_read_failed",
            extra={"session_id": session.session_id, "error_class": type(exc).__name__},
        )
    finally:
        session.closed = True
        session.offer(None)


async def _inbound(ws: WebSocket, session: DesktopSession) -> bool:
    """Browser -> RFB. Returns True when the client asked for a clean close."""
    while True:
        try:
            message = await ws.receive()
        except WebSocketDisconnect:
            return False
        payload = message.get("bytes")
        text = message.get("text")
        if payload is not None:
            session.writer.write(payload)
            await session.writer.drain()
            continue
        if text is None:
            continue
        try:
            control = json.loads(text)
        except ValueError:
            continue
        if isinstance(control, dict) and control.get("type") == "close":
            return True


async def _outbound(ws: WebSocket, session: DesktopSession) -> bool:
    """RFB -> browser; returns False when the stream hits EOF."""
    while True:
        item = await session.queue.get()
        if item is None:
            return False
        await ws.send_bytes(item)


async def _run_attached(ws: WebSocket, session: DesktopSession) -> None:
    """Run both directions until either side ends; then start the grace window."""
    session.attached = True
    session.detached_at = None
    inbound_task: asyncio.Task[bool] = asyncio.create_task(_inbound(ws, session))
    outbound_task: asyncio.Task[bool] = asyncio.create_task(_outbound(ws, session))
    clean_close = False
    rfb_ended = False
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
                rfb_ended = not outbound_task.result()
            elif task is inbound_task:
                clean_close = inbound_task.result()
    finally:
        session.attached = False
        session.detached_at = time.monotonic()

    if failure is not None:
        logger.warning(
            "desktop_bridge_error",
            extra={"session_id": session.session_id, "error_class": type(failure).__name__},
            exc_info=failure,
        )
        with contextlib.suppress(Exception):
            await ws.close(code=CLOSE_INTERNAL_ERROR, reason="bridge error")
    elif clean_close or rfb_ended:
        with contextlib.suppress(Exception):
            await ws.close(code=1000, reason="session ended")


@router.websocket("/desktop/{instance_id}")
async def desktop_endpoint(websocket: WebSocket, instance_id: str) -> None:
    app_state = websocket.app.state
    settings: GatewaySettings = app_state.settings
    registry: DesktopRegistry = app_state.desktops

    async def deny(code: int, reason: str) -> None:
        logger.info("desktop_denied", extra={"reason": reason})
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

    try:
        port = resolve_desktop_port(websocket.query_params.get("port"))
    except ValueError as exc:
        await deny(CLOSE_POLICY_VIOLATION, str(exc))
        return
    if not claims.allows_port(port):
        await deny(CLOSE_POLICY_VIOLATION, "port not allowed by token")
        return

    resume_id = websocket.query_params.get("resume")
    if resume_id:
        try:
            session = registry.get_for_resume(resume_id, instance_id, claims.sub)
        except SessionUnavailable:
            await deny(CLOSE_POLICY_VIOLATION, "resume unavailable")
            return
        logger.info("desktop_resumed", extra={"session_id": session.session_id})
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
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(address.host, port), timeout=_CONNECT_TIMEOUT_SECONDS
        )
    except (OSError, TimeoutError) as exc:
        logger.warning(
            "rfb_connect_failed",
            extra={"lab_instance_id": instance_id, "error_class": type(exc).__name__},
        )
        await deny(CLOSE_INTERNAL_ERROR, "desktop unavailable")
        return

    try:
        session = registry.create(
            lab_instance_id=instance_id,
            user_id=claims.sub,
            reader=reader,
            writer=writer,
        )
    except SessionCapReached:
        writer.close()
        await deny(CLOSE_TRY_AGAIN_LATER, "per-lab session limit reached")
        return

    logger.info("desktop_opened", extra={"session_id": session.session_id})
    session.pump_task = asyncio.create_task(_pump(session))
    await websocket.send_text(json.dumps({"type": "session", "session_id": session.session_id}))
    await _run_attached(websocket, session)


HEARTBEAT_PATH = "/internal/vpn/heartbeat"


def gateway_auth_headers(
    secret: str, body: bytes = b"", *, now: float | None = None
) -> dict[str, str]:
    """Build gateway HMAC headers over ``f"{ts}:{body}"`` (runner pattern)."""
    timestamp = str(int(time.time() if now is None else now))
    digest = hmac.new(secret.encode(), timestamp.encode() + b":" + body, hashlib.sha256).hexdigest()
    return {"X-Gateway-Timestamp": timestamp, "X-Gateway-Signature": digest}


class VpnHeartbeatClient(Protocol):
    async def beat(self, device_public_key: str) -> bool:
        """Report a live WireGuard device; True when the API accepted it."""
        ...


class HttpVpnHeartbeatClient:
    """Concrete VpnHeartbeatClient speaking to the API over HTTP."""

    def __init__(
        self,
        api_url: str | None = None,
        secret: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = (
            api_url or os.environ.get("OPENRANGE_API_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        self._secret = (
            secret if secret is not None else os.environ.get("OPENRANGE_GATEWAY_SECRET", "")
        )
        self._timeout_seconds = timeout_seconds

    async def beat(self, device_public_key: str) -> bool:
        body = json.dumps({"device_public_key": device_public_key}).encode()
        headers = gateway_auth_headers(self._secret, body)
        headers["content-type"] = "application/json"
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout_seconds
            ) as client:
                response = await client.post(HEARTBEAT_PATH, content=body, headers=headers)
        except httpx.HTTPError:
            return False
        return response.status_code == 200
