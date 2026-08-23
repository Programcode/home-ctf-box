"""Test helper: run the real runner app on a local port."""

from __future__ import annotations

import uvicorn


def serve_runner(port: int) -> uvicorn.Server:
    from openrange.runner.main import create_app

    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    return uvicorn.Server(config)
