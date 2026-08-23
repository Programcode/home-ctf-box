"""Persistence report endpoint: verifies a findings list, pays out the flag.

Training target only. The checker runs on the box itself and compares
the submitted paths against the four planted artifacts.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXPECTED = [
    "/etc/cron.d/system-sync",
    "/home/deploy/.bashrc",
    "/usr/local/sbin/sysmon-helper",
    "/etc/systemd/system/sysmon.service",
]
FLAG = os.environ["ROOM_FLAG"]
USAGE = {
    "endpoint": "/api/report",
    "method": "POST",
    "body": {"findings": ["/full/path/one", "..."]},
    "note": "submit the full path of every persistence artifact you identified",
}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path in ("/healthz", "/api/report"):
            self._send_json(USAGE)
            return
        self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        if self.path != "/api/report":
            self._send_json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            raw = json.loads(self.rfile.read(length) or b"{}")
            findings = [str(f).strip() for f in raw.get("findings", []) if str(f).strip()]
        except (json.JSONDecodeError, AttributeError):
            self._send_json({"error": "body must be JSON with a findings list"}, 400)
            return

        submitted = set(findings)
        expected = set(EXPECTED)
        missing = sorted(expected - submitted)
        unexpected = sorted(submitted - expected)
        verdict = {
            "status": "verified" if not missing else "incomplete",
            "matched": len(EXPECTED) - len(missing),
            "expected_total": len(EXPECTED),
            "missing": missing,
            "unexpected": unexpected,
        }
        if not missing:
            verdict["flag"] = FLAG
            verdict["note"] = (
                "all four persistence artifacts identified. In a real incident "
                "the next steps are containment, timeline building, and eradication."
            )
        else:
            verdict["note"] = "keep hunting; correlate shared indicators across artifacts."
        self._send_json(verdict)

    def log_message(self, fmt: str, *args: object) -> None:
        print("[report] " + fmt % args)


if __name__ == "__main__":
    port = int(os.environ.get("REPORT_PORT", "8000"))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
