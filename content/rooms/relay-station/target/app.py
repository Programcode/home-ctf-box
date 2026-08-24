"""Relay coordinator for the relay-station room: NTLM relay mechanics, simulated.

Real NTLM relay abuses the NTLMv2 challenge-response protocol over
SMB or HTTP. This room substitutes a documented HMAC-SHA256
challenge-response scheme with deterministic challenges derived from
sha256(target + fixed room secret). The choice is disclosed on
/docs/protocol, keeps the room deterministic, and removes any legal
gray area: no NTLM bytes, no SMB, no responder-style sniffing, and no
real credentials exist anywhere.

The essence being taught: a proof is bound to its challenge but not to
the party that posed it, so whoever carries both can spend them at the
target that minted the challenge.
"""

import hashlib
import hmac
import json
import os

from flask import Flask, Response, jsonify, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

# Fixed, disclosed room secret backing deterministic challenges.
ROOM_SECRET = "COORDSIM-RELAY-V1"
CHALLENGE_BYTES = 12  # rendered as 24 hex characters

TARGETS = ["fileserver", "printserver", "backup-nas"]

DEVICES = {
    "printer-svc": {
        "password": "PrintQueue77!",
        "device": "printer01",
        "normally_calls": "printserver",
    },
}

NOTICE = (
    "Simulation notice: this box speaks JSON over plain HTTP, not SMB "
    "or NTLM. Challenges and proofs are documented HMAC/SHA-256 "
    "stand-ins; no real credentials exist."
)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Relay Station</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:38rem; margin:.4rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:.8rem; }
p, li { color:#787774; font-size:.92rem; }
.notice { border-left:3px solid #C9A227; padding-left:.8rem; }
code { font-family:ui-monospace,Menlo,monospace; background:#F7F6F3; padding:.1rem .3rem; border-radius:4px; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>%s</body></html>"""


def page(body: str):
    return PAGE % body


def target_challenge(target: str) -> str:
    material = f"challenge|{target}|{ROOM_SECRET}".encode()
    return hashlib.sha256(material).hexdigest()[: CHALLENGE_BYTES * 2]


def account_proof(password: str, challenge_hex: str) -> str:
    key = hashlib.sha256(password.encode()).digest()
    try:
        blob = bytes.fromhex(challenge_hex)
    except ValueError:
        return ""
    return hmac.new(key, blob, hashlib.sha256).hexdigest()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return page(
        "<div class='box'><h1>Relay Station <small>(simulated)</small></h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p>Three parties share this stage. The <strong>coordinator</strong> "
        "mints per-target challenges at <a href='/coordinator/challenge?"
        "target=fileserver'>/coordinator/challenge</a>. The <strong>printer "
        "device</strong> answers any challenge handed to it via POST "
        "<code>/devices/printer/connect</code>, check its posture at "
        "<a href='/devices/printer/status'>/devices/printer/status</a>. The "
        "<strong>fileserver endpoint</strong> accepts matching triples at "
        "<code>/fileserver/verify</code>. Protocol and disclosure: "
        "<a href='/docs/protocol'>/docs/protocol</a>. Tooling: "
        "<a href='/tools/relay-sim.py'>/tools/relay-sim.py</a>.</p></div>"
    )


@app.get("/docs/protocol")
def docs():
    example_target = "fileserver"
    example_challenge = target_challenge(example_target)
    return page(
        "<div class='box'><h1>SIM-AUTH protocol documentation</h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p><strong>Challenges.</strong> For each service target the "
        'coordinator mints <code>sha256("challenge|&lt;target&gt;|'
        f'{escape(ROOM_SECRET)}")[:24 hex]</code>, currently '
        f"<code>{example_challenge}</code> for {example_target}. "
        "Deterministic on purpose so grading works twice.</p>"
        "<p><strong>Proofs.</strong> An account answers a challenge with "
        "<code>HMAC-SHA256(key=sha256(password), msg=challenge-bytes)</code>. "
        "The password never leaves the account; the proof is only valid for "
        "the exact challenge bytes.</p>"
        "<p><strong>The flaw.</strong> Neither the coordinator nor the "
        "device binds a handshake to the session that requested it. A "
        "challenge minted for fileserver stays acceptable there, so anyone "
        "who can make printer-svc answer that specific challenge can carry "
        "the result to fileserver themselves. That is the whole relay "
        "idea, minus NTLM.</p>"
        "<p><strong>What real relaying adds.</strong> Actual NTLM relay "
        "runs over SMB or HTTP negotiation, needs signing disabled on the "
        "target, and usually pairs with coercion of machine accounts "
        "(printer bugs, PetitPotam-style triggers). Defenders enable "
        "channel binding plus SMB signing everywhere, restrict inbound "
        "NTLM, and watch for coercion traffic.</p></div>"
    )


@app.get("/coordinator/challenge")
def coordinator_challenge():
    target = request.args.get("target", "")
    if target not in TARGETS:
        return jsonify({"error": "UNKNOWN_TARGET", "known": TARGETS}), 404
    return Response(
        json.dumps(
            {
                "simulation": NOTICE,
                "target": target,
                "challenge": target_challenge(target),
            },
            indent=2,
        ),
        mimetype="application/json",
        headers={"X-COORD-SIM": "deterministic training data"},
    )


@app.get("/devices/printer/status")
def printer_status():
    record = DEVICES["printer-svc"]
    body = {
        "account": "printer-svc",
        "device": record["device"],
        "normally_calls": record["normally_calls"],
        "posture": "answers any challenge presented by any caller",
        "note": "this trust model is what makes relay possible",
    }
    return Response(
        json.dumps({"simulation": NOTICE, **body}, indent=2),
        mimetype="application/json",
        headers={"X-DEVICE-SIM": "fictional training data"},
    )


@app.post("/devices/printer/connect")
def printer_connect():
    data = request.get_json(silent=True) or {}
    challenge = str(data.get("challenge", "")).lower()
    if len(challenge) != CHALLENGE_BYTES * 2 or any(c not in "0123456789abcdef" for c in challenge):
        return (
            jsonify({"error": "MALFORMED_CHALLENGE", "detail": "24 hex chars expected"}),
            400,
        )
    record = DEVICES["printer-svc"]
    proof = account_proof(record["password"], challenge)
    if not proof:
        return jsonify({"error": "MALFORMED_CHALLENGE"}), 400
    return Response(
        json.dumps(
            {
                "simulation": NOTICE,
                "account": "printer-svc",
                "answered_challenge": challenge,
                "proof": proof,
                "note": "response handed back to the presenting caller",
            },
            indent=2,
        ),
        mimetype="application/json",
        headers={"X-DEVICE-SIM": "proof is not an NTLM response"},
    )


@app.post("/fileserver/verify")
def fileserver_verify():
    data = request.get_json(silent=True) or {}
    account = str(data.get("account", ""))
    challenge = str(data.get("challenge", "")).lower()
    proof = str(data.get("proof", "")).lower()
    expected_challenge = target_challenge("fileserver")
    if challenge != expected_challenge:
        return (
            jsonify(
                {
                    "error": "WRONG_TARGET_CHALLENGE",
                    "detail": "that challenge was not minted for fileserver",
                }
            ),
            400,
        )
    record = DEVICES.get(account)
    if record is None:
        return jsonify({"error": "UNKNOWN_ACCOUNT"}), 404
    if not hmac.compare_digest(account_proof(record["password"], challenge), proof):
        return jsonify({"error": "BAD_PROOF"}), 401
    return page(
        "<div class='box'><h1>Fileserver access granted</h1>"
        "<p>Authenticated as "
        + escape(account)
        + " through a proof the device computed for someone else's "
        "handshake. Signing and channel binding would have refused this "
        "on a real network. Your session verification token:</p>"
        f"<span class='flag'>{FLAG}</span></div>"
    )


TOOL_DIR = "tools"


@app.get("/tools/relay-sim.py")
def tool_script():
    with open(f"{app.root_path}/{TOOL_DIR}/relay-sim.py") as fh:
        return Response(fh.read(), mimetype="text/x-python")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
