"""Request correlation, security headers, and auth-endpoint rate limits."""

from __future__ import annotations

import uuid

from fastapi import Request, Response
from openrange.api.auth.ratelimit import check_rate_limit
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# bucket -> (limit, window seconds)
_AUTH_LIMITS: dict[str, tuple[int, int]] = {
    "/api/auth/login": (20, 300),
    "/api/auth/register": (10, 3600),
    "/api/auth/password/reset-request": (5, 3600),
    "/api/auth/mfa/verify": (20, 300),
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers.setdefault("x-content-type-options", "nosniff")
        response.headers.setdefault("x-frame-options", "DENY")
        response.headers.setdefault("referrer-policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "content-security-policy", "default-src 'none'; frame-ancestors 'none'"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rule = _AUTH_LIMITS.get(request.url.path)
        if rule is not None and request.method == "POST":
            limit, window = rule
            allowed = await check_rate_limit(request, request.url.path, limit, window)
            if not allowed:
                return Response(
                    content='{"type":"about:blank","title":"Too Many Requests",'
                    '"status":429,"detail":"rate limit exceeded"}',
                    status_code=429,
                    media_type="application/problem+json",
                    headers={"retry-after": str(window)},
                )
        return await call_next(request)
