"""Archive-evidence-driven capability status（按产品 opt-in）。

背景（lnkretail，Owner 裁定 D-020 第 14 项，2026-11-25 落地）：业务 change 归档后 specs
基线不再为空，空基线播种（全部本体能力记 ``present-unconfirmed``）不再触发，OpenSpec
scope ID 会直接成为能力条目。启用本口径的产品，能力清单重建为“产品本体能力清单”，
状态只由 **显式能力映射 + 归档目录 + SHA 绑定的门禁证据** 驱动：

- 被映射的归档 change 通过门禁核验 → 其覆盖的能力记 ``existing``；任一映射注明只覆盖
  部分场景（``coverage: partial``）的记 ``partial``。同一能力可由多个 change 覆盖，
  逐个保留证据；
- 门禁核验：归档目录齐全且 tasks 全部勾选；映射里的 40 位 ``verification_sha`` 是代码仓
  HEAD 的祖先，且归档的 verification-report 引用了它全文或不短于 7 位的缩写；
- 其余本体能力仍为 ``present-unconfirmed``（目标能力，业务实现未扫描）；
- scope ID（技术或业务）不直接进入能力清单；
- 不启用任何代码扫描。

启用方式（code-map rules，按产品）::

    archive_evidence_driven:
      enabled: true
      capability_map: $COMPANY_BASE/30-products/<pid>/ontology/archive-capability-map.yaml

未写该键的产品不进入本模块，行为与启用前一致。能力映射是产品数据，放在 docs 仓的
产品本体目录，由 docs 侧在回写裁定后维护；本模块只读取与核验，任一核验不通过即不晋升
（fail closed），原因写入运行日志。
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .archive_evidence import _count_tasks
from .models import CapabilityStatus, Confidence, EvidenceKind, EvidenceRef, ReconciledCapability

CONFIG_KEY = "archive_evidence_driven"
SEED_STATUS = "present-unconfirmed"
_SKILL_ROOT = Path(__file__).resolve().parents[1]
_COVERAGES = ("full", "partial")
_SHA40 = re.compile(r"[0-9a-f]{40}")
_HEX_TOKEN = re.compile(r"(?<![0-9a-f])([0-9a-f]{7,40})(?![0-9a-f])")
_ARCHIVE_DIR = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})-(?P<change_id>[A-Za-z0-9][A-Za-z0-9-]*)")
_REQUIRED_FILES = ("proposal.md", "tasks.md", "verification-report.md")
_BASE_TOKENS = ("${COMPANY_BASE}", "$COMPANY_BASE", "${LANLNK_BASE}", "$LANLNK_BASE")

_NOT_ARCHIVED_GAP = (
    "该能力为产品本体声明的目标能力，尚无归档 change 覆盖它的业务实现"
    "（code authority: present-unconfirmed；archive-evidence-driven）"
)
_PARTIAL_GAP = "归档门禁证据只覆盖该能力的部分场景"


@dataclass(frozen=True, slots=True)
class GateResult:
    ok: bool
    reason: str
    archive_date: str = ""
    verification_sha: str = ""


@dataclass(frozen=True, slots=True)
class Cover:
    change_id: str
    archive_date: str
    verification_sha: str
    coverage: str
    scope: str


@dataclass(frozen=True, slots=True)
class Promotion:
    """One capability as covered by one or more verified archived changes."""

    covers: tuple[Cover, ...]

    @property
    def coverage(self) -> str:
        return "full" if all(cover.coverage == "full" for cover in self.covers) else "partial"

    @property
    def scope(self) -> str:
        return "；".join(dict.fromkeys(cover.scope for cover in self.covers if cover.scope))


def _rules(project: str) -> Mapping[str, Any]:
    from .code_map import _load_code_map_rules  # lazy: keep the module import graph acyclic

    return _load_code_map_rules(project, _SKILL_ROOT)


def is_enabled(project: str) -> bool:
    """True only when the product's code-map rules opt in (``archive_evidence_driven.enabled: true``)."""
    config = _rules(project).get(CONFIG_KEY)
    return isinstance(config, Mapping) and config.get("enabled") is True


def resolve_capability_map_path(config: Mapping[str, Any]) -> Path | None:
    """Resolve ``capability_map``; ``$COMPANY_BASE`` / ``$LANLNK_BASE`` expand to the company base."""
    raw = config.get("capability_map")
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    base = os.environ.get("COMPANY_BASE") or os.environ.get("LANLNK_BASE")
    if any(token in text for token in _BASE_TOKENS):
        if not base:
            return None
        for token in _BASE_TOKENS:
            text = text.replace(token, base)
    return Path(text)


