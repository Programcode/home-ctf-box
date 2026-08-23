"""Identity models: users, sessions, MFA, tokens, roles.

Security invariants baked into the schema:
- passwords store Argon2id hashes only;
- password-reset and setup tokens are stored hashed with expiry and
  single-use semantics;
- sessions are server-side records so revocation is immediate;
- permissions attach to roles; users hold roles. Endpoint guards check
  permission strings, never role names.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from openrange.api.db.base import Base, Timestamped, UUIDPrimaryKey
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    email_verified_at: Mapped[datetime | None]
    password_hash: Mapped[str | None]  # null for OIDC-only accounts
    display_name: Mapped[str] = mapped_column(String(64), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    leaderboard_opt_out: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None]  # soft delete start of deletion workflow
    last_seen_at: Mapped[datetime | None]

    sessions: Mapped[list[AuthSession]] = relationship(back_populates="user")
    roles: Mapped[list[UserRole]] = relationship(back_populates="user")

    def has_permission(self, permission: str) -> bool:
        return any(r.role is not None and permission in r.role.permissions_list for r in self.roles)


class AuthSession(Base, UUIDPrimaryKey):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    mfa_pending: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="sessions", foreign_keys=[user_id])

    @property
    def is_live(self) -> bool:
        now = datetime.now(tz=self.expires_at.tzinfo)
        return self.revoked_at is None and now < self.expires_at


class EmailVerification(Base, UUIDPrimaryKey):
    __tablename__ = "email_verifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


class PasswordReset(Base, UUIDPrimaryKey):
    __tablename__ = "password_resets"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    requested_ip: Mapped[str] = mapped_column(String(64), default="")


class MfaFactor(Base, UUIDPrimaryKey):
    __tablename__ = "mfa_factors"
    __table_args__ = (UniqueConstraint("user_id", "type", name="uq_user_factor_type"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(16))  # totp | webauthn
    secret_encrypted: Mapped[str | None]  # envelope-encrypted TOTP seed
    credential_json: Mapped[str | None]  # serialized WebAuthn credential
    label: Mapped[str] = mapped_column(String(64), default="")
    confirmed_at: Mapped[datetime | None]
    last_used_at: Mapped[datetime | None]


class RecoveryCode(Base, UUIDPrimaryKey):
    __tablename__ = "recovery_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    code_hash: Mapped[str] = mapped_column(String(64))
    used_at: Mapped[datetime | None]


class Role(Base, UUIDPrimaryKey):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    permissions: Mapped[str] = mapped_column(Text, default="")  # space-separated permission ids

    @property
    def permissions_list(self) -> list[str]:
        return [p for p in self.permissions.split() if p]


class UserRole(Base, UUIDPrimaryKey):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))

    user: Mapped[User] = relationship(back_populates="roles")
    role: Mapped[Role | None] = relationship()


class ApiToken(Base, UUIDPrimaryKey):
    __tablename__ = "api_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scopes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None]
    last_used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]


class LoginAttempt(Base, UUIDPrimaryKey):
    """Brute-force signal for lockout/backoff decisions."""

    __tablename__ = "login_attempts"

    username_tried: Mapped[str] = mapped_column(String(64), index=True)
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    succeeded: Mapped[bool]
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
