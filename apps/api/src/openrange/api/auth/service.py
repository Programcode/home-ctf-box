"""Authentication and session service.

Every flow here is covered by integration tests in
`apps/api/tests/test_auth_flows.py`. Change a rule there first.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pyotp
from openrange.api.auth.passwords import (
    PasswordPolicyError,
    hash_password,
    validate_password_strength,
    validate_username,
    verify_password,
)
from openrange.api.auth.tokens import generate_token, hash_token
from openrange.api.config import ApiSettings
from openrange.api.rbac import ROLE_DEFINITIONS
from openrange.api.users.models import (
    AuthSession,
    EmailVerification,
    LoginAttempt,
    MfaFactor,
    PasswordReset,
    RecoveryCode,
    Role,
    User,
    UserRole,
)
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class AuthError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(slots=True)
class SessionContext:
    ip_address: str = ""
    user_agent: str = ""


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def seed_roles(db: AsyncSession) -> None:
    """Idempotently ensure every defined role exists with its permissions."""
    existing = (await db.execute(select(Role))).scalars().all()
    by_name = {r.name: r for r in existing}
    for name, definition in ROLE_DEFINITIONS.items():
        role = by_name.get(name)
        perms = " ".join(definition.permissions)
        if role is None:
            db.add(Role(name=name, description=definition.description, permissions=perms))
        elif role.permissions != perms:
            role.permissions = perms
            role.description = definition.description
    await db.flush()


async def user_count(db: AsyncSession) -> int:
    return (await db.execute(select(func.count()).select_from(User))).scalar_one()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    username: str,
    password: str | None,
    email: str | None = None,
    roles: tuple[str, ...] = ("learner",),
) -> User:
    try:
        clean_username = validate_username(username)
    except PasswordPolicyError as exc:
        raise AuthError(str(exc)) from exc
    if password is not None:
        try:
            validate_password_strength(password, clean_username)
        except PasswordPolicyError as exc:
            raise AuthError(str(exc)) from exc
    dup = await db.execute(select(User.id).where(User.username == clean_username))
    if dup.scalar_one_or_none() is not None:
        raise AuthError("username taken")
    if email:
        dup_email = await db.execute(select(User.id).where(User.email == email))
        if dup_email.scalar_one_or_none() is not None:
            raise AuthError("email already in use")
    user = User(
        username=clean_username,
        email=email,
        password_hash=hash_password(password) if password else None,
    )
    db.add(user)
    await db.flush()
    for role_name in roles:
        role_id = await _role_id(db, role_name)
        db.add(UserRole(user_id=user.id, role_id=role_id))
    await db.flush()
    return user


async def _role_id(db: AsyncSession, name: str) -> uuid.UUID:
    role = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
    if role is None:
        await seed_roles(db)
        role = (await db.execute(select(Role).where(Role.name == name))).scalar_one()
    assert role is not None
    return role.id


async def start_session(
    db: AsyncSession,
    settings: ApiSettings,
    user: User,
    ctx: SessionContext,
    *,
    mfa_pending: bool = False,
) -> tuple[AuthSession, str]:
    raw_token = generate_token(32)
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_token=generate_token(24),
        ip_address=ctx.ip_address[:64],
        user_agent=ctx.user_agent[:256],
        expires_at=_utcnow() + timedelta(minutes=settings.session_lifetime_minutes),
        mfa_pending=mfa_pending,
    )
    db.add(session)
    await db.flush()
    return session, raw_token


async def resolve_session(db: AsyncSession, raw_token: str) -> AuthSession | None:
    session = (
        await db.execute(
            select(AuthSession)
            .options(
                selectinload(AuthSession.user).selectinload(User.roles).selectinload(UserRole.role)
            )
            .where(AuthSession.token_hash == hash_token(raw_token))
        )
    ).scalar_one_or_none()
    if session is None or not session.is_live:
        return None
    return session


async def revoke_session(db: AsyncSession, session: AuthSession) -> None:
    session.revoked_at = _utcnow()


async def record_login_attempt(
    db: AsyncSession, username: str, ctx: SessionContext, succeeded: bool
) -> None:
    """Record in its own transaction: the signal must survive the failed
    request whose rollback would otherwise erase it."""
    from openrange.api.db import session_factory

    assert session_factory is not None
    async with session_factory() as audit_db:
        audit_db.add(
            LoginAttempt(
                username_tried=username[:64], ip_address=ctx.ip_address[:64], succeeded=succeeded
            )
        )
        await audit_db.commit()


async def is_locked_out(
    db: AsyncSession, settings: ApiSettings, username: str, ctx: SessionContext
) -> bool:
    since = _utcnow() - timedelta(minutes=settings.login_lockout_minutes)
    fails = await db.execute(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.attempted_at >= since,
            (LoginAttempt.username_tried == username) | (LoginAttempt.ip_address == ctx.ip_address),
        )
    )
    return int(fails.scalar_one()) >= settings.login_max_attempts


async def attempt_login(
    db: AsyncSession, settings: ApiSettings, *, username: str, password: str, ctx: SessionContext
) -> tuple[User, AuthSession, str]:
    if await is_locked_out(db, settings, username, ctx):
        raise AuthError("too many attempts; wait before retrying", 429)
    user = await get_user_by_username(db, username)
    ok = verify_password(user.password_hash if user else None, password)
    await record_login_attempt(db, username, ctx, ok)
    if not ok or user is None or not user.is_active or user.deleted_at is not None:
        raise AuthError("invalid credentials", 401)

    has_totp = (
        await db.execute(
            select(MfaFactor).where(
                MfaFactor.user_id == user.id,
                MfaFactor.type == "totp",
                MfaFactor.confirmed_at.is_not(None),
            )
        )
    ).scalar_one_or_none() is not None
    session, raw_token = await start_session(db, settings, user, ctx, mfa_pending=has_totp)
    user.last_seen_at = _utcnow()
    await db.flush()
    return user, session, raw_token


async def complete_mfa_login(db: AsyncSession, session: AuthSession, code: str) -> bool:
    factor = (
        await db.execute(
            select(MfaFactor).where(
                MfaFactor.user_id == session.user_id,
                MfaFactor.type == "totp",
                MfaFactor.confirmed_at.is_not(None),
            )
        )
    ).scalar_one_or_none()
    if factor is None or not factor.secret_encrypted:
        return False
    totp = pyotp.TOTP(factor.secret_encrypted)
    valid = totp.verify(code.replace(" ", ""), valid_window=1)
    if valid:
        session.mfa_pending = False
        factor.last_used_at = _utcnow()
        await db.flush()
    return valid


async def use_recovery_code(db: AsyncSession, user_id: uuid.UUID, code: str) -> bool:
    rows = (
        (
            await db.execute(
                select(RecoveryCode).where(
                    RecoveryCode.user_id == user_id, RecoveryCode.used_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        if verify_recovery_code(row.code_hash, code):
            row.used_at = _utcnow()
            await db.flush()
            return True
    return False


def recovery_code_hash(code: str) -> str:
    import hashlib

    return hashlib.sha256(code.encode()).hexdigest()


def verify_recovery_code(stored_hash: str, code: str) -> bool:
    import hashlib

    return secrets.compare_digest(hashlib.sha256(code.encode()).hexdigest(), stored_hash)


async def setup_totp(db: AsyncSession, user: User) -> str:
    secret = pyotp.random_base32()
    existing = (
        await db.execute(
            select(MfaFactor).where(MfaFactor.user_id == user.id, MfaFactor.type == "totp")
        )
    ).scalar_one_or_none()
    if existing:
        existing.secret_encrypted = secret
        existing.confirmed_at = None
    else:
        db.add(MfaFactor(user_id=user.id, type="totp", secret_encrypted=secret))
    await db.flush()
    return secret


async def confirm_totp(db: AsyncSession, user: User, code: str) -> list[str] | None:
    factor = (
        await db.execute(
            select(MfaFactor).where(MfaFactor.user_id == user.id, MfaFactor.type == "totp")
        )
    ).scalar_one_or_none()
    if factor is None or not factor.secret_encrypted:
        raise AuthError("no pending TOTP enrollment", 409)
    if not pyotp.TOTP(factor.secret_encrypted).verify(code, valid_window=1):
        return None
    factor.confirmed_at = _utcnow()
    codes = [secrets.token_hex(5) for _ in range(8)]
    await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    for c in codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=recovery_code_hash(c)))
    await db.flush()
    return codes


async def disable_totp(db: AsyncSession, user: User, code: str) -> bool:
    factor = (
        await db.execute(
            select(MfaFactor).where(
                MfaFactor.user_id == user.id,
                MfaFactor.type == "totp",
                MfaFactor.confirmed_at.is_not(None),
            )
        )
    ).scalar_one_or_none()
    if factor is None or not factor.secret_encrypted:
        return False
    if not pyotp.TOTP(factor.secret_encrypted).verify(code, valid_window=1):
        return False
    await db.delete(factor)
    await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    await db.flush()
    return True


async def request_password_reset(
    db: AsyncSession, settings: ApiSettings, *, username: str, ctx: SessionContext
) -> str | None:
    """Create a single-use reset token. Returns the token so delivery can be
    handled by the notification layer; returns None for unknown users so we
    do not leak account existence."""
    user = await get_user_by_username(db, username)
    if user is None or user.deleted_at is not None:
        return None
    token = generate_token(32)
    db.add(
        PasswordReset(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=_utcnow() + timedelta(hours=1),
            requested_ip=ctx.ip_address[:64],
        )
    )
    await db.flush()
    return token


async def complete_password_reset(db: AsyncSession, *, token: str, new_password: str) -> bool:
    row = (
        await db.execute(
            select(PasswordReset).where(
                PasswordReset.token_hash == hash_token(token), PasswordReset.used_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if row is None or row.expires_at < _utcnow():
        return False
    user = await db.get(User, row.user_id)
    if user is None:
        return False
    try:
        validate_password_strength(new_password, user.username)
    except PasswordPolicyError as exc:
        raise AuthError(str(exc)) from exc
    user.password_hash = hash_password(new_password)
    row.used_at = _utcnow()
    # A reset revokes every live session: the credential changed.
    sessions = (
        await db.execute(select(AuthSession).where(AuthSession.user_id == user.id))
    ).scalars()
    for s in sessions:
        s.revoked_at = s.revoked_at or _utcnow()
    await db.flush()
    return True


async def change_password(db: AsyncSession, user: User, *, current: str, new_password: str) -> bool:
    if not verify_password(user.password_hash, current):
        return False
    try:
        validate_password_strength(new_password, user.username)
    except PasswordPolicyError as exc:
        raise AuthError(str(exc)) from exc
    user.password_hash = hash_password(new_password)
    await db.flush()
    return True


async def request_email_verification(db: AsyncSession, settings: ApiSettings, user: User) -> str:
    token = generate_token(32)
    db.add(
        EmailVerification(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=_utcnow() + timedelta(days=2),
        )
    )
    await db.flush()
    return token


async def confirm_email_verification(db: AsyncSession, token: str) -> bool:
    row = (
        await db.execute(
            select(EmailVerification).where(
                EmailVerification.token_hash == hash_token(token),
                EmailVerification.used_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None or row.expires_at < _utcnow():
        return False
    user = await db.get(User, row.user_id)
    if user is None:
        return False
    user.email_verified_at = _utcnow()
    row.used_at = _utcnow()
    await db.flush()
    return True


async def export_account(db: AsyncSession, user: User) -> dict[str, object]:
    """Privacy export: everything the platform stores about the caller."""
    sessions = (
        (await db.execute(select(AuthSession).where(AuthSession.user_id == user.id)))
        .scalars()
        .all()
    )
    return {
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "bio": user.bio,
            "created_at": user.created_at.isoformat(),
            "email_verified_at": user.email_verified_at.isoformat()
            if user.email_verified_at
            else None,
            "leaderboard_opt_out": user.leaderboard_opt_out,
        },
        "roles": [r.role.name if r.role else "?" for r in user.roles],
        "active_sessions": len([s for s in sessions if s.is_live]),
        "total_sessions": len(sessions),
    }


async def begin_account_deletion(db: AsyncSession, user: User) -> None:
    user.deleted_at = _utcnow()
    user.is_active = False
    sessions = (
        await db.execute(select(AuthSession).where(AuthSession.user_id == user.id))
    ).scalars()
    for s in sessions:
        s.revoked_at = s.revoked_at or _utcnow()
    anonymize = f"deleted-{user.id}"
    user.username = anonymize[:32]
    user.email = None
    user.display_name = ""
    user.bio = ""
    user.password_hash = None
    await db.flush()


async def grant_role(db: AsyncSession, user: User, role_name: str) -> None:
    if role_name not in ROLE_DEFINITIONS:
        raise AuthError(f"unknown role {role_name}", 422)
    role_id = await _role_id(db, role_name)
    exists = (
        await db.execute(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role_id)
        )
    ).scalar_one_or_none()
    if exists is None:
        db.add(UserRole(user_id=user.id, role_id=role_id))
        await db.flush()


async def list_sessions_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[AuthSession]:
    rows = (
        (
            await db.execute(
                select(AuthSession)
                .where(AuthSession.user_id == user_id)
                .order_by(AuthSession.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def revoke_session_by_id(db: AsyncSession, user_id: uuid.UUID, session_id: str) -> None:
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise AuthError("unknown session", 404) from exc
    row = (
        await db.execute(
            select(AuthSession).where(AuthSession.id == sid, AuthSession.user_id == user_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise AuthError("unknown session", 404)
    row.revoked_at = _utcnow()
    await db.flush()
