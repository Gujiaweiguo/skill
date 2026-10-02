from __future__ import annotations

from product_prd_generator.coverage_validate import (
    build_baseline,
    build_run_identity,
    detect_delta,
)


def _requirement() -> dict[str, str]:
    return {
        "source_type": "customer-requirements",
        "source_customer": "customer-a",
        "normalized_term": "capability-a",
        "function": "Capability A",
        "nearby_text": "Current requirement text",
        "matched_capability": "capability-a",
        "priority": "高",
    }


def _reconcile(revision: str) -> dict[str, object]:
    return {
        "project": "lnkchat",
        "source_revision": revision,
        "scan_coverage": {
            "status": "partial",
            "scope": ["configured OpenSpec specs", "direct runtime code", "direct tests"],
        },
        "capabilities": [
            {
                "id": "capability-a",
                "reconciled_status": "existing",
                "evidence": [{"kind": "spec", "ref": "spec.md"}],
            },
        ],
        "requirements": [_requirement()],
    }


def test_run_identity_is_stable_for_same_inputs() -> None:
    doc_map = {"features": [], "requirements": [_requirement()]}

    first = build_run_identity("lnkchat", _reconcile("rev-a"), doc_map)
    second = build_run_identity("lnkchat", _reconcile("rev-a"), doc_map)

    assert first == second
    assert first["run_fingerprint"]


def test_revision_only_change_is_evidence_only() -> None:
    requirements = [_requirement()]
    doc_map = {"features": [], "requirements": requirements}
    old_reconcile = _reconcile("rev-a")
    new_reconcile = _reconcile("rev-b")
    baseline = build_baseline(
        requirements,
        project="lnkchat",
        reconcile=old_reconcile,
        doc_map=doc_map,
    )

    delta = detect_delta(
        requirements,
        baseline,
        build_run_identity("lnkchat", new_reconcile, doc_map),
    )

    assert delta.comparison_status == "evidence-only-change"
    assert delta.evidence_only_change is True
    assert delta.product_input_changed is False
    assert delta.new_items == ()
    assert delta.dropped_count == 0
    assert delta.modified_count == 0


def test_product_input_change_is_not_evidence_only() -> None:
    old_requirements = [_requirement()]
    new_requirements = [{**_requirement(), "nearby_text": "Changed product requirement"}]
    old_doc_map = {"features": [], "requirements": old_requirements}
    new_doc_map = {"features": [], "requirements": new_requirements}
    baseline = build_baseline(
        old_requirements,
        project="lnkchat",
        reconcile=_reconcile("rev-a"),
        doc_map=old_doc_map,
    )

    delta = detect_delta(
        new_requirements,
        baseline,
        build_run_identity("lnkchat", _reconcile("rev-b"), new_doc_map),
    )

    assert delta.comparison_status == "product-input-change"
    assert delta.product_input_changed is True
    assert delta.evidence_only_change is False
    assert delta.modified_count == 1
