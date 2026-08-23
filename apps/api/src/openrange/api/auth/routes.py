"""Auth HTTP routes: /api/auth and /api/users/me."""

from __future__ import annotations

from datetime import UTC, datetime

import pyotp
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openrange.api.auth import service
from openrange.api.auth.dependencies import CurrentUser, DbSession, current_session
from openrange.api.auth.service import AuthError, SessionContext
from openrange.api.config import get_settings
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])
me = APIRouter(prefix="/api/users/me", tags=["users"])


def _ctx(request: Request) -> SessionContext:
    return SessionContext(
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )


def _session_response(
    body: dict[str, object],
    raw_token: str | None,
    csrf: str | None,
    status_code: int = 200,
) -> JSONResponse:
    settings = get_settings()
    response = JSONResponse(body, status_code=status_code)
    if raw_token:
        response.set_cookie(
            settings.session_cookie_name,
            raw_token,
            httponly=True,
            secure=settings.env != "dev",
            samesite="strict",
            path="/",
            max_age=settings.session_lifetime_minutes * 60,
        )
    if csrf:
        # Readable by the app to echo the token back in headers.
        response.set_cookie(
            settings.csrf_cookie_name,
            csrf,
            samesite="strict",
            secure=settings.env != "dev",
            path="/",
        )
    return response


class RegisterIn(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


class CodeIn(BaseModel):
    code: str


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str


class PasswordResetRequestIn(BaseModel):
    username: str


class PasswordResetCompleteIn(BaseModel):
    token: str
    new_password: str


@router.post("/register", status_code=201)
async def register(payload: RegisterIn, db: DbSession) -> JSONResponse:
    settings = get_settings()
    user = await service.create_user(
        db,
        username=payload.username,
        password=payload.password,
        email=payload.email,
        roles=("learner",),
    )
    session, raw_token = await service.start_session(
        db, settings, user, SessionContext(), mfa_pending=False
    )
    return _session_response(
        {
            "id": str(user.id),
            "username": user.username,
            "mfa_pending": False,
            "csrf_token": session.csrf_token,
        },
        raw_token,
        session.csrf_token,
        status_code=201,
    )


@router.post("/login")
async def login(payload: LoginIn, request: Request, db: DbSession) -> JSONResponse:
    settings = get_settings()
    user, session, raw_token = await service.attempt_login(
        db,
        settings,
        username=payload.username.strip(),
        password=payload.password,
        ctx=_ctx(request),
    )
    return _session_response(
        {
            "id": str(user.id),
            "username": user.username,
            "mfa_pending": session.mfa_pending,
            "csrf_token": session.csrf_token,
        },
        raw_token,
        session.csrf_token,
    )


@router.post("/logout")
async def logout(request: Request, db: DbSession) -> JSONResponse:
    _, session = await current_session(request, db)
    if session is not None:
        await service.revoke_session(db, session)
    response = JSONResponse({"ok": True})
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return response


@router.post("/mfa/verify")
async def mfa_verify(payload: CodeIn, request: Request, db: DbSession) -> dict[str, object]:
    user, session = await current_session(request, db)
    if user is None or session is None:
        raise AuthError("authentication required", 401)
    ok = await service.complete_mfa_login(db, session, payload.code)
    if not ok:
        ok = await service.use_recovery_code(db, user.id, payload.code)
    if not ok:
        raise AuthError("invalid second factor", 401)
    return {"mfa_pending": False}


@me.get("")
async def whoami(user: CurrentUser) -> dict[str, object]:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "email_verified": user.email_verified_at is not None,
        "leaderboard_opt_out": user.leaderboard_opt_out,
        "permissions": sorted({p for r in user.roles if r.role for p in r.role.permissions_list}),
    }


