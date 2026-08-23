"""Email dispatch abstraction.

Design choice (documented per plan): stdlib ``smtplib`` executed through
``asyncio.to_thread`` instead of aiosmtplib. The outbox drain path sends
at most one small batch every 30s, so SMTP pipelining/async concurrency
buys nothing, and skipping aiosmtplib keeps the dependency tree flat.
Configuration travels through the shared Settings env prefix:
OPENRANGE_SMTP_HOST / OPENRANGE_SMTP_PORT / OPENRANGE_SMTP_TLS /
OPENRANGE_SMTP_FROM. Sending stays off unless OPENRANGE_SMTP_ENABLED is
truthy, so dev stacks default to DevNullSender and never send mail.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Protocol

from openrange.api.config import get_settings

logger = logging.getLogger(__name__)

SMTP_ENABLED_ENV = "OPENRANGE_SMTP_ENABLED"


class EmailSender(Protocol):
    async def send(self, *, to_email: str, subject: str, body_text: str) -> None: ...


class DevNullSender:
    """Default sender: accepts messages and drops them."""

    async def send(self, *, to_email: str, subject: str, body_text: str) -> None:
        logger.debug("devnull email to %s: %s", to_email, subject)


class SmtpSender:
    def __init__(self, *, host: str, port: int, use_tls: bool, from_addr: str) -> None:
        self._host = host
        self._port = port
        self._use_tls = use_tls
        self._from_addr = from_addr

    async def send(self, *, to_email: str, subject: str, body_text: str) -> None:
        await asyncio.to_thread(self._send_sync, to_email, subject, body_text)

    def _send_sync(self, to_email: str, subject: str, body_text: str) -> None:
        message = EmailMessage()
        message["From"] = self._from_addr
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body_text)
        with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
            if self._use_tls:
                smtp.starttls()
            smtp.send_message(message)


def sender_from_settings() -> EmailSender:
    settings = get_settings()
    enabled = os.environ.get(SMTP_ENABLED_ENV, "").strip().lower() in {"1", "true", "yes"}
    if not enabled:
        return DevNullSender()
    return SmtpSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        use_tls=settings.smtp_tls,
        from_addr=settings.smtp_from,
    )
