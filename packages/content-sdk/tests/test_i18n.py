"""i18n gate: locale resolution, protected-span validation, loader
overrides, and the shipped Hungarian sample proven end-to-end."""

from __future__ import annotations

from pathlib import Path

import pytest
from openrange.content import i18n
from openrange.content.i18n import resolve_locale, validate_translation
from openrange.content.loader import (
    LoadError,
    LocaleOverrides,
    SectionOverride,
    apply_section_overrides,
    available_locales,
    load_bundle,
    load_locale_overrides,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_MODULE = REPO_ROOT / "content" / "modules" / "linux-shell-and-files"

EN_SPANS = (
    "`ls *.log` lists logs while `mv report?.txt` renames one character.\n"
    "Run `mkdir -p lab/{raw,clean}` first; check `pwd` before any `rm *`.\n"
    "```\n"
    "$ grep -rn TODO /var/log\n"
    "```\n"
)

HU_FAITHFUL = (
    "A `ls *.log` listázza a naplókat, a `mv report?.txt` egy karaktert nevez át.\n"
    "Előbb futtasd a `mkdir -p lab/{raw,clean}` parancsot; `rm *` előtt nézd meg a `pwd`-t.\n"
    "```\n"
    "$ grep -rn TODO /var/log\n"
    "```\n"
)


def test_resolve_locale_exact_then_fallback_then_default() -> None:
    assert resolve_locale("hu", ["en", "hu"]) == "hu"
    assert resolve_locale("hu-HU", ["en", "hu"]) == "hu"
    assert resolve_locale("DE", ["en", "de"]) == "de"
    assert resolve_locale("hu-HU", ["en", "hu-hu"]) == "hu-hu"
    assert resolve_locale("de", ["en", "hu"]) == "en"
    assert resolve_locale(None, ["en", "hu"]) == "en"
    assert resolve_locale("  ", ["en", "hu"]) == "en"


def test_faithful_translation_has_no_violations() -> None:
    assert validate_translation(EN_SPANS, HU_FAITHFUL) == []


def test_modified_inline_code_span_is_caught() -> None:
    mutated = HU_FAITHFUL.replace("`mv report?.txt`", "`mv report.txt`")
    violations = validate_translation(EN_SPANS, mutated)
    assert [(v.kind, v.span_kind) for v in violations] == [("modified", "inline_code")]
    assert violations[0].expected == "mv report?.txt"


def test_missing_code_fence_is_caught() -> None:
    en = "Transcript:\n\n```\n$ grep -rn TODO /var/log\n```\nDone.\n"
    hu = "Átirat:\n\nKész.\n"
    violations = validate_translation(en, hu)
    assert {(v.kind, v.span_kind) for v in violations} == {("missing", "code_block")}


def test_missing_command_line_outside_fence_is_caught() -> None:
    en = "Check services:\n\n$ systemctl --failed\n"
    hu = "Ellenőrizd a szolgáltatásokat:\n"
    violations = validate_translation(en, hu)
    assert {(v.kind, v.span_kind) for v in violations} == {
        ("missing", "command_line"),
        ("missing", "flag"),
    }


def test_inline_code_wrapped_across_source_lines_still_matches() -> None:
    en = "Create with `tar czf out.tar.gz\nDIR`, extract with `tar xzf out.tar.gz`."
    hu = "Létrehozás: `tar czf out.tar.gz DIR`, kicsomagolás: `tar xzf out.tar.gz`."
    assert validate_translation(en, hu) == []


def test_missing_flag_and_path_are_caught() -> None:
    en = "Use the -r flag and inspect /var/log afterwards."
    hu_dropped = "Használd az -q kapcsolót, és utána nézd meg a naplókat."
    violations = validate_translation(en, hu_dropped)
    assert {(v.kind, v.span_kind) for v in violations} == {
        ("missing", "flag"),
        ("missing", "path"),
    }
    hu_kept = "Használd az -r kapcsolót, és utána nézd meg a /var/log könyvtárt."
    assert validate_translation(en, hu_kept) == []


def test_whitespace_only_change_reports_modified() -> None:
    en = "```\n$ ls -la\n$ pwd\n```"
    hu_padded = "```\n$ ls  -la\n$ pwd\n```"
    violations = validate_translation(en, hu_padded)
    assert [(v.kind, v.span_kind) for v in violations] == [("modified", "code_block")]
    assert "whitespace" in violations[0].detail


def test_sample_module_locales_and_overrides_load() -> None:
    assert available_locales(SAMPLE_MODULE) == ["en", "hu"]
    overrides = load_locale_overrides(SAMPLE_MODULE, "hu")
    assert overrides is not None
    assert overrides.locale == "hu"
    assert len(overrides.sections) == 6
    assert load_locale_overrides(SAMPLE_MODULE, "de") is None


def test_apply_section_overrides_keeps_structure_and_code() -> None:
    bundle = load_bundle(SAMPLE_MODULE / "module.yaml")
    overrides = load_locale_overrides(SAMPLE_MODULE, "hu")
    assert overrides is not None
    localized = apply_section_overrides(bundle, overrides)
    assert localized.metadata.slug == bundle.metadata.slug
    assert [s.id for s in localized.spec.sections] == [s.id for s in bundle.spec.sections]
    for before, after in zip(bundle.spec.sections, localized.spec.sections, strict=True):
        assert len(before.blocks) == len(after.blocks)
        for original, translated in zip(before.blocks, after.blocks, strict=True):
            if original.type in ("code", "quiz"):
                assert translated == original, f"{before.id}: {original.type} must stay English"
            elif original.type == "prose":
                assert translated.markdown != original.markdown


def test_shipped_hungarian_sample_passes_validation() -> None:
    bundle = load_bundle(SAMPLE_MODULE / "module.yaml")
    overrides = load_locale_overrides(SAMPLE_MODULE, "hu")
    assert overrides is not None
    localized = apply_section_overrides(bundle, overrides)
    checked = 0
    for before, after in zip(bundle.spec.sections, localized.spec.sections, strict=True):
        for original, translated in zip(before.blocks, after.blocks, strict=True):
            if original.type not in ("prose", "callout") or translated == original:
                continue
            violations = validate_translation(original.markdown, translated.markdown)
            assert violations == [], f"{before.id}: {violations}"
            checked += 1
    assert checked == 10


def test_deliberate_violation_in_shipped_sample_is_caught() -> None:
    """Sabotage one shipped Hungarian span and prove the gate trips."""
    bundle = load_bundle(SAMPLE_MODULE / "module.yaml")
    overrides = load_locale_overrides(SAMPLE_MODULE, "hu")
    assert overrides is not None
    sabotaged = dict(overrides.sections)
    entry = sabotaged["find-and-archive"]
    prose = next(b for b in entry.blocks if b.type == "prose")
    damaged = prose.model_copy(update={"markdown": prose.markdown.replace("-mtime -7", "-mtime 7")})
    sabotaged["find-and-archive"] = SectionOverride(
        section_id=entry.section_id, title=entry.title, blocks=[damaged]
    )
    broken = LocaleOverrides(locale="hu", path=overrides.path, sections=sabotaged)
    localized = apply_section_overrides(bundle, broken)
    section_after = next(s for s in localized.spec.sections if s.id == "find-and-archive")
    section_before = next(s for s in bundle.spec.sections if s.id == "find-and-archive")
    violations = validate_translation(
        section_before.blocks[0].markdown, section_after.blocks[0].markdown
    )
    assert [(v.kind, v.span_kind, v.expected) for v in violations] == [
        ("modified", "inline_code", "-mtime -7")
    ]


def test_override_count_mismatch_is_rejected() -> None:
    bundle = load_bundle(SAMPLE_MODULE / "module.yaml")
    overrides = load_locale_overrides(SAMPLE_MODULE, "hu")
    assert overrides is not None
    empty = SectionOverride(section_id="practice-mini-lab", title="Gyakorlat", blocks=[])
    broken = LocaleOverrides(
        locale="hu", path=overrides.path, sections={"practice-mini-lab": empty}
    )
    with pytest.raises(LoadError, match="do not match"):
        apply_section_overrides(bundle, broken)


def test_non_translatable_block_in_override_is_rejected(tmp_path: Path) -> None:
    module_dir = tmp_path / "mini-module"
    module_dir.mkdir()
    (module_dir / "sections.de.yaml").write_text(
        "locale: de\n"
        "sections:\n"
        "  - id: intro\n"
        "    title: 'Einfuehrung'\n"
        "    blocks:\n"
        "      - type: code\n"
        "        language: bash\n"
        "        code: |\n"
        "          $ echo hallo\n",
        encoding="utf-8",
    )
    with pytest.raises(LoadError, match=r"non-translatable block types \['code'\]"):
        load_locale_overrides(module_dir, "de")


def test_wrong_declared_locale_is_rejected(tmp_path: Path) -> None:
    module_dir = tmp_path / "mini-module"
    module_dir.mkdir()
    (module_dir / "sections.fr.yaml").write_text("locale: de\nsections: []\n", encoding="utf-8")
    with pytest.raises(LoadError, match="'locale' must be 'fr'"):
        load_locale_overrides(module_dir, "fr")


def test_unknown_top_level_keys_are_rejected(tmp_path: Path) -> None:
    module_dir = tmp_path / "mini-module"
    module_dir.mkdir()
    (module_dir / "sections.es.yaml").write_text(
        "locale: es\nsurprise: true\nsections: []\n", encoding="utf-8"
    )
    with pytest.raises(LoadError, match="unknown keys"):
        load_locale_overrides(module_dir, "es")


def test_i18n_module_exports_expected_surface() -> None:
    assert i18n.DEFAULT_LOCALE == "en"
