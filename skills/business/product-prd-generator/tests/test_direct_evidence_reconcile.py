"""Regression tests for direct-evidence-only capabilities in reconcile().

2026-11-01 lnkcard fix: a direct scanner match on an ontology capability id
(e.g. immutable-value-ledger) that is NOT already in by_id (populated
baseline, no roadmap seeding) used to be dropped — the coverage ledger then
warned "capability ... not declared in ontology modules" and the static
evidence was lost. The capability must now enter the inventory conservatively
(partial / low confidence / "static evidence only" gap) with the evidence
attached, and the ledger warning must disappear.
"""

from __future__ import annotations

from pathlib import Path

from product_prd_generator import reconcile as recon
from product_prd_generator.reconcile import reconcile

POPULATED_COVERAGE = {
    "scanners": {"specs": {"status": "complete", "artifact_count": 2, "limitations": []}}
}

ONT_WITH_COVERAGE = {
    "modules": {
        "card-core": {
            "name": "卡核心",
            "sub_functions": {
                "ledger": {
                    "name": "账本",
                    "capabilities": ["immutable-value-ledger"],
                    "terms": ["账本"],
                },
            },
        },
    },
    "coverage": {
        "ledger-scope": {
            "change": "add-ledger",
            "commit": "abc123",
            "capabilities": [
                {"id": "immutable-value-ledger", "coverage": "full"},
            ],
        },
    },
}


def _patch_ontology(monkeypatch, tmp_path: Path, data: dict) -> Path:
    ontology = tmp_path / "ontology.yaml"
    import yaml

    ontology.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(recon, "ontology_path_for_project", lambda project: ontology)
    return ontology


def test_direct_evidence_match_seeds_capability_without_spec(monkeypatch, tmp_path, capsys) -> None:
    """No spec/matrix entry: direct match alone must seed the capability conservatively."""
    _patch_ontology(monkeypatch, tmp_path, ONT_WITH_COVERAGE)
    code_map = {
        "project": "lnkcard",
        "scan_coverage": POPULATED_COVERAGE,
        "spec_capabilities": [],
        "direct_evidence": {
            "matches": [
                {
                    "capability_id": "immutable-value-ledger",
                    "kind": "code",
                    "ref": "src/ledger.py:12",
                    "evidence_id": "EV-1",
                    "term": "immutable value ledger",
                    "spec_capability_id": "",
                    "role": "implementation",
                },
            ],
        },
    }
    result = reconcile(code_map, {"project": "lnkcard", "features": []})

    cap = next((c for c in result.capabilities if c.id == "immutable-value-ledger"), None)
    assert cap is not None, "direct-evidence hit must enter capabilities even without spec"
    # conservative grading: static presence only, not existing/verified
    assert cap.reconciled_status == "partial"
    assert cap.confidence == "low"
    assert any("static evidence only" in g for g in cap.gaps)
    # the direct evidence itself must be attached
    assert any(e.kind == "code" and "src/ledger.py" in e.ref for e in cap.evidence)


def test_coverage_ledger_no_warning_for_direct_evidence_capability(monkeypatch, tmp_path, capsys) -> None:
    """Coverage ledger referencing the capability must not warn 'not declared in ontology modules'."""
    _patch_ontology(monkeypatch, tmp_path, ONT_WITH_COVERAGE)
    code_map = {
        "project": "lnkcard",
        "scan_coverage": POPULATED_COVERAGE,
        "spec_capabilities": [
            {"id": "ledger-scope", "status": "existing", "evidence": []},
        ],
        "direct_evidence": {
            "matches": [
                {
                    "capability_id": "immutable-value-ledger",
                    "kind": "code",
                    "ref": "src/ledger.py:12",
                    "evidence_id": "EV-1",
                    "term": "immutable value ledger",
                    "spec_capability_id": "",
                    "role": "implementation",
                },
            ],
        },
    }
    result = reconcile(code_map, {"project": "lnkcard", "features": []})
    out = capsys.readouterr().out
    assert "not declared in ontology modules" not in out

    cap = next(c for c in result.capabilities if c.id == "immutable-value-ledger")
    # ledger full upgrade on a static-only (ledger-only evidence) capability still applies
    assert cap.reconciled_status == "existing"
    assert any(e.kind == "spec" and e.ref == "spec:ledger-scope/spec.md" for e in cap.evidence)
