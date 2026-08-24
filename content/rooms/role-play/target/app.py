"""IAM privilege-escalation chain lab for the role-play room.

A simulated cloud IAM console: policy documents are readable, and the
lambda invoke endpoint honors pass_role when the caller may both
invoke the function and pass the target role. The intended chain is
dev-cli to report-runner to admin-role. Everything is a local
simulation with deterministic context tokens; no real cloud.
"""

import hashlib
import os

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

ACCOUNT = "111122223333"


def _fn_arn(name: str) -> str:
    return f"arn:sim:lambda:{ACCOUNT}:function/{name}"


def _role_arn(name: str) -> str:
    return f"arn:sim:iam::{ACCOUNT}:role/{name}"


def _context_token(function: str, role: str) -> str:
    digest = hashlib.sha256(f"{function}|{role}".encode()).hexdigest()[:20]
    return f"simctx-{digest}"


ADMIN_CONTEXT_TOKEN = _context_token("admin-console", "admin-role")

USERS = {
    "dev-cli": {
        "userName": "dev-cli",
        "note": "developer automation identity; this is who you are in the sim console",
        "attachedPolicies": [
            {
                "policyName": "dev-deploy",
                "document": {
                    "Version": "2012-10-sim",
                    "Statement": [
                        {
                            "Sid": "InvokeNightlyReport",
                            "Effect": "Allow",
                            "Action": ["lambda:InvokeFunction"],
                            "Resource": [_fn_arn("nightly-report")],
                        },
                        {
                            "Sid": "PassRunnerRoleOnly",
                            "Effect": "Allow",
                            "Action": ["iam:PassRole"],
                            "Resource": [_role_arn("report-runner")],
                        },
                        {
                            "Sid": "NoDirectAssume",
                            "Effect": "Deny",
                            "Action": ["sts:AssumeRole"],
                            "Resource": ["*"],
                        },
                    ],
                },
            }
        ],
    },
    "guest-audit": {
        "userName": "guest-audit",
        "note": "read-only reviewer account (decoy)",
        "attachedPolicies": [
            {
                "policyName": "console-read-only",
                "document": {
                    "Version": "2012-10-sim",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": ["iam:Get*", "lambda:Get*", "lambda:List*"],
                            "Resource": ["*"],
                        }
                    ],
                },
            }
        ],
    },
}

ROLES = {
    "report-runner": {
        "roleName": "report-runner",
        "arn": _role_arn("report-runner"),
        "assumePolicy": {
            "Version": "2012-10-sim",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.sim"},
                    "Action": "sts:AssumeRole",
                }
            ],
        },
        "attachedPolicies": [
            {
                "policyName": "runner-ops",
                "document": {
                    "Version": "2012-10-sim",
                    "Statement": [
                        {
                            "Sid": "InvokeAdminConsole",
                            "Effect": "Allow",
                            "Action": ["lambda:InvokeFunction"],
                            "Resource": [_fn_arn("admin-console")],
                        },
                        {
                            "Sid": "PassAdminRoleOnly",
                            "Effect": "Allow",
                            "Action": ["iam:PassRole"],
                            "Resource": [_role_arn("admin-role")],
                        },
                    ],
                },
            }
        ],
    },
    "admin-role": {
        "roleName": "admin-role",
        "arn": _role_arn("admin-role"),
        "assumePolicy": {
            "Version": "2012-10-sim",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.sim"},
                    "Action": "sts:AssumeRole",
                }
            ],
        },
        "attachedPolicies": [
            {
                "policyName": "admin-full",
                "document": {
                    "Version": "2012-10-sim",
                    "Statement": [
                        {
                            "Sid": "Everything",
                            "Effect": "Allow",
                            "Action": ["*"],
                            "Resource": ["*"],
                        },
                        {
                            "Sid": "AdminConsoleContextNote",
                            "Effect": "Allow",
                            "Action": ["sim:AdminConsoleContext"],
                            "Resource": [f"arn:sim:admin::{ACCOUNT}:context/console"],
                            "note": (
                                "the admin context endpoint accepts only an active "
                                "admin-console invocation token"
                            ),
                        },
                    ],
                },
            }
        ],
    },
}

FUNCTIONS = {
    "nightly-report": {
        "functionName": "nightly-report",
        "arn": _fn_arn("nightly-report"),
        "runtime": "python3.12-sim",
        "configuredRole": _role_arn("report-runner"),
        "trigger": "http-event(signed)",
        "description": "compiles the nightly ops report",
    },
    "admin-console": {
        "functionName": "admin-console",
        "arn": _fn_arn("admin-console"),
        "runtime": "python3.12-sim",
        "configuredRole": _role_arn("admin-role"),
        "trigger": "internal-event",
        "description": "administrative console backend",
    },
    "thumbnailer": {
        "functionName": "thumbnailer",
        "arn": _fn_arn("thumbnailer"),
        "runtime": "python3.12-sim",
        "configuredRole": None,
        "trigger": "storage-event",
        "description": "media pipeline worker; nobody needs to invoke this by hand",
    },
}


def _acting_identity() -> tuple[str | None, str]:
    ctx_token = request.headers.get("X-Sim-Context")
    if not ctx_token:
        return None, "sandbox"
    for function_name in FUNCTIONS:
        for role_name in ROLES:
            if _context_token(function_name, role_name) == ctx_token:
                return ctx_token, role_name
    return None, "invalid-context"


def _short(value: str) -> str:
    return value.rstrip("/").split("/")[-1].split(":")[-1]


def _allowed(identity: str, action: str, resource: str) -> bool:
    if identity == "sandbox":
        return False
    source: dict = ROLES.get(identity, USERS.get(identity, {}))
    for attached in source.get("attachedPolicies", []):
        for stmt in attached["document"]["Statement"]:
            if stmt.get("Effect") != "Allow":
                continue
            actions = stmt.get("Action", [])
            resources = stmt.get("Resource", [])
            if "*" in actions or action in actions:
                if "*" in resources or resource in resources:
                    return True
    return False


PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>sim iam console</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:36rem; margin-bottom:1rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
a { color:#111; }
</style></head><body>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE_HEAD
        + """
<div class="box">
<h1>sim iam console</h1>
<p>A local simulation of a cloud identity plane: users, roles,
attached policy documents you can read, and lambda functions whose
invocations honor <code>pass_role</code> when policy permits.</p>
<p>You are signed in as <code>dev-cli</code>. Requests may carry an
<code>X-Sim-Context</code> header when acting through an invoked
function's execution context.</p>
<p>Endpoints:</p>
<ul>
<li><code>GET /whoami</code></li>
<li><code>GET /iam/users/&lt;name&gt;</code> and
<code>GET /iam/roles/&lt;name&gt;</code>: policy documents</li>
<li><code>GET /lambda/functions</code>, then
<code>/lambda/functions/&lt;name&gt;/config</code></li>
<li><code>POST /lambda/functions/&lt;name&gt;/invoke</code> with JSON
body, optionally <code>{"pass_role":"&lt;role&gt;"}</code></li>
<li><code>GET /admin/context</code>: requires an authorized elevation</li>
</ul>
<p>This whole console is one Flask process inside your lab container.
Nothing here touches a real cloud provider or account.</p>
</div></body></html>"""
    )


@app.get("/whoami")
def whoami():
    token, role = _acting_identity()
    return jsonify(
        {
            "principal": role if token else "dev-cli",
            "mode": "execution-context" if token else "console-session",
            "contextToken": token,
            "hint": "policy documents are readable under /iam/...",
        }
    )


@app.get("/iam/users/<name>")
def get_user(name: str):
    user = USERS.get(name)
    if not user:
        return jsonify({"error": "NoSuchUser"}), 404
    return jsonify(user)


@app.get("/iam/roles/<name>")
def get_role(name: str):
    role = ROLES.get(name)
    if not role:
        return jsonify({"error": "NoSuchRole"}), 404
    return jsonify(role)


@app.get("/lambda/functions")
def list_functions():
    return jsonify({"functions": list(FUNCTIONS.values())})


@app.get("/lambda/functions/<name>")
def function_config(name: str):
    fn = FUNCTIONS.get(name)
    if not fn:
        return jsonify({"error": "NoSuchFunction"}), 404
    return jsonify(fn)


@app.post("/lambda/functions/<name>/invoke")
def invoke(name: str):
    fn = FUNCTIONS.get(name)
    if not fn:
        return jsonify({"error": "NoSuchFunction"}), 404

    token, acting_role = _acting_identity()
    if token is None and acting_role == "invalid-context":
        return jsonify({"error": "InvalidSimContext"}), 403

    body = request.get_json(silent=True) or {}
    pass_role = body.get("pass_role")
    target_resource = _fn_arn(name)

    if not _allowed(acting_role if token else "dev-cli", "lambda:InvokeFunction", target_resource):
        return (
            jsonify(
                {
                    "error": "AccessDeniedInvoke",
                    "detail": f"identity '{'dev-cli' if not token else acting_role}' "
                    f"may not invoke {name}",
                }
            ),
            403,
        )

    if pass_role:
        role_name = _short(str(pass_role))
        if role_name not in ROLES:
            return jsonify({"error": "NoSuchRole"}), 404
        if not _allowed(acting_role if token else "dev-cli", "iam:PassRole", _role_arn(role_name)):
            return (
                jsonify(
                    {
                        "error": "AccessDeniedPassRole",
                        "detail": f"identity '{'dev-cli' if not token else acting_role}' "
                        f"may not pass {role_name}",
                    }
                ),
                403,
            )
        executed_as = role_name
        new_token = _context_token(name, role_name)
    else:
        if name == "nightly-report":
            output = (
                "nightly report compiled: 41 backups verified, "
                "0 anomalies flagged. nothing interesting here."
            )
        elif name == "admin-console":
            output = "admin console idle."
        else:
            output = "function ran in sandbox context."
        return jsonify(
            {
                "invocationId": f"inv-{abs(hash(name)) % 100000:05d}",
                "executedAs": "sandbox-baseline",
                "output": output,
                "note": "no pass_role supplied, so no execution context was attached",
            }
        )

    return jsonify(
        {
            "invocationId": f"inv-{abs(hash(name + executed_as)) % 100000:05d}",
            "invokedFunction": name,
            "passedRole": _role_arn(executed_as),
            "executedAs": executed_as,
            "contextToken": new_token,
            "usage": "send it as X-Sim-Context on later calls, or as a Bearer token",
        }
    )


@app.get("/admin/context")
def admin_context():
    token = ""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.headers.get("X-Sim-Context", "")
    if token == ADMIN_CONTEXT_TOKEN:
        return (
            PAGE_HEAD
            + f"""
<div class="box">
<h1>admin console context active</h1>
<p>You are operating through admin-role via an admin-console
invocation. The direct-assume path was denied on purpose; the only way
here was the chained PassRole plus InvokeFunction combo.</p>
<span class="flag">{FLAG}</span>
<p>Remediation note: PassRole belongs in narrow, resource-scoped
statements. A developer identity that can hand roles to compute it can
also invoke is holding a ladder to admin.</p>
</div></body></html>"""
        )
    return (
        PAGE_HEAD
        + """
<div class="box">
<h1>admin context required</h1>
<p>This endpoint answers only to an active admin-console execution
context. Present the context token from such an invocation as a Bearer
token or X-Sim-Context header.</p>
</div></body></html>""",
        403,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
