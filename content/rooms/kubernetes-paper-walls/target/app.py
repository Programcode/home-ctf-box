"""Fake Kubernetes API for the kubernetes-paper-walls room.

Serves a small JSON graph of service accounts, secrets, roles, and
role bindings for one namespace, with bearer-token authentication and
RBAC checks computed from the live binding list. The intended chain:
an over-privileged SA token leads to a stolen peer token, a created
binding grants exec rights, and an exec into the simulated pod yields
the flag. Everything is in-memory Flask; no cluster exists here.
"""

import base64
import os

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

TOKENS = {
    "sim-token-metrics-agent": "metrics-agent",
    "sim-jwt-deploy-bot-9f4c2e": "deploy-bot",
    "sim-token-default-none": "default",
}

SERVICE_ACCOUNTS = {
    "default": {"secrets": []},
    "metrics-agent": {"secrets": ["metrics-agent-token"]},
    "deploy-bot": {"secrets": ["deploy-bot-token"]},
    "flagship-app": {"secrets": ["flagship-token"]},
}

SECRETS = {
    "metrics-agent-token": {
        "type": "sim.io/service-account-token",
        "data": {"token": "sim-token-metrics-agent"},
        "annotations": {
            "sim.io/service-account.name": "metrics-agent",
            "note": "this is your own identity; you are already wearing it",
        },
    },
    "deploy-bot-token": {
        "type": "sim.io/service-account-token",
        "data": {"token": "sim-jwt-deploy-bot-9f4c2e"},
        "annotations": {
            "sim.io/service-account.name": "deploy-bot",
            "note": "mounted into the deploy-bot jobs; whoever reads it wears it",
        },
    },
    "flagship-token": {
        "type": "sim.io/service-account-token",
        "data": {"token": "REDACTED-FOR-SIM"},
        "annotations": {
            "sim.io/service-account.name": "flagship-app",
            "note": "the sim redacted this one; some doors stay shut on purpose",
        },
    },
    "ops-config": {
        "type": "Opaque",
        "data": {"log_level": "info", "retry_max": "3"},
        "annotations": {"note": "harmless application config"},
    },
}

ROLES = {
    "token-reader": {
        "rules": [{"verbs": ["get", "list"], "resource": "secrets"}],
    },
    "log-viewer": {
        "rules": [
            {"verbs": ["get"], "resource": "pods/log"},
            {"verbs": ["list"], "resource": "pods"},
        ],
    },
    "binding-admin": {
        "rules": [{"verbs": ["create"], "resource": "rolebindings"}],
    },
    "prod-admin": {
        "rules": [
            {"verbs": ["create", "get"], "resource": "pods/exec"},
            {"verbs": ["get", "list"], "resource": "pods"},
        ],
    },
}

BINDINGS = [
    {
        "metadata": {"name": "metrics-agent-reads", "namespace": "prod"},
        "roleRef": {"kind": "Role", "name": "token-reader"},
        "subjects": [{"kind": "ServiceAccount", "name": "metrics-agent"}],
    },
    {
        "metadata": {"name": "metrics-agent-logs", "namespace": "prod"},
        "roleRef": {"kind": "Role", "name": "log-viewer"},
        "subjects": [{"kind": "ServiceAccount", "name": "metrics-agent"}],
    },
    {
        "metadata": {"name": "deploy-bot-manages-bindings", "namespace": "prod"},
        "roleRef": {"kind": "Role", "name": "binding-admin"},
        "subjects": [{"kind": "ServiceAccount", "name": "deploy-bot"}],
    },
]

PODS = [
    {
        "metadata": {"name": "flagship-0", "namespace": "prod"},
        "spec": {"serviceAccountName": "flagship-app"},
        "status": {"phase": "Running"},
    }
]


def _current_sa() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return TOKENS.get(auth.split(" ", 1)[1].strip())
    return None