def load_capability_map(config: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Load the product capability map; any problem returns ``(None, notes)`` so nothing is promoted."""
    path = resolve_capability_map_path(config)
    if path is None:
        return None, ["capability_map 未配置，或公司基座环境变量未设置：不晋升任何能力"]
    if not path.is_file():
        return None, [f"capability_map 不存在：{path}"]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("changes"), list):
        return None, [f"capability_map 形状不符（需 product_id 与 changes 列表）：{path}"]
    return data, []


def _is_ancestor(sha: str, code_root: Path) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(code_root), "merge-base", "--is-ancestor", sha, "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def evaluate_gate(entry: Mapping[str, Any], code_root: Path) -> GateResult:
    """Verify one mapped archived change against its archive directory and gate evidence."""
    change_id = str(entry.get("change_id", "")).strip()
    archive_rel = str(entry.get("archive_dir", "")).strip()
    if not change_id or not archive_rel:
        return GateResult(False, "change_id 或 archive_dir 缺失")
    match = _ARCHIVE_DIR.fullmatch(Path(archive_rel).name)
    if match is None or match.group("change_id") != change_id:
        return GateResult(False, "archive_dir 目录名须为 <YYYY-MM-DD>-<change_id> 且与 change_id 一致")
    archive_dir = code_root / archive_rel
    if not archive_dir.is_dir():
        return GateResult(False, f"归档目录不存在：{archive_rel}")
    for file_name in _REQUIRED_FILES:
        if not (archive_dir / file_name).is_file():
            return GateResult(False, f"归档目录缺 {file_name}")
    completed, total = _count_tasks(archive_dir / "tasks.md")
    if total == 0 or completed != total:
        return GateResult(False, f"tasks 未全部完成（{completed}/{total}）")
    gate = entry.get("gate_evidence")
    sha = str(gate.get("verification_sha", "")).strip() if isinstance(gate, Mapping) else ""
    if not _SHA40.fullmatch(sha):
        return GateResult(False, "gate_evidence.verification_sha 须为 40 位提交 SHA")
    report = (archive_dir / "verification-report.md").read_text(encoding="utf-8")
    if not any(sha.startswith(token) for token in _HEX_TOKEN.findall(report)):
        return GateResult(False, "verification_sha 未出现在归档的 verification-report.md（全文或不短于 7 位的缩写）")
    if not _is_ancestor(sha, code_root):
        return GateResult(False, "verification_sha 不是代码仓 HEAD 的祖先，或 git 不可用")
    return GateResult(True, "ok", match.group("date"), sha)


def evaluate_promotions(
    capability_map: Mapping[str, Any],
    code_root: Path,
    known_ids: set[str] | frozenset[str],
) -> tuple[dict[str, Promotion], list[str]]:
    """Turn verified map entries into ``{capability_id: Promotion}``; everything else is a note."""
    covers: dict[str, list[Cover]] = {}
    notes: list[str] = []
    for entry in capability_map.get("changes", []):
        if not isinstance(entry, Mapping):
            notes.append("changes 条目不是映射，已忽略")
            continue
        change_id = str(entry.get("change_id", "")).strip()
        label = change_id or "<unnamed>"
        gate = evaluate_gate(entry, code_root)
        if not gate.ok:
            notes.append(f"{label}：门禁核验未通过（{gate.reason}），其能力不晋升")
            continue
        for item in entry.get("capabilities") or []:
            if not isinstance(item, Mapping):
                notes.append(f"{label}：capability 条目不是映射，已忽略")
                continue
            cap_id = str(item.get("id", "")).strip()
            coverage = str(item.get("coverage", "full")).strip().lower()
            if cap_id not in known_ids:
                notes.append(f"{label}：{cap_id or '<empty>'} 不在本体能力清单中，已忽略")
            elif coverage not in _COVERAGES:
                notes.append(f"{label}：{cap_id} 的 coverage 须为 full 或 partial，已忽略")
            elif any(cover.change_id == change_id for cover in covers.get(cap_id, [])):
                notes.append(f"{label}：{cap_id} 在同一 change 内重复列出，忽略后一条")
            else:
                covers.setdefault(cap_id, []).append(
                    Cover(
                        change_id=change_id,
                        archive_date=gate.archive_date,
                        verification_sha=gate.verification_sha,
                        coverage=coverage,
                        scope=str(item.get("scope", "")).strip(),
                    )
                )
    return {cap_id: Promotion(tuple(items)) for cap_id, items in covers.items()}, notes


def build_inventory(
    by_id: dict[str, ReconciledCapability],
    ontology_capabilities: tuple[tuple[str, str], ...],
    promotions: Mapping[str, Promotion],
    ontology_ref: str,
) -> dict[str, ReconciledCapability]:
    """Return the ontology capability inventory with archive-evidence-driven statuses."""
    inventory: dict[str, ReconciledCapability] = {}
    for cap_id, cap_name in ontology_capabilities:
        prior = by_id.get(cap_id)
        if prior is not None and prior.reconciled_status == CapabilityStatus.EXPLICITLY_NOT_DO.value:
            inventory[cap_id] = prior  # product override (explicitly-not-do) outranks archive evidence
            continue
        promotion = promotions.get(cap_id)
        if promotion is None:
            if prior is not None and prior.reconciled_status == SEED_STATUS:
                inventory[cap_id] = prior  # already seeded as a target capability by the empty-baseline path
                continue
            inventory[cap_id] = ReconciledCapability(
                id=cap_id,
                name=cap_name,
                code_status=CapabilityStatus.MISSING.value,
                doc_status=CapabilityStatus.EXISTING.value,
                reconciled_status=SEED_STATUS,
                confidence=Confidence.LOW.value,
                gaps=(_NOT_ARCHIVED_GAP,),
                evidence=(EvidenceRef(kind="doc", ref=ontology_ref),),
            )
            continue
        status = CapabilityStatus.EXISTING if promotion.coverage == "full" else CapabilityStatus.PARTIAL
        gaps: tuple[str, ...] = ()
        if promotion.coverage == "partial":
            gaps = (f"{_PARTIAL_GAP}：{promotion.scope}" if promotion.scope else _PARTIAL_GAP,)
        inventory[cap_id] = ReconciledCapability(
            id=cap_id,
            name=cap_name,
            code_status=status.value,
            doc_status=CapabilityStatus.EXISTING.value,
            reconciled_status=status.value,
            confidence=Confidence.MEDIUM.value,
            gaps=gaps,
            evidence=(EvidenceRef(kind="doc", ref=ontology_ref),)
            + tuple(
                EvidenceRef(
                    kind=EvidenceKind.OPENSPEC_ARCHIVE,
                    ref=f"{cover.change_id}@{cover.archive_date}",
                    note=f"archive-verified; gate sha {cover.verification_sha[:12]}; coverage={cover.coverage}",
                )
                for cover in promotion.covers
            ),
        )
    return inventory


def apply_archive_driven_inventory(
    by_id: dict[str, ReconciledCapability],
    project: str,
    code_map: Mapping[str, object],
) -> list[str]:
    """Hook body: rebuild ``by_id`` in place. Returns notes (also printed to the run log)."""
    from .reconcile import _iter_ontology_capabilities, _resolve_project_ontology  # lazy: avoid import cycle

    notes: list[str] = []
    ontology_path = _resolve_project_ontology(project)
    if ontology_path is None:
        notes.append(f"{CONFIG_KEY}: 产品本体不可解析，未重建能力清单")
        return notes
    data = yaml.safe_load(ontology_path.read_text(encoding="utf-8"))
    ontology_capabilities = _iter_ontology_capabilities(data)
    config = _rules(project).get(CONFIG_KEY)
    capability_map, map_notes = load_capability_map(config if isinstance(config, Mapping) else {})
    notes.extend(map_notes)
    promotions: dict[str, Promotion] = {}
    if capability_map is not None:
        promotions, gate_notes = evaluate_promotions(
            capability_map,
            Path(str(code_map.get("source_path", ""))),
            {cap_id for cap_id, _ in ontology_capabilities},
        )
        notes.extend(gate_notes)
    inventory = build_inventory(by_id, ontology_capabilities, promotions, f"ontology:{ontology_path.name}")
    by_id.clear()
    by_id.update(inventory)
    print(
        f"  archive-evidence-driven inventory: {len(inventory)} ontology capabilities; "
        f"promoted {len(promotions)} (existing {sum(1 for p in promotions.values() if p.coverage == 'full')}, "
        f"partial {sum(1 for p in promotions.values() if p.coverage != 'full')}); "
        f"not-archived {len(inventory) - len(promotions)} present-unconfirmed"
    )
    for note in notes:
        print(f"  archive-evidence-driven note: {note}")
    return notes
