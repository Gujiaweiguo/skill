"""Tests for the opt-in archive-evidence-driven capability status.

Each test builds a synthetic code repo with one or two archived changes under tmp_path.
Run with `uv run pytest tests/test_archive_status.py -v`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from product_prd_generator import archive_status, reconcile
from product_prd_generator.models import EvidenceKind, ReconciledCapability

ARCHIVE_REL = "openspec/changes/archive/2026-11-24-s1-demo"
SECOND_REL = "openspec/changes/archive/2026-11-25-s1-second"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _archive_files(archive: Path, tasks: str, citation: str) -> None:
    archive.mkdir(parents=True)
    (archive / "proposal.md").write_text("# demo\n", encoding="utf-8")
    (archive / "tasks.md").write_text(tasks, encoding="utf-8")
    (archive / "verification-report.md").write_text(
        f"## Formal evidence\n\nEvidence bound to `{citation}`.\n", encoding="utf-8"
    )


def _repo(
    tmp_path: Path,
    *,
    tasks: str = "- [x] 1.1 done\n",
    cite: str | None = None,
    cite_len: int = 40,
    git: bool = True,
) -> tuple[Path, str]:
    root = tmp_path / "code"
    root.mkdir(parents=True)
    head = "0" * 40
    if git:
        _git(root, "init", "-q")
        (root / "README.md").write_text("demo\n")
        _git(root, "add", "README.md")
        _git(root, "commit", "-q", "-m", "init")
        head = _git(root, "rev-parse", "HEAD")
    _archive_files(root / ARCHIVE_REL, tasks, (cite or head)[:cite_len])
    if git:
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "archive")
    return root, head


def _second_archive(root: Path, sha: str) -> None:
    _archive_files(root / SECOND_REL, "- [x] 2.1 done\n", sha)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "second archive")


def _entry(sha: str, capabilities: list[dict[str, str]] | None = None, **overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "change_id": "s1-demo",
        "archive_dir": ARCHIVE_REL,
        "gate_evidence": {"verification_sha": sha},
        "capabilities": [{"id": "cap-a", "coverage": "full"}] if capabilities is None else capabilities,
    }
    entry.update(overrides)
    return entry


def _cap(cap_id: str, status: str = "existing") -> ReconciledCapability:
    return ReconciledCapability(
        id=cap_id, name=cap_id, code_status=status, doc_status="existing",
        reconciled_status=status, confidence="high",
    )


def _cover(coverage: str = "full", scope: str = "", change_id: str = "s1-demo") -> archive_status.Cover:
    return archive_status.Cover(change_id, "2026-11-24", "a" * 40, coverage, scope)


# --- gate verification -----------------------------------------------------


def test_gate_passes_for_archived_change_with_cited_ancestor_sha(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    result = archive_status.evaluate_gate(_entry(head), root)
    assert result.ok, result.reason
    assert (result.archive_date, result.verification_sha) == ("2026-11-24", head)


@pytest.mark.parametrize("cite_len", [7, 8, 12])
def test_gate_accepts_an_abbreviation_cited_in_the_report(tmp_path: Path, cite_len: int) -> None:
    root, head = _repo(tmp_path, cite_len=cite_len)
    result = archive_status.evaluate_gate(_entry(head), root)
    assert result.ok, result.reason


def test_gate_fails_closed(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    assert "verification-report" in archive_status.evaluate_gate(_entry("c" * 40), root).reason
    assert "verification-report" in archive_status.evaluate_gate(_entry(head[:6] + "0" * 34), root).reason
    assert "40 位" in archive_status.evaluate_gate(_entry("abc123"), root).reason
    assert "目录名" in archive_status.evaluate_gate(_entry(head, change_id="other-id"), root).reason

    unchecked, unchecked_head = _repo(tmp_path / "unchecked", tasks="- [x] 1.1\n- [ ] 1.2\n")
    assert "tasks" in archive_status.evaluate_gate(_entry(unchecked_head), unchecked).reason

    not_ancestor, _ = _repo(tmp_path / "not-ancestor", cite="c" * 40)
    assert "祖先" in archive_status.evaluate_gate(_entry("c" * 40), not_ancestor).reason

    missing, missing_head = _repo(tmp_path / "missing")
    subprocess.run(["rm", "-rf", str(missing / ARCHIVE_REL)], check=True)
    assert "归档目录不存在" in archive_status.evaluate_gate(_entry(missing_head), missing).reason

    no_git, _ = _repo(tmp_path / "nogit", cite="a" * 40, git=False)
    assert "祖先" in archive_status.evaluate_gate(_entry("a" * 40), no_git).reason


# --- promotion evaluation --------------------------------------------------


def test_evaluate_promotions_keeps_only_verified_known_capabilities(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    capability_map = {
        "changes": [
            _entry(head, [
                {"id": "cap-a", "coverage": "full"},
                {"id": "cap-b", "coverage": "partial", "scope": "settlement-price scene only"},
                {"id": "not-in-ontology", "coverage": "full"},
                {"id": "cap-c", "coverage": "maybe"},
                "not-a-mapping",
            ]),
            _entry("c" * 40, [{"id": "cap-d", "coverage": "full"}]),  # gate fails: sha not cited
        ]
    }
    promotions, notes = archive_status.evaluate_promotions(capability_map, root, {"cap-a", "cap-b", "cap-c", "cap-d"})
    assert set(promotions) == {"cap-a", "cap-b"}
    assert (promotions["cap-a"].coverage, promotions["cap-a"].covers[0].verification_sha) == ("full", head)
    assert (promotions["cap-b"].coverage, promotions["cap-b"].scope) == ("partial", "settlement-price scene only")
    joined = "; ".join(notes)
    for needle in ("not-in-ontology", "cap-c 的 coverage", "不是映射", "s1-demo：门禁核验未通过"):
        assert needle in joined


def test_repeated_capability_within_one_change_is_reported_not_merged(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    capability_map = {"changes": [
        _entry(head, [{"id": "cap-a", "coverage": "full"}, {"id": "cap-a", "coverage": "partial"}]),
        _entry(head, [{"id": "cap-a", "coverage": "partial"}]),
    ]}
    promotions, notes = archive_status.evaluate_promotions(capability_map, root, {"cap-a"})
    assert [cover.coverage for cover in promotions["cap-a"].covers] == ["full"]
    assert sum("重复" in note for note in notes) == 2


def test_capability_covered_by_several_changes_keeps_every_piece_of_evidence(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    _second_archive(root, head)
    capability_map = {"changes": [
        _entry(head, [{"id": "cap-a", "coverage": "full"}]),
        _entry(head, [{"id": "cap-a", "coverage": "partial", "scope": "in-transit only"}],
                change_id="s1-second", archive_dir=SECOND_REL),
    ]}
    promotions, notes = archive_status.evaluate_promotions(capability_map, root, {"cap-a"})
    assert notes == []
    promotion = promotions["cap-a"]
    assert [(cover.change_id, cover.coverage) for cover in promotion.covers] == [("s1-demo", "full"), ("s1-second", "partial")]
    assert (promotion.coverage, promotion.scope) == ("partial", "in-transit only")
    built = archive_status.build_inventory({}, (("cap-a", "A"),), promotions, "ontology:o.yaml")
    archive_refs = [e.ref for e in built["cap-a"].evidence if e.kind == EvidenceKind.OPENSPEC_ARCHIVE]
    assert archive_refs == ["s1-demo@2026-11-24", "s1-second@2026-11-25"]
    assert built["cap-a"].gaps == (f"{archive_status._PARTIAL_GAP}：in-transit only",)


# --- inventory rebuild -----------------------------------------------------


def test_build_inventory_promotes_seeds_and_keeps_override() -> None:
    promotions = {
        "cap-a": archive_status.Promotion((_cover("full"),)),
        "cap-b": archive_status.Promotion((_cover("partial", "scene x only"),)),
    }
    by_id = {"identity": _cap("identity"), "cap-c": _cap("cap-c", "explicitly-not-do")}
    inventory = archive_status.build_inventory(
        by_id, (("cap-a", "A"), ("cap-b", "B"), ("cap-c", "C"), ("cap-d", "D")), promotions, "ontology:ontology.yaml"
    )
    assert list(inventory) == ["cap-a", "cap-b", "cap-c", "cap-d"]
    assert "identity" not in inventory
    assert (inventory["cap-a"].reconciled_status, inventory["cap-a"].gaps) == ("existing", ())
    assert (inventory["cap-b"].reconciled_status, inventory["cap-b"].gaps) == (
        "partial", (f"{archive_status._PARTIAL_GAP}：scene x only",)
    )
    assert inventory["cap-a"].evidence[1].kind == EvidenceKind.OPENSPEC_ARCHIVE
    assert inventory["cap-a"].evidence[1].ref == "s1-demo@2026-11-24"
    assert inventory["cap-c"].reconciled_status == "explicitly-not-do"
    seeded = inventory["cap-d"]
    assert (seeded.reconciled_status, seeded.code_status, seeded.doc_status, seeded.confidence) == (
        archive_status.SEED_STATUS, "missing", "existing", "low"
    )
    assert seeded.gaps == (archive_status._NOT_ARCHIVED_GAP,)


def test_build_inventory_resets_spec_scan_status_when_not_promoted() -> None:
    inventory = archive_status.build_inventory({"cap-a": _cap("cap-a")}, (("cap-a", "A"),), {}, "ontology:o.yaml")
    assert inventory["cap-a"].reconciled_status == archive_status.SEED_STATUS
    assert inventory["cap-a"].gaps == (archive_status._NOT_ARCHIVED_GAP,)


def test_build_inventory_keeps_existing_target_capability_seed() -> None:
    seeded = ReconciledCapability(
        id="cap-a", name="A", code_status="missing", doc_status="existing",
        reconciled_status=archive_status.SEED_STATUS, confidence="low", gaps=("empty-baseline: 骨架仓",),
    )
    inventory = archive_status.build_inventory({"cap-a": seeded}, (("cap-a", "A"),), {}, "ontology:o.yaml")
    assert inventory["cap-a"] is seeded


# --- opt-in switch and map location ----------------------------------------


@pytest.mark.parametrize(
    "rules, expected",
    [({}, False), ({"archive_evidence_driven": {"enabled": False}}, False),
     ({"archive_evidence_driven": {"enabled": "true"}}, False),
     ({"archive_evidence_driven": {"enabled": True}}, True)],
)
def test_is_enabled_only_by_explicit_opt_in(monkeypatch: pytest.MonkeyPatch, rules: dict[str, object], expected: bool) -> None:
    monkeypatch.setattr(archive_status, "_rules", lambda project: rules)
    assert archive_status.is_enabled("any-product") is expected


def test_capability_map_path_expands_company_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPANY_BASE", raising=False)
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    text = "$COMPANY_BASE/30-products/p/ontology/archive-capability-map.yaml"
    assert archive_status.resolve_capability_map_path({"capability_map": text}) is None
    monkeypatch.setenv("LANLNK_BASE", "/base")
    assert archive_status.resolve_capability_map_path({"capability_map": text}) == Path(
        "/base/30-products/p/ontology/archive-capability-map.yaml"
    )
    assert archive_status.resolve_capability_map_path({"capability_map": "/abs/map.yaml"}) == Path("/abs/map.yaml")
    assert archive_status.resolve_capability_map_path({}) is None


def test_load_capability_map_fails_closed(tmp_path: Path) -> None:
    assert archive_status.load_capability_map({})[0] is None
    assert archive_status.load_capability_map({"capability_map": str(tmp_path / "absent.yaml")})[0] is None
    bad = tmp_path / "bad.yaml"
    bad.write_text("product_id: p\n", encoding="utf-8")
    assert archive_status.load_capability_map({"capability_map": str(bad)})[0] is None


# --- hook end to end -------------------------------------------------------


def test_apply_rebuilds_by_id_in_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ontology = tmp_path / "ontology.yaml"
    ontology.write_text(
        "modules:\n  - id: m1\n    sub_functions:\n      - id: s1\n        name: S1\n"
        "        capabilities:\n          - id: cap-a\n          - id: cap-b\n",
        encoding="utf-8",
    )
    root, head = _repo(tmp_path)
    capability_map = tmp_path / "archive-capability-map.yaml"
    capability_map.write_text(
        "product_id: p\nchanges:\n  - change_id: s1-demo\n"
        f"    archive_dir: {ARCHIVE_REL}\n    gate_evidence:\n      verification_sha: {head}\n"
        "    capabilities:\n      - { id: cap-a, coverage: full }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(reconcile, "_resolve_project_ontology", lambda project: ontology)
    monkeypatch.setattr(
        archive_status, "_rules",
        lambda project: {"archive_evidence_driven": {"enabled": True, "capability_map": str(capability_map)}},
    )
    by_id = {"identity": _cap("identity")}
    notes = archive_status.apply_archive_driven_inventory(by_id, "p", {"source_path": str(root)})
    assert notes == []
    assert list(by_id) == ["cap-a", "cap-b"]
    assert by_id["cap-a"].reconciled_status == "existing"
    assert by_id["cap-b"].reconciled_status == archive_status.SEED_STATUS
