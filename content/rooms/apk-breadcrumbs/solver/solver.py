"""Intended-path solver: unzip the package, regex the resources, verify findings."""

import io
import re
import zipfile

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def _resource(strings_xml: str, name: str) -> str:
    match = re.search(rf'<string name="{name}">([^<]+)</string>', strings_xml)
    assert match, f"missing resource {name}"
    return match.group(1)


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["extract-and-verify"]
    client = httpx.Client(base_url=ctx.url(), timeout=10)
    apk = client.get("/evidence/app.apk").content

    with zipfile.ZipFile(io.BytesIO(apk)) as zf:
        names = zf.namelist()
        assert "classes.dex" in names and "res/values/strings.xml" in names
        dex_stub = zf.read("classes.dex").decode()
        strings = zf.read("res/values/strings.xml").decode()

    assert "api_base_url" in dex_stub, "smali flow notes should name the resource"
    endpoint = _resource(strings, "api_base_url")
    key = _resource(strings, "debug_api_key")
    legacy = _resource(strings, "api_base_url_legacy")
    assert endpoint != legacy and "/v2" in endpoint

    resp = client.post("/verify", data={"api_endpoint": endpoint, "api_key": key})
    client.close()
    flags = find_flags(resp.text)
    captured = flags[0] if flags else None
    ok = captured == expected
    detail = None if ok else f"endpoint={endpoint} status={resp.status_code}"
    return SolveResult(
        results=[TaskResult(task_id="extract-and-verify", ok=ok, captured=captured, detail=detail)]
    )
