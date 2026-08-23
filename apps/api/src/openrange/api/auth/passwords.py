"""Password hashing and strength rules (Argon2id)."""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_ph = PasswordHasher()  # argon2id, sensible defaults

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,31}$")
_RESERVED_USERNAMES = {
    "admin",
    "root",
    "administrator",
    "support",
    "security",
    "moderation",
    "openrange",
    "api",
    "system",
    "official",
    "staff",
}
_COMMON_PASSWORDS = {
    "password",
    "password1",
    "12345678",
    "qwertyuiop",
    "letmein123",
    "iloveyou",
    "admin12345",
    "welcome123",
    "monkey123",
    "dragon123",
}


class PasswordPolicyError(ValueError):
    pass


def validate_username(raw: str) -> str:
    name = raw.strip()
    if not _USERNAME_RE.match(name):
        raise PasswordPolicyError(
            "username must be 3-32 chars: letters, digits, dot, dash or underscore"
        )
    if name.lower() in _RESERVED_USERNAMES:
        raise PasswordPolicyError("that username is reserved")
    return name


def validate_password_strength(password: str, username: str) -> None:
    if len(password) < 10 or len(password) > 256:
        raise PasswordPolicyError("password must be 10-256 characters")
    if password.lower() in _COMMON_PASSWORDS:
        raise PasswordPolicyError("that password appears on breach lists; pick another")
    if username.lower() in password.lower():
        raise PasswordPolicyError("password must not contain your username")
    classes = sum(
        [
            any(c.islower() for c in password),
            any(c.isupper() for c in password),
            any(c.isdigit() for c in password),
            any(not c.isalnum() for c in password),
        ]
    )
    if len(password) < 16 and classes < 3:
        raise PasswordPolicyError("use at least three character classes, or a longer passphrase")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Constant-time-ish verification; returns False for null hashes.

    Rehashes transparently when parameters have drifted upward.
    """
    if not password_hash:
        return False
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _ph.check_needs_rehash(password_hash)
