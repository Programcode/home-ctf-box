"""Request authentication: session cookie plus CSRF, and API tokens."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from openrange.api.auth.service import AuthError, resolve_session
from openrange.api.auth.tokens import constant_time_equals
from openrange.api.db import get_session
from openrange.api.users.models import AuthSession, User
from sqlalchemy.ext.asyncio import AsyncSession

DbSession = Annotated[AsyncSession, Depends(get_session)]


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


async def current_session(
    request: Request,
    db: DbSession,
) -> tuple[User | None, AuthSession | None]:
    raw_cookie = request.cookies.get("openrange_session")
    raw = raw_cookie or _bearer_token(request)
    if not raw:
        return None, None
    session = await resolve_session(db, raw)
    if session is None:
        return None, None
    # Cookie-authenticated mutations must present the matching CSRF token.
    # Bearer-token clients (no cookie) are exempt by design.
    if (
        raw_cookie
        and request.method not in {"GET", "HEAD", "OPTIONS"}
        and not constant_time_equals(session.csrf_token, request.headers.get("x-csrf-token", ""))
    ):
        raise AuthError("csrf validation failed", 403)
    user = session.user
    return user, session


async def get_current_user(
    deps: Annotated[tuple[User | None, AuthSession | None], Depends(current_session)],
) -> User:
    user, session = deps
    if user is None or session is None or not user.is_active or user.deleted_at is not None:
        raise AuthError("authentication required", 401)
    if session.mfa_pending:
        raise AuthError("second factor required", 403)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    deps: Annotated[tuple[User | None, AuthSession | None], Depends(current_session)],
) -> User | None:
    user, session = deps
    if user is not None and session is not None and session.mfa_pending:
        return None
    if user is not None and (not user.is_active or user.deleted_at is not None):
        return None
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_permission(
    permission: str,
) -> Callable[..., Awaitable[User]]:
    async def dependency(
        request: Request,
        deps: Annotated[tuple[User | None, AuthSession | None], Depends(current_session)],
    ) -> User:
        user, session = deps
        if (
            user is None
            or session is None
            or not user.is_active
            or user.deleted_at is not None
            or session.mfa_pending
        ):
            raise AuthError("authentication required", 401)
        # CSRF is enforced in current_session; here we only check permission.
        if not user.has_permission(permission):
            raise AuthError(f"missing permission {permission}", 403)
        return user

    return dependency
