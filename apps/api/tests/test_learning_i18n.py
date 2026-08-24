"""Localization endpoint proof: the shipped linux-shell-and-files
Hungarian override served end-to-end through /api/learning."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from openrange.api.learning import content as learning_content

pytestmark = [pytest.mark.integration]

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = "linux-shell-and-files"


@pytest.fixture(autouse=True)
def real_content(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    monkeypatch.setenv(learning_content.CONTENT_DIR_ENV, str(REPO_ROOT / "content"))
    learning_content.clear_caches()
    yield
    learning_content.clear_caches()


async def make_client(username: str) -> tuple[AsyncClient, dict[str, str]]:
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    client = AsyncClient(transport=transport, base_url="http://test", timeout=60)
    res = await client.post(
        "/api/auth/register",
        json={"username": username, "password": "correct-horse-battery"},
    )
    assert res.status_code == 201, res.text
    return client, {"x-csrf-token": res.json()["csrf_token"]}


async def test_module_serves_hungarian_overrides_end_to_end() -> None:
    client, headers = await make_client("l10n-reader")
    try:
        en_res = await client.get(f"/api/learning/modules/{MODULE}", headers=headers)
        assert en_res.status_code == 200, en_res.text
        en = en_res.json()

        hu_res = await client.get(
            f"/api/learning/modules/{MODULE}", params={"lang": "hu"}, headers=headers
        )
        assert hu_res.status_code == 200, hu_res.text
        hu = hu_res.json()

        assert en["locale"] == "en"
        assert hu["locale"] == "hu"
        assert hu["sections"][0]["title"] == "Navigálás szándékkal"
        assert (
            hu["sections"][0]["blocks"][0]["markdown"] != en["sections"][0]["blocks"][0]["markdown"]
        )

        # Code and quiz blocks must be byte-identical to English.
        for sec_en, sec_hu in zip(en["sections"], hu["sections"], strict=True):
            kept_en = [b for b in sec_en["blocks"] if b["type"] in ("code", "quiz")]
            kept_hu = [b for b in sec_hu["blocks"] if b["type"] in ("code", "quiz")]
            assert kept_en == kept_hu, f"{sec_en['id']}: non-prose blocks drifted"

        # Unknown locale falls back to English.
        de_res = await client.get(
            f"/api/learning/modules/{MODULE}", params={"lang": "de"}, headers=headers
        )
        assert de_res.status_code == 200
        de = de_res.json()
        assert de["locale"] == "en"
        assert de["sections"][0]["title"] == en["sections"][0]["title"]

        # Language fallback: hu-HU resolves to the hu overrides.
        hh_res = await client.get(
            f"/api/learning/modules/{MODULE}", params={"lang": "hu-HU"}, headers=headers
        )
        assert hh_res.json()["locale"] == "hu"
    finally:
        await client.aclose()


async def test_module_lang_falls_back_when_module_has_no_overrides() -> None:
    client, headers = await make_client("l10n-reader-2")
    try:
        res = await client.get(
            "/api/learning/modules/terminals-and-operating-systems",
            params={"lang": "hu"},
            headers=headers,
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["locale"] == "en"
    finally:
        await client.aclose()
