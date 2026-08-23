"""Outbox drainer: background loop that dispatches queued email rows.

Runs at most ``batch_size`` rows per pass every ``interval_seconds``
(defaults: 20 rows / 30s). Failures increment ``attempts``, record
``last_error``, and push ``next_attempt_at`` forward on an exponential
backoff (30s base, 15m cap); after ``max_attempts`` the row is parked as
``failed`` for ops inspection via /admin/email-outbox.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from openrange.api import db as dbmodule
from openrange.api.notifications.email import DevNullSender, EmailSender
from openrange.api.notifications.models import EmailOutbox
from sqlalchemy import or_, select

logger = logging.getLogger(__name__)

_BACKOFF_BASE_SECONDS = 30.0
_BACKOFF_CAP_SECONDS = 900.0


def _backoff(attempts: int) -> timedelta:
    seconds = min(_BACKOFF_BASE_SECONDS * (2**attempts), _BACKOFF_CAP_SECONDS)
    return timedelta(seconds=seconds)


class OutboxDrainer:
    def __init__(
        self,
        *,
        sender: EmailSender | None = None,
        interval_seconds: float = 30.0,
        batch_size: int = 20,
        max_attempts: int = 5,
    ) -> None:
        self.sender = sender
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self.max_attempts = max_attempts
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self.sender is None:
            self.sender = DevNullSender()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="outbox-drainer")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            try:
                drained = await self.drain_once()
                if drained:
                    logger.info("drained %d email outbox rows", drained)
            except Exception:  # pragma: no cover - loop must survive anything
                logger.exception("email outbox drain pass failed")
            await asyncio.sleep(self.interval_seconds)

    async def drain_once(self, sender: EmailSender | None = None) -> int:
        """Process one batch; returns rows processed.

        Accepts an explicit sender override so tests can inject fakes.
        """
        active = sender or self.sender or DevNullSender()
        # Read through the module so engine re-init between loops/tests
        # is picked up instead of a stale import-time binding.
        if dbmodule.session_factory is None:
            dbmodule.init_engine()
        assert dbmodule.session_factory is not None
        processed = 0
        async with dbmodule.session_factory() as db:
            now = datetime.now(UTC)
            rows = (
                (
                    await db.execute(
                        select(EmailOutbox)
                        .where(
                            EmailOutbox.status == "queued",
                            or_(
                                EmailOutbox.next_attempt_at.is_(None),
                                EmailOutbox.next_attempt_at <= now,
                            ),
                        )
                        .order_by(EmailOutbox.created_at)
                        .limit(self.batch_size)
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                try:
                    await active.send(
                        to_email=row.to_email, subject=row.subject, body_text=row.body_text
                    )
                except Exception as exc:
                    row.attempts += 1
                    row.last_error = f"{exc.__class__.__name__}: {exc}"[:2000]
                    if row.attempts >= self.max_attempts:
                        row.status = "failed"
                    else:
                        row.next_attempt_at = datetime.now(UTC) + _backoff(row.attempts)
                else:
                    row.status = "sent"
                    row.sent_at = datetime.now(UTC)
                    row.last_error = ""
                processed += 1
            await db.commit()
        return processed
