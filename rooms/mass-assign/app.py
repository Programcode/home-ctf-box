from flask import Flask, jsonify, Response, request
import os

app = Flask(__name__)
FLAG = os.environ["FLAG_10"]

USERS = {
    "guest": {"name": "Guest User", "email": "guest@nimbus.io", "role": "user"},
    "admin": {"name": "Ada Ministrator", "email": "admin@nimbus.io", "role": "admin"},
}


def text_resp(text, status):
    return Response(text, status=status, mimetype="text/plain")


@app.route("/")
def index():
    return (
        "<h1>Nimbus Profiles API</h1>"
        "<p>GET /profile?u=&lt;username&gt; reads a profile.</p>"
        "<p>POST /profile?u=&lt;username&gt; updates it from a JSON object body.</p>"
    )


@app.route("/profile", methods=["GET", "POST"])
def profile():
    u = request.args.get("u", "")
    prof = USERS.get(u)
    if prof is None:
        return text_resp("unknown user\n", 404)
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return text_resp("expected a JSON object body\n", 400)
        prof.update(data)
        return jsonify(name=prof["name"], email=prof["email"], updated=True)
    payload = {"name": prof["name"], "email": prof["email"]}
    if prof.get("role") == "admin":
        payload["note"] = FLAG
    return jsonify(payload)


app.run(host="0.0.0.0", port=5000)
