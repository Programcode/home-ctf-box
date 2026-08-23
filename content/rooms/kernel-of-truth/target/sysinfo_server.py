"""Legacy appliance sysinfo endpoint: reports the simulated kernel version."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KERNEL = "Linux target 5.4.0-42-generic #46-Ubuntu SMP Fri Jul 10 00:24:02 UTC 2026 x86_64"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path == "/healthz":
            self._send_json({"status": "ok"})
            return
        if self.path == "/api/sysinfo":
            self._send_json(
                {
                    "hostname": "target",
                    "kernel": KERNEL,
                    "version_simulated": True,
                    "note": (
                        "This appliance slice reports a fixed kernel version for the "
                        "training scenario. The container host's real kernel is "
                        "irrelevant here; treat this endpoint as authoritative."
                    ),
                }
            )
            return
        self._send_json({"error": "not found"}, 404)

    def log_message(self, fmt: str, *args: object) -> None:
        print("[sysinfo] " + fmt % args)


if __name__ == "__main__":
    port = int(os.environ.get("SYSINFO_PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
