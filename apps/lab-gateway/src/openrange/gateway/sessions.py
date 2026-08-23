"""In-memory terminal session registry with reconnect grace.

Limitations documented in docs/contracts/gateway-api.md: state lives in one
process (single-replica deployments or sticky routing only), and output
produced while no client is attached is buffered up to MAX_BUFFERED_CHUNKS
with oldest-first eviction.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field

import asyncssh

logger = logging.getLogger(__name__)

#: Outbound chunks buffered while detached; each chunk is at most 8 KiB.
MAX_BUFFERED_CHUNKS = 2048


class SessionCapReached(Exception):
    """All concurrent sessions for this lab are attached."""


class SessionUnavailable(Exception):
    """Resume requested for a session that cannot be reattached."""


@dataclass
class TerminalSession:
    """One live SSH PTY plus its reconnect state."""

    session_id: str
    lab_instance_id: str
    user_id: str
    process: asyncssh.SSHClientProcess[bytes]
    connection: asyncssh.SSHClientConnection
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
            logger.warning("terminal_output_dropped", extra={"session_id": self.session_id})

    def resize(self, cols: int, rows: int) -> None:
        self.process.change_terminal_size(width=cols, height=rows)

    def close_nowait(self) -> None:
        """Synchronous close used for eviction paths."""
        self.closed = True
        self.process.close()
        self.connection.close()

    async def aclose(self) -> None:
        """Close the PTY and its transport; the pump task ends on EOF."""
        self.closed = True
        self.process.close()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=5)
        except (TimeoutError, asyncssh.Error):
            logger.warning("terminal_close_timeout", extra={"session_id": self.session_id})
        self.connection.close()


class SessionRegistry:
    """Tracks live sessions per lab instance."""

    def __init__(self, max_per_lab: int, resume_ttl_seconds: float) -> None:
        self.max_per_lab = max_per_lab
        self.resume_ttl_seconds = resume_ttl_seconds
        self._sessions: dict[str, TerminalSession] = {}

    @property
    def sessions(self) -> list[TerminalSession]:
        return list(self._sessions.values())

    def create(
        self,
        *,
        lab_instance_id: str,
        user_id: str,
        process: asyncssh.SSHClientProcess[bytes],
        connection: asyncssh.SSHClientConnection,
        now: float | None = None,
    ) -> TerminalSession:
        """Register a new session, evicting an old detached one if at cap.

        Raises SessionCapReached when every slot is held by an attached
        session; otherwise the oldest detached session is closed to make
        room (a browser reopening should beat a stale grace window).
        """
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
                "terminal_session_evicted",
                extra={"session_id": victim.session_id, "lab_instance_id": lab_instance_id},
            )
            del self._sessions[victim.session_id]
            victim.close_nowait()
        session = TerminalSession(
            session_id=uuid.uuid4().hex,
            lab_instance_id=lab_instance_id,
            user_id=user_id,
            process=process,
            connection=connection,
            queue=asyncio.Queue(MAX_BUFFERED_CHUNKS + 1),
        )
        self._sessions[session.session_id] = session
        return session

    def get_for_resume(
        self, session_id: str, lab_instance_id: str, user_id: str, *, now: float | None = None
    ) -> TerminalSession:
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

    def drop_expired(self, *, now: float) -> list[TerminalSession]:
        """Remove and return sessions past the resume TTL or already dead."""
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


async def reap_loop(registry: SessionRegistry, interval_seconds: float = 5.0) -> None:
    """Background task closing sessions whose grace window has lapsed."""
    while True:
        await asyncio.sleep(interval_seconds)
        for session in registry.drop_expired(now=time.monotonic()):
            logger.info("terminal_session_expired", extra={"session_id": session.session_id})
            await session.aclose()
