"""RFC 9457 problem-details responses for the gateway API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class GatewayError(Exception):
    """A failure that maps directly onto a problem-details response."""

    def __init__(self, status: int, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail


def problem_body(status: int, title: str, detail: str | None, **extra: object) -> dict[str, Any]:
    body: dict[str, Any] = {"type": "about:blank", "title": title, "status": status}
    if detail:
        body["detail"] = detail
    body.update(extra)
    return body


def problem_response(status: int, title: str, detail: str | None, **extra: object) -> JSONResponse:
    return JSONResponse(
        problem_body(status, title, detail, **extra),
        status_code=status,
        media_type="application/problem+json",
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(GatewayError)
    async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
        return problem_response(exc.status, exc.title, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = "Internal Server Error" if exc.status_code >= 500 else "Request Failed"
        return problem_response(exc.status_code, title, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        safe_errors = [
            {k: v for k, v in err.items() if k in ("loc", "msg", "type")} for err in exc.errors()
        ]
        return problem_response(
            422, "Validation Failed", "request payload failed validation", errors=safe_errors
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return problem_response(500, "Internal Server Error", "an unexpected error occurred")
