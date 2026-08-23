"""Optional OIDC single sign-on for self-hosters.

Enabled when `OPENRANGE_OIDC_ISSUER` (plus client id/secret) is set.
Discovery happens at startup; the flow is standard authorization code.
Provider failures surface as 502s, never as stack traces.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from openrange.api.auth import service
from openrange.api.auth.dependencies import DbSession
from openrange.api.auth.service import AuthError, SessionContext
from openrange.api.config import get_settings
from openrange.api.users.models import User
from sqlalchemy import select

router = APIRouter(prefix="/api/auth/oidc", tags=["auth"])

_state_cookie = "openrange_oidc_state"


def enabled() -> bool:
    settings = get_settings()
    return bool(settings.oidc_issuer and settings.oidc_client_id and settings.oidc_client_secret)


async def _discover() -> dict[str, Any]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(
            f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
        )
        res.raise_for_status()
        return res.json()  # type: ignore[no-any-return]


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    return verifier, challenge


@router.get("/login")
async def oidc_login() -> RedirectResponse:
    if not enabled():
        raise AuthError("oidc is not configured", 404)
    metadata = await _discover()
    verifier, challenge = _pkce_pair()
    settings = get_settings()
    state = secrets.token_urlsafe(24)
    redirect_uri = f"{settings.public_url.rstrip('/')}/api/auth/oidc/callback"
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    import json

    response = RedirectResponse(f"{metadata['authorization_endpoint']}?{httpx.QueryParams(params)}")
    response.set_cookie(
        _state_cookie,
        json.dumps({"state": state, "verifier": verifier}),
        httponly=True,
        samesite="lax",
        max_age=600,
        secure=settings.env != "dev",
    )
    return response


@router.get("/callback")
async def oidc_callback(
    request: Request, db: DbSession, code: str = "", state: str = ""
) -> RedirectResponse:
    if not enabled():
        raise AuthError("oidc is not configured", 404)
    import json

    raw = request.cookies.get(_state_cookie)
    if not raw or not state:
        raise AuthError("missing oidc state", 400)
    stored = json.loads(raw)
    if state != stored["state"]:
        raise AuthError("oidc state mismatch", 400)
    metadata = await _discover()
    settings = get_settings()
    redirect_uri = f"{settings.public_url.rstrip('/')}/api/auth/oidc/callback"
    async with httpx.AsyncClient(timeout=10) as client:
        token_res = await client.post(
            metadata["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
                "code_verifier": stored["verifier"],
            },
        )
        token_res.raise_for_status()
        access_token = token_res.json()["access_token"]
        userinfo_res = await client.get(
            metadata["userinfo_endpoint"],
            headers={"authorization": f"Bearer {access_token}"},
        )
        userinfo_res.raise_for_status()
        userinfo = userinfo_res.json()

    sub = str(userinfo.get("sub", ""))
    email = userinfo.get("email")
    preferred = userinfo.get("preferred_username") or (
        email.split("@")[0] if email else f"oidc-{sub[:8]}"
    )
    if not sub:
        raise AuthError("oidc provider returned no subject", 502)

    from openrange.api.users.models import ApiToken  # noqa: F401 - future machine auth

    base_name = "".join(c for c in preferred if c.isalnum() or c in "._-")[:24] or f"oidc{sub[:6]}"
    candidate = base_name
    for attempt in range(1, 50):
        existing = (
            await db.execute(select(User).where(User.username == candidate))
        ).scalar_one_or_none()
        if existing is None:
            break
        candidate = f"{base_name}-{attempt}"
    else:
        raise AuthError("could not allocate username", 502)
    user = (await db.execute(select(User).where(User.username == candidate))).scalar_one_or_none()
    if user is None:
        user = await service.create_user(
            db,
            username=candidate,
            password=None,
            email=email,
            roles=("learner",),
        )
    if user is None or user.deleted_at is not None:
        raise AuthError("account unavailable", 403)
    _session, raw_token = await service.start_session(db, settings, user, SessionContext())
    response = RedirectResponse(settings.public_url, status_code=303)
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        httponly=True,
        secure=settings.env != "dev",
        samesite="strict",
        path="/",
        max_age=settings.session_lifetime_minutes * 60,
    )
    response.delete_cookie(_state_cookie, path="/")
    return response
