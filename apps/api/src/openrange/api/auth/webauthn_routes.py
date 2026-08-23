"""WebAuthn (passkey) second factor.

Ceremonies follow the W3C model via the `webauthn` library. Challenges
live in process memory keyed by the caller's session token hash and are
single-use. Credentials serialize into `mfa_factors.credential_json`.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import ClassVar

from fastapi import APIRouter, Request, Response
from openrange.api.auth.dependencies import CurrentUser, DbSession, current_session
from openrange.api.auth.service import AuthError
from openrange.api.auth.tokens import hash_token
from openrange.api.config import get_settings
from openrange.api.users.models import MfaFactor
from pydantic import BaseModel
from sqlalchemy import select
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.exceptions import InvalidAuthenticationResponse
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
)

router = APIRouter(prefix="/api/auth/webauthn", tags=["mfa"])

logger = logging.getLogger(__name__)


def _rp() -> tuple[str, str]:
    settings = get_settings()
    from urllib.parse import urlparse

    host = urlparse(settings.public_url).hostname or "localhost"
    return host, settings.public_url


class _ChallengeStore:
    challenges: ClassVar[dict[str, dict[str, object]]] = {}


def _challenge_key(request: Request) -> str:
    raw = request.cookies.get("openrange_session", "")
    return hash_token(raw)[:32]


async def _webauthn_factors(db: DbSession, user_id: uuid.UUID) -> list[MfaFactor]:
    rows = (
        await db.execute(
            select(MfaFactor).where(
                MfaFactor.user_id == user_id,
                MfaFactor.type == "webauthn",
            )
        )
    ).scalars()
    return [f for f in rows if f.credential_json]


def _descriptors(factors: list[MfaFactor]) -> list[PublicKeyCredentialDescriptor]:
    out = []
    for f in factors:
        stored = json.loads(f.credential_json or "{}")
        if "id_hex" in stored:
            out.append(PublicKeyCredentialDescriptor(id=bytes.fromhex(stored["id_hex"])))
    return out


@router.post("/register/begin")
async def register_begin(user: CurrentUser, request: Request, db: DbSession) -> Response:
    rp_id, rp_name = _rp()
    existing = await _webauthn_factors(db, user.id)
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_name=user.username,
        exclude_credentials=_descriptors(existing),
    )
    _ChallengeStore.challenges[_challenge_key(request)] = {
        "challenge": options.challenge,
        "user_id": str(user.id),
    }
    return Response(content=options_to_json(options), media_type="application/json")


class CeremonyIn(BaseModel):
    response: dict[str, object]
    label: str = "passkey"


@router.post("/register/finish")
async def register_finish(payload: CeremonyIn, request: Request, db: DbSession) -> dict[str, bool]:
    info = _ChallengeStore.challenges.get(_challenge_key(request))
    if not info:
        raise AuthError("no registration ceremony started", 409)
    rp_id, expected_origin = _rp()
    try:
        verification = verify_registration_response(
            credential=parse_registration_credential_json(json.dumps(payload.response)),
            expected_challenge=info["challenge"],  # type: ignore[arg-type]
            expected_origin=expected_origin,
            expected_rp_id=rp_id,
            require_user_verification=False,
        )
    except Exception as exc:
        raise AuthError("registration ceremony failed", 400) from exc
    db.add(
        MfaFactor(
            user_id=uuid.UUID(str(info["user_id"])),
            type="webauthn",
            credential_json=json.dumps(
                {
                    "id_hex": verification.credential_id.hex(),
                    "public_key": verification.credential_public_key.hex(),
                    "sign_count": verification.sign_count,
                }
            ),
            label=payload.label[:64],
            confirmed_at=datetime.now(UTC),
        )
    )
    del _ChallengeStore.challenges[_challenge_key(request)]
    await db.flush()
    return {"registered": True}


@router.post("/authenticate/begin")
async def authenticate_begin(request: Request, db: DbSession) -> Response:
    user, session = await current_session(request, db)
    if user is None or session is None:
        raise AuthError("authentication required", 401)
    factors = await _webauthn_factors(db, user.id)
    if not factors:
        raise AuthError("no passkeys registered", 404)
    options = generate_authentication_options(
        rp_id=_rp()[0], allow_credentials=_descriptors(factors)
    )
    _ChallengeStore.challenges[_challenge_key(request)] = {"challenge": options.challenge}
    return Response(content=options_to_json(options), media_type="application/json")


@router.post("/authenticate/finish")
async def authenticate_finish(
    payload: CeremonyIn, request: Request, db: DbSession
) -> dict[str, bool]:
    key = _challenge_key(request)
    info = _ChallengeStore.challenges.get(key)
    user, session = await current_session(request, db)
    if info is None or session is None or user is None:
        raise AuthError("no authentication ceremony started", 409)
    factors = await _webauthn_factors(db, user.id)
    matched: MfaFactor | None = None
    credential_id_hex = ""
    try:
        parsed = parse_authentication_credential_json(json.dumps(payload.response))
        credential_id_hex = parsed.raw_id.hex()
    except Exception as exc:
        logger.info("unparseable webauthn assertion (%s)", exc.__class__.__name__)
    for f in factors:
        stored = json.loads(f.credential_json or "{}")
        if stored.get("id_hex") != credential_id_hex:
            continue
        try:
            verification = verify_authentication_response(
                credential=parse_authentication_credential_json(json.dumps(payload.response)),
                expected_challenge=info["challenge"],  # type: ignore[arg-type]
                expected_origin=_rp()[1],
                expected_rp_id=_rp()[0],
                credential_public_key=bytes.fromhex(stored["public_key"]),
                credential_current_sign_count=int(stored["sign_count"]),
                require_user_verification=False,
            )
        except InvalidAuthenticationResponse as exc:
            raise AuthError("authentication ceremony failed", 401) from exc
        matched = f
        stored["sign_count"] = verification.new_sign_count
        f.credential_json = json.dumps(stored)
        break
    if matched is None:
        raise AuthError("unknown or invalid credential", 401)
    session.mfa_pending = False
    matched.last_used_at = datetime.now(UTC)
    del _ChallengeStore.challenges[key]
    await db.flush()
    return {"verified": True}
