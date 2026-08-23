"""Authenticated streaming HTTP reverse proxy into lab instances."""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from openrange.gateway.problems import GatewayError
from openrange.gateway.runner import InstanceNotFoundError, RunnerUnavailableError
from openrange.gateway.tokens import LabTokenClaims, TokenError, verify_token

router = APIRouter()

#: Opaque instance ids: safe as a path segment and log field.
_INSTANCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

#: Never forwarded upstream; the lab token must not leak into lab networks.
_STRIPPED_QUERY_PARAMS = frozenset({"token", "resume"})

_HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)

#: Dropped towards the target: the platform session must not leak either.
_STRIPPED_REQUEST_HEADERS = ("authorization", "cookie")


def extract_token(request: Request) -> str | None:
    """Token from Authorization: Bearer, else from the token query param."""
    authorization = request.headers.get("authorization")
    if authorization and authorization[:7].lower() == "bearer ":
        return authorization[7:].strip()
    return request.query_params.get("token")


def authenticate(request: Request) -> LabTokenClaims:
    """Validate the request's lab token or raise a GatewayError."""
    secret = request.app.state.settings.gateway_secret
    token = extract_token(request)
    if not token:
        raise GatewayError(401, "Unauthenticated", "missing lab token")
    try:
        return verify_token(token, secret)
    except TokenError as exc:
        raise GatewayError(401, "Invalid Token", str(exc)) from exc


def _forwarded_query(request: Request) -> str:
    pairs = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(request.url.query, keep_blank_values=True)
        if key not in _STRIPPED_QUERY_PARAMS
    ]
    return urllib.parse.urlencode(pairs)


def _upstream_headers(request: Request, host_header: str) -> dict[str, str]:
    headers = {
        key.lower(): value
        for key, value in request.headers.items()
        if key.lower() not in _HOP_BY_HOP_HEADERS
        and key.lower() not in _STRIPPED_REQUEST_HEADERS
        and key.lower() != "host"
    }
    client_ip = request.client.host if request.client else "unknown"
    existing_chain = request.headers.get("x-forwarded-for")
    headers["x-forwarded-for"] = f"{existing_chain}, {client_ip}" if existing_chain else client_ip
    headers["x-forwarded-proto"] = request.url.scheme
    headers["x-forwarded-host"] = host_header
    headers["x-forwarded-port"] = str(
        request.url.port or (443 if request.url.scheme == "https" else 80)
    )
    return headers


async def _stream_upstream(upstream: httpx.Response) -> AsyncIterator[bytes]:
    try:
        async for chunk in upstream.aiter_raw():
            yield chunk
    finally:
        await upstream.aclose()


@router.api_route("/proxy/{instance_id}/{port}/{path:path}", methods=PROXY_METHODS)
async def proxy_request(instance_id: str, port: int, request: Request) -> StreamingResponse:
    if not _INSTANCE_ID_RE.match(instance_id):
        raise GatewayError(400, "Bad Request", "malformed instance id")
    claims = authenticate(request)
    if claims.lab != instance_id:
        raise GatewayError(403, "Forbidden", "token is scoped to another lab")
    if not claims.allows_port(port):
        raise GatewayError(403, "Forbidden", "port not allowed by this token")

    try:
        address = await request.app.state.runner.instance_address(instance_id)
    except InstanceNotFoundError as exc:
        raise GatewayError(404, "Not Found", "unknown lab instance") from exc
    except RunnerUnavailableError as exc:
        raise GatewayError(502, "Bad Gateway", "runner unavailable") from exc

    query = _forwarded_query(request)
    quoted_path = urllib.parse.quote(request.path_params["path"], safe="/")
    url = f"http://{address.host}:{port}/{quoted_path}"
    if query:
        url = f"{url}?{query}"

    client: httpx.AsyncClient = request.app.state.http
    upstream_request = client.build_request(
        request.method,
        url,
        headers=_upstream_headers(request, request.headers.get("host", "")),
        content=request.stream(),
    )
    upstream_response = await client.send(upstream_request, stream=True)

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in _HOP_BY_HOP_HEADERS
        and key.lower() not in ("content-length", "connection")
    }
    return StreamingResponse(
        _stream_upstream(upstream_response),
        status_code=upstream_response.status_code,
        headers=response_headers,
    )