def _effective_rules(sa: str) -> list[dict]:
    rules: list[dict] = []
    for binding in BINDINGS:
        subjects = [s["name"] for s in binding["subjects"] if s["kind"] == "ServiceAccount"]
        if sa in subjects:
            rules.extend(ROLES[binding["roleRef"]["name"]]["rules"])
    return rules


def _can(sa: str | None, verb: str, resource: str) -> bool:
    if not sa:
        return False
    for rule in _effective_rules(sa):
        resources = rule["resource"].split("/")
        base_resource = resources[0]
        subresource = resources[1] if len(resources) > 1 else ""
        wanted_base, _, wanted_sub = resource.partition("/")
        if base_resource != wanted_base or subresource != wanted_sub:
            continue
        if verb in rule["verbs"] or "*" in rule["verbs"]:
            return True
    return False


def _unauthorized():
    return (
        jsonify(
            {
                "kind": "Status",
                "status": "Failure",
                "reason": "Unauthorized",
                "message": "provide Authorization: Bearer <sa token>",
            }
        ),
        401,
    )


def _forbidden(action: str, sa: str):
    return (
        jsonify(
            {
                "kind": "Status",
                "status": "Failure",
                "reason": "Forbidden",
                "message": f"service account '{sa}' may not {action}",
            }
        ),
        403,
    )


PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>paper walls apiserver (sim)</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:37rem; margin-bottom:1rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
a { color:#111; }
</style></head><body>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/version")
def version():
    return jsonify({"major": "1", "minor": "31-sim", "platform": "flask/paper"})


@app.get("/")
def home():
    return (
        PAGE_HEAD
        + """
<div class="box">
<h1>paper walls apiserver</h1>
<p>A simulated Kubernetes control plane serving one namespace,
<code>prod</code>, as plain JSON. Bearer tokens authenticate; RBAC is
computed live from the role binding list.</p>
<p>Your starting identity:</p>
<ul>
<li>service account <code>metrics-agent</code></li>
<li>bearer token <code>sim-token-metrics-agent</code></li>
</ul>
<p>Endpoints mirror kubectl's wire paths:</p>
<ul>
<li><code>/api/v1/namespaces/prod/serviceaccounts</code></li>
<li><code>/api/v1/namespaces/prod/secrets/&#123;name&#125;</code></li>
<li><code>/apis/rbac.authorization.k8s.io/v1/namespaces/prod/roles</code></li>
<li><code>/apis/rbac.authorization.k8s.io/v1/namespaces/prod/rolebindings</code> (GET list, POST create)</li>
<li><code>/api/v1/namespaces/prod/pods</code>,
<code>/api/v1/namespaces/prod/pods/flagship-0/exec</code> (POST)</li>
<li><code>/apis/authorization.sim.io/v1/selfsubjectrulesreviews</code>: your effective rules</li>
</ul>
<p>This apiserver is a dictionary-backed Flask process inside your lab
container. No real cluster, node, or container runs anywhere behind
it.</p>
</div></body></html>"""
    )


@app.get("/apis/authorization.sim.io/v1/selfsubjectrulesreviews")
def selfreview():
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    return jsonify({"serviceAccount": sa, "rules": _effective_rules(sa)})


@app.get("/api/v1/namespaces/prod/serviceaccounts")
def list_sas():
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    items = [
        {"metadata": {"name": name, "namespace": "prod"}, "secrets": info["secrets"]}
        for name, info in SERVICE_ACCOUNTS.items()
    ]
    return jsonify({"kind": "ServiceAccountList", "items": items})


@app.get("/api/v1/namespaces/prod/serviceaccounts/<name>")
def get_sa(name: str):
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    if name not in SERVICE_ACCOUNTS:
        return jsonify({"kind": "Status", "reason": "NotFound"}), 404
    return jsonify(
        {
            "metadata": {"name": name, "namespace": "prod"},
            "secrets": SERVICE_ACCOUNTS[name]["secrets"],
        }
    )


@app.get("/api/v1/namespaces/prod/secrets")
def list_secrets():
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    if not _can(sa, "list", "secrets"):
        return _forbidden("list secrets", sa)
    items = [
        {"metadata": {"name": name, "namespace": "prod"}, "type": meta["type"]}
        for name, meta in SECRETS.items()
    ]
    return jsonify({"kind": "SecretList", "items": items})


@app.get("/api/v1/namespaces/prod/secrets/<name>")
def get_secret(name: str):
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    if not _can(sa, "get", "secrets"):
        return _forbidden(f"read secret '{name}'", sa)
    meta = SECRETS.get(name)
    if not meta:
        return jsonify({"kind": "Status", "reason": "NotFound"}), 404
    encoded = {
        key: base64.b64encode(value.encode()).decode() for key, value in meta["data"].items()
    }
    return jsonify(
        {
            "kind": "Secret",
            "metadata": {"name": name, "namespace": "prod"},
            "type": meta["type"],
            "annotations": meta["annotations"],
            "data": encoded,
        }
    )


@app.get("/apis/rbac.authorization.k8s.io/v1/namespaces/prod/roles")
def list_roles():
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    items = [
        {"metadata": {"name": name, "namespace": "prod"}, "rules": role["rules"]}
        for name, role in ROLES.items()
    ]
    return jsonify({"kind": "RoleList", "items": items})


@app.get("/apis/rbac.authorization.k8s.io/v1/namespaces/prod/rolebindings")
def list_bindings():
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    return jsonify({"kind": "RoleBindingList", "items": BINDINGS})


@app.post("/apis/rbac.authorization.k8s.io/v1/namespaces/prod/rolebindings")
def create_binding():
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    if not _can(sa, "create", "rolebindings"):
        return _forbidden("create rolebindings", sa)
    body = request.get_json(silent=True) or {}
    metadata = body.get("metadata") or {}
    role_ref = body.get("roleRef") or {}
    subjects = body.get("subjects") or []
    name = str(metadata.get("name") or "")
    role_name = str(role_ref.get("name") or "")
    if not name or not role_name or not subjects:
        return (
            jsonify(
                {
                    "kind": "Status",
                    "reason": "Invalid",
                    "message": "need metadata.name, roleRef.name, and subjects",
                }
            ),
            400,
        )
    if role_name not in ROLES:
        return (
            jsonify(
                {
                    "kind": "Status",
                    "reason": "NotFound",
                    "message": f"role '{role_name}' does not exist",
                }
            ),
            404,
        )
    binding = {
        "metadata": {"name": name, "namespace": "prod"},
        "roleRef": {"kind": "Role", "name": role_name},
        "subjects": subjects,
    }
    BINDINGS.append(binding)
    return jsonify({"kind": "RoleBinding", **binding}), 201


@app.get("/api/v1/namespaces/prod/pods")
def list_pods():
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    if not _can(sa, "list", "pods"):
        return _forbidden("list pods", sa)
    return jsonify({"kind": "PodList", "items": PODS})


@app.post("/api/v1/namespaces/prod/pods/<pod>/exec")
def exec_pod(pod: str):
    sa = _current_sa()
    if not sa:
        return _unauthorized()
    if pod != "flagship-0":
        return jsonify({"kind": "Status", "reason": "NotFound"}), 404
    if not _can(sa, "create", "pods/exec"):
        return _forbidden(f"exec into pod '{pod}'", sa)
    body = request.get_json(silent=True) or {}
    command = [str(arg) for arg in body.get("command", [])]
    stdout = (
        f"{FLAG}\n"
        if any("cat" == arg for arg in command) and any("flag" in arg for arg in command)
        else "bin\netc\nvar\n"
    )
    return jsonify(
        {
            "kind": "SimExecResult",
            "pod": pod,
            "command": command,
            "stdout": stdout,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
