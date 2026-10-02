from __future__ import annotations

from pathlib import Path
from typing import cast

from product_prd_generator.direct_evidence import EvidenceRole, _line_roles, scan_direct_evidence
from product_prd_generator.models import EvidenceKind


def _rules() -> dict[str, object]:
    return {
        "direct_code": {
            "enabled": True,
            "include_paths": ["src/**/*.py"],
            "extensions": [".py"],
        "capabilities": {"capability-a": ["Capability A"]},
        "spec_anchors": {"capability-a": "capability-a-spec"},
        },
        "direct_tests": {
            "enabled": True,
            "include_paths": ["tests/**/*.py"],
            "extensions": [".py"],
            "capabilities": {"capability-a": ["Capability A"]},
        },
        "exclude_paths": ["**/generated/**", "**/__pycache__/**"],
    }


def test_code_only_and_test_only_evidence_are_separate(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "service.py").write_text("CAPABILITY = 'Capability A'\n", encoding="utf-8")
    (tmp_path / "tests" / "test_service.py").write_text("assert 'Capability A'\n", encoding="utf-8")

    result = scan_direct_evidence(tmp_path, _rules())

    code_evidence = result.evidence_for("capability-a")
    assert [item.kind for item in code_evidence] == ["code", "test"]
    assert [item.ref for item in code_evidence] == ["src/service.py:1", "tests/test_service.py:1"]
    assert result.matches[0].spec_capability_id == "capability-a-spec"
    assert all("runtime not verified" in item.note or "test execution not verified" in item.note for item in code_evidence)


def test_spec_only_capability_has_no_direct_evidence(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "service.py").write_text("OTHER = 'unrelated'\n", encoding="utf-8")

    result = scan_direct_evidence(tmp_path, _rules())

    assert result.code.status == "complete"
    assert result.tests.status == "complete"
    assert result.evidence_for("capability-a") == ()


def test_excluded_path_produces_no_evidence(tmp_path: Path) -> None:
    generated = tmp_path / "src" / "generated"
    generated.mkdir(parents=True)
    (generated / "service.py").write_text("Capability A\n", encoding="utf-8")

    result = scan_direct_evidence(tmp_path, _rules())

    assert result.code.status == "complete"
    assert result.evidence_for("capability-a") == ()


def test_missing_configured_root_is_inaccessible(tmp_path: Path) -> None:
    rules = _rules()
    rules["direct_code"] = {
        "enabled": True,
        "include_paths": ["missing/**/*.py"],
        "extensions": cast(dict[str, object], rules["direct_code"])["extensions"],
        "capabilities": cast(dict[str, object], rules["direct_code"])["capabilities"],
    }

    result = scan_direct_evidence(tmp_path, rules)

    assert result.code.status == "inaccessible"
    assert result.evidence_for("capability-a") == ()


def test_serialized_evidence_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "b.py").write_text("Capability A\n", encoding="utf-8")
    (tmp_path / "src" / "a.py").write_text("Capability A\n", encoding="utf-8")

    first = scan_direct_evidence(tmp_path, _rules())
    second = scan_direct_evidence(tmp_path, _rules())

    assert first == second
    assert [item.ref for item in first.evidence_for("capability-a")] == ["src/a.py:1", "src/b.py:1"]


def test_python_matches_are_classified_by_syntax_role() -> None:
    source = "\n".join(
        [
            "from providers import ProviderCapabilities",
            "",
            "class ProviderCapabilities:",
            "    supports_chat: bool = False",
            "",
            "def get_provider_capabilities():",
            "    capabilities = ProviderCapabilities(supports_chat=True)",
            "",
            "def test_provider_capability():",
            "    dummy_provider = ProviderCapabilities(supports_chat=True)",
            "    assert dummy_provider.supports_chat is True",
        ]
    )

    roles = _line_roles(source, kind=EvidenceKind.TEST)

    assert roles[1] is EvidenceRole.IMPORT
    assert roles[3] is EvidenceRole.DECLARATION
    assert roles[7] is EvidenceRole.MAPPING
    assert roles[10] is EvidenceRole.FIXTURE
    assert roles[11] is EvidenceRole.ASSERTION


def test_syntax_error_source_defaults_to_other_role() -> None:
    assert _line_roles("def broken(:\n", kind=EvidenceKind.CODE) == {}