class ProfileIn(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    leaderboard_opt_out: bool | None = None


@me.patch("")
async def update_profile(payload: ProfileIn, user: CurrentUser, db: DbSession) -> dict[str, object]:
    if payload.display_name is not None:
        user.display_name = payload.display_name[:64]
    if payload.bio is not None:
        user.bio = payload.bio[:2000]
    if payload.leaderboard_opt_out is not None:
        user.leaderboard_opt_out = payload.leaderboard_opt_out
    await db.flush()
    return {"updated": True}


@me.post("/mfa/totp")
async def enroll_totp(user: CurrentUser, db: DbSession) -> dict[str, str]:
    secret = await service.setup_totp(db, user)
    label = f"OpenRange:{user.username}"
    return {
        "secret": secret,
        "otpauth_url": pyotp.totp.TOTP(secret).provisioning_uri(
            name=label, issuer_name="OpenRange"
        ),
    }


@me.post("/mfa/totp/confirm")
async def confirm_totp(payload: CodeIn, user: CurrentUser, db: DbSession) -> dict[str, list[str]]:
    codes = await service.confirm_totp(db, user, payload.code)
    if codes is None:
        raise AuthError("code did not match; restart enrollment", 400)
    return {"recovery_codes": codes}


@me.delete("/mfa/totp")
async def remove_totp(payload: CodeIn, user: CurrentUser, db: DbSession) -> dict[str, bool]:
    ok = await service.disable_totp(db, user, payload.code)
    if not ok:
        raise AuthError("invalid code or TOTP not enabled", 400)
    return {"disabled": True}


@me.get("/sessions")
async def list_sessions(user: CurrentUser, db: DbSession) -> list[dict[str, object]]:
    rows = await service.list_sessions_for_user(db, user.id)
    now = datetime.now(UTC)
    return [
        {
            "id": str(s.id),
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "live": s.revoked_at is None and s.expires_at > now,
        }
        for s in rows
    ]


@me.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, user: CurrentUser, db: DbSession) -> dict[str, bool]:
    await service.revoke_session_by_id(db, user.id, session_id)
    return {"revoked": True}


@me.post("/password")
async def change_password(
    payload: PasswordChangeIn, user: CurrentUser, db: DbSession
) -> dict[str, bool]:
    ok = await service.change_password(
        db, user, current=payload.current_password, new_password=payload.new_password
    )
    if not ok:
        raise AuthError("current password incorrect", 403)
    return {"changed": True}


class EmailRequestIn(BaseModel):
    email: str


@me.post("/email/verify-request")
async def request_email_verification(
    payload: EmailRequestIn | None, user: CurrentUser, db: DbSession
) -> dict[str, bool]:
    target = payload.email if payload else user.email
    if not target:
        raise AuthError("no email on file", 422)
    user.email = target
    user.email_verified_at = None
    await service.request_email_verification(db, get_settings(), user)
    # Delivery goes through the notification layer; the API never returns
    # the token to the client.
    return {"requested": True}


@router.post("/email/confirm")
async def confirm_email(payload: CodeIn, db: DbSession) -> dict[str, bool]:
    ok = await service.confirm_email_verification(db, payload.code)
    if not ok:
        raise AuthError("invalid or expired verification token", 400)
    return {"verified": True}


@router.post("/password/reset-request")
async def password_reset_request(
    payload: PasswordResetRequestIn, request: Request, db: DbSession
) -> dict[str, bool]:
    # Uniform response whether or not the account exists.
    await service.request_password_reset(
        db, get_settings(), username=payload.username.strip(), ctx=_ctx(request)
    )
    return {"requested": True}


@router.post("/password/reset")
async def password_reset_complete(
    payload: PasswordResetCompleteIn, db: DbSession
) -> dict[str, bool]:
    ok = await service.complete_password_reset(
        db, token=payload.token, new_password=payload.new_password
    )
    if not ok:
        raise AuthError("invalid or expired reset token", 400)
    return {"reset": True}


@me.get("/export")
async def export_account(user: CurrentUser, db: DbSession) -> dict[str, object]:
    return await service.export_account(db, user)


@me.post("/delete")
async def delete_account(user: CurrentUser, db: DbSession) -> dict[str, bool]:
    await service.begin_account_deletion(db, user)
    return {"deletion_started": True}
