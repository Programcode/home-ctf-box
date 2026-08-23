"""Nimbus people API: JSON patch merged wholesale into stored profiles. Room target only."""

import os

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

PEOPLE = {
    "guest": {"name": "Guest User", "email": "guest@nimbus.io", "role": "user"},
    "admin": {"name": "Ada Ministrator", "email": "admin@nimbus.io", "role": "admin"},
}


@app.get("/healthz")
def healthz() -> str:
    return "ok"


@app.get("/")
def index() -> str:
    return (
        "<h1>Nimbus People API</h1>"
        "<p>GET /profile?u=&lt;username&gt; reads a profile.</p>"
        "<p>POST /profile?u=&lt;username&gt; merges a JSON object body into it.</p>"
    )


@app.route("/profile", methods=["GET", "POST"])
def profile() -> Response | tuple[str, int]:
    handle = request.args.get("u", "")
    record = PEOPLE.get(handle)
    if record is None:
        return Response("unknown user\n", status=404, mimetype="text/plain")
    if request.method == "POST":
        patch = request.get_json(silent=True)
        if not isinstance(patch, dict):
            return Response("expected a JSON object body\n", status=400, mimetype="text/plain")
        record.update(patch)
        return jsonify(name=record["name"], email=record["email"], updated=True)
    payload = {"name": record["name"], "email": record["email"]}
    if record.get("role") == "admin":
        payload["note"] = FLAG
    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
