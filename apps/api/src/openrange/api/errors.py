"""Problem Details errors (RFC 9457) and handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openrange.api.auth.service import AuthError
from starlette.exceptions import HTTPException as StarletteHTTPException


def problem_response(
    status: int, title: str, detail: str | None, type_: str = "about:blank", **extra: object
) -> JSONResponse:
    body: dict[str, object] = {"type": type_, "title": title, "status": status}
    if detail:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        titles = {
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
        }
        return problem_response(exc.status, titles.get(exc.status, "Bad Request"), str(exc))

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem_response(
            exc.status_code,
            (exc.status_code >= 500 and "Internal Server Error") or "Request Failed",
            str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem_response(
            422, "Validation Failed", "request payload failed validation", errors=exc.errors()
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never leak internals; request id is in logs for correlation.
        return problem_response(500, "Internal Server Error", "an unexpected error occurred")
