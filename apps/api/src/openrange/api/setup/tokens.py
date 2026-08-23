"""Process-local storage for the one-time setup token.

The raw token lives only in API process memory: never in the database,
never on disk. A restart invalidates it, which is safe because issuing
a new one requires the same privileged position. Multi-worker
deployments should run the wizard through a single worker (the installer
does exactly that) or pass --workers 1 until setup completes.
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_raw_token: str | None = None


def store_setup_token(raw: str | None) -> None:
    global _raw_token
    with _lock:
        _raw_token = raw


def get_pending_setup_token() -> str | None:
    with _lock:
        return _raw_token
