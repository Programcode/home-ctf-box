"""Redis-backed sliding-window rate limiting.

Applied to authentication endpoints where brute force is cheapest.
If Redis is unreachable the limiter fails open and logs an error:
availability of login is preserved, and lockout/backoff still applies
through the database path.
"""

from __future__ import annotations

import logging
import os

from fastapi import Request
from openrange.api.config import get_settings
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_client: Redis | None = None


def _redis() -> Redis:
    global _client
    if _client is None:
        settings = get_settings()
        url = os.environ.get("OPENRANGE_REDIS_URL", settings.redis_url)
        _client = Redis.from_url(url, decode_responses=True)
    return _client


async def check_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int) -> bool:
    """Returns True when the request is allowed."""
    ident = request.client.host if request.client else "unknown"
    key = f"ratelimit:{bucket}:{ident}"
    try:
        client = _redis()
        async with client.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            count, _ = await pipe.execute()
        return int(count) <= limit
    except Exception as exc:  # pragma: no cover - depends on live redis
        logger.error("rate limiter unavailable (%s); failing open", exc)
        return True
