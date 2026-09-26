"""Project-scoped path resolution for product-prd-generator config files.

Resolution priority (post lnkcre 目录统一，2026-09):

- canonical_product_id(raw):
    别名归一。MI / MI-CRE / LnkCRE / lnkcre / 商管系统 → ``lnkcre``；
    langchat / lnkchat → ``lnkchat``。未知产品返回清洗后的原名（走
    out/prd/<project>/output/ legacy 链路，不静默映射到其他产品）。

- resolve_product_paths(project) -> ProductPaths:
    LnkCRE 统一路径契约（唯一权威源，SKILL.md / registry / 各脚本共用）：
    - canonical docs_root   = $BASE/30-products/lnkcre/
    - ontology_root         = $BASE/30-products/lnkcre/ontology/
    - prd_root              = $BASE/30-products/lnkcre/prd/
    - feature_baseline_path = $BASE/30-products/lnkcre/prd/baseline/feature-baseline.yaml
    - competitor_evidence_root = $BASE/30-products/lnkcre/evidence/competitors/
    - legacy_fallback_enabled = False（docs 仓 mi-cre→lnkcre 合并已完成，2026-09 三层整理）

- ontology_path_for_project(project):
    1. $LANLNK_BASE/30-products/<canonical-dir>/ontology/ontology.yaml  (lnkcre 三层目录)
    2. $LANLNK_BASE/30-products/<canonical-dir>/ontology.yaml           (扁平变体，如 lnkchat)
    3. $LANLNK_BASE/out/prd/<project>/output/ontology.yaml              (legacy)
    4. $LANLNK_BASE/config/ontology/business-ontology.yaml              (lnkcre 注册入口/兜底)

- term_aliases_path_for_project(project, skill_root):
    同上三级 + <skill_root>/references/term-aliases.yaml 兜底。

- feature_baseline_path_for_project / domain_knowledge_path_for_project /
  competitor_evidence_paths_for_project:
    canonical 路径不存在时 raise MissingProductDataError（错误信息含产品 ID +
    全部尝试路径），绝不静默回退到其他产品（如 lnkreport / lnkchat）。

MI-* / MI-CRE-* 是历史稳定文档 ID，不代表目录仍叫 mi-cre；不要批量改写
历史文件名、历史 commit 或历史 source_ref。新生成文件与 registry 记录用
LnkCRE / lnkcre。

Canonical layout note (2026-09-26 方案 B 家族迁移): lnkreport / lnkchatbi /
lnkvision 的 canonical PRD 家族与本体已迁入 30-products/<pid>/{prd,ontology}/，
out/prd/ 降为纯生成区（skill 生成产物仍落 out/，经 owner 审后晋升并入
canonical，双源不并存）。canonical 布局登记见 references/product-registry.yaml；
本模块的代码默认输出仍是生成区 out/prd/<project>/output/，不改行为。
已知缺口：_PRODUCT_CANONICAL_DIR 尚未登记上述三个产品，
ontology/term-aliases 解析暂不能命中它们的新 canonical 位置
（见 SKILL.md「已知限制」——补条目属代码行为变更，须另行批准）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ─── LnkCRE canonical / legacy 目录契约 ────────────────────────────────

LNKCRE_CANONICAL_DIR = "lnkcre"
LNKCRE_LEGACY_DIR = "mi-cre"  # 历史目录段（30-products/mi-cre 已于 2026-09 合并删除）；仅用于历史路径段识别（doc 扫描过滤），不参与路径 fallback

# canonical product id 归一表（key 一律小写比较；中文原样）。
# MI / MI-CRE 是 LnkCRE 的历史代号，MI-* / MI-CRE-* 文档 ID 保持不变。
_PRODUCT_ALIASES: dict[str, str] = {
    # LnkCRE 商管系统家族
    "lnkcre": "lnkcre",
    "mi": "lnkcre",
    "mi-cre": "lnkcre",
    "mi_cre": "lnkcre",
    "商管系统": "lnkcre",
    # LnkChat 岗位 AI 家族（目录已统一 30-products/lnkchat/）
    "lnkchat": "lnkchat",
    "langchat": "lnkchat",
}

# 每个产品的"目录段别名"——doc_map 产品过滤用它识别属于该产品的路径段。
# lnkcre 迁移期同时认 canonical 段和 legacy 段（读取兼容，写入只进 canonical）。
_PRODUCT_DIR_SEGMENTS: dict[str, tuple[str, ...]] = {
    "lnkcre": (LNKCRE_CANONICAL_DIR, LNKCRE_LEGACY_DIR, "商管系统"),
    "lnkchat": ("lnkchat", "langchat"),
}

# PRD 产物细分目录（requirement：基线/增量/需求/决策/交接 各归其位）。
# 仅对已有 30-products/<product>/prd/ 三层目录的产品生效。
PRD_OUTPUT_SUBDIRS: dict[str, str] = {
    "baseline": "baseline",        # 产品基线 / 首版全量 PRD
    "increments": "increments",    # 增量 PRD
    "requirements": "requirements",  # 客户需求汇总 / 需求清单
    "decisions": "decisions",      # 产品决策（ADR / 裁决包）
    "handoffs": "handoffs",        # 实施交接 / 提示词 / 回传件
}


class MissingProductDataError(RuntimeError):
    """canonical 与 legacy 路径都不存在时抛出；错误信息必须含产品 ID 和全部尝试路径。"""


def canonical_product_id(raw: str) -> str:
    """把用户/CLI 输入的产品代号归一到 canonical product id。

    MI、MI-CRE、LnkCRE、lnkcre、商管系统 → ``lnkcre``（大小写不敏感）。
    未知产品返回 strip 后的原文（保持 out/prd/<project>/ 链路可用），
    绝不静默映射到另一个产品。
    """
    cleaned = (raw or "").strip()
    return _PRODUCT_ALIASES.get(cleaned.lower(), cleaned) if cleaned else cleaned


def is_lnkre_product(project: str) -> bool:
    """project 是否属于 LnkCRE（商管）产品家族——域专属逻辑的总开关。"""
    return canonical_product_id(project) == "lnkcre"


def product_dir_aliases(project: str) -> tuple[str, ...]:
    """属于该产品的路径段集合（用于 doc 扫描过滤；含迁移期 legacy 段）。"""
    cid = canonical_product_id(project)
    known = _PRODUCT_DIR_SEGMENTS.get(cid)
    if known:
        return known
    # 未知/新产品：精确段 + 大小写变体（行为对齐旧版 exact-segment 过滤）
    return (project, project.lower()) if project != project.lower() else (project,)


def _legacy_fallback_enabled() -> bool:
    """迁移期兼容开关。docs 仓 mi-cre → lnkcre 合并已于 2026-09 完成（三层整理，
    证据：30-products/product-registry-feedback.yaml），fallback 关闭。"""
    return False


@dataclass(frozen=True)
class ProductPaths:
    """LnkCRE（及未来三层目录产品）的统一路径契约。

    所有字段均为"目标路径"，不保证存在；存在性判断和 fallback 顺序由
    feature_baseline_path_for_project 等解析函数负责。
    """

    canonical_product_id: str
    docs_root: Path                      # canonical 产品根（30-products/lnkcre）
    ontology_root: Path                  # 本体入口目录（…/lnkcre/ontology）
    prd_root: Path                       # PRD 层根（…/lnkcre/prd）
    feature_baseline_path: Path          # 功能基线（…/prd/baseline/feature-baseline.yaml）
    competitor_evidence_root: Path       # 竞品证据（…/evidence/competitors）
    legacy_docs_root: Path | None = None  # 历史 legacy 根（30-products/mi-cre，已于 2026-09 删除；fallback 关闭后仅描述性字段）
    legacy_feature_baseline_path: Path | None = None
    legacy_competitor_root: Path | None = None
    legacy_fallback_enabled: bool = field(default_factory=_legacy_fallback_enabled)

    def prd_output_dir(self, kind: str = "baseline") -> Path:
        """PRD 产物细分目录：baseline/increments/requirements/decisions/handoffs。"""
        try:
            return self.prd_root / PRD_OUTPUT_SUBDIRS[kind]
        except KeyError as exc:
            raise ValueError(
                f"未知 PRD 输出分类 {kind!r}；可选：{sorted(PRD_OUTPUT_SUBDIRS)}"
            ) from exc


def resolve_product_paths(project: str) -> ProductPaths:
    """解析产品的统一路径契约。目前仅 lnkcre 有完整三层目录；其他产品返回
    其 canonical 目录（如存在）的等价结构，不携带 legacy 字段。"""
    base = _lanlnk_base()
    cid = canonical_product_id(project)
    products_dir = base / "30-products"

    if cid == "lnkcre":
        docs_root = products_dir / LNKCRE_CANONICAL_DIR
        legacy_root = products_dir / LNKCRE_LEGACY_DIR
        return ProductPaths(
            canonical_product_id=cid,
            docs_root=docs_root,
            ontology_root=docs_root / "ontology",
            prd_root=docs_root / "prd",
            feature_baseline_path=docs_root / "prd" / "baseline" / "feature-baseline.yaml",
            competitor_evidence_root=docs_root / "evidence" / "competitors",
            legacy_docs_root=legacy_root,
            legacy_feature_baseline_path=legacy_root / "feature-baseline" / "feature-baseline.yaml",
            legacy_competitor_root=legacy_root / "competitor-analysis",
            legacy_fallback_enabled=_legacy_fallback_enabled(),
        )

    if cid == "lnkchat":
        docs_root = products_dir / "lnkchat"
        return ProductPaths(
            canonical_product_id=cid,
            docs_root=docs_root,
            ontology_root=docs_root,
            prd_root=docs_root / "prd",
            feature_baseline_path=docs_root / "prd" / "baseline" / "feature-baseline.yaml",
            competitor_evidence_root=docs_root / "evidence" / "competitors",
        )

    # 未知/未注册三层目录的产品：canonical 目录按产品 id 推导，不编造 legacy。
    docs_root = products_dir / cid
    return ProductPaths(
        canonical_product_id=cid,
        docs_root=docs_root,
        ontology_root=docs_root / "ontology",
        prd_root=docs_root / "prd",
        feature_baseline_path=docs_root / "prd" / "baseline" / "feature-baseline.yaml",
        competitor_evidence_root=docs_root / "evidence" / "competitors",
    )


def feature_baseline_path_for_project(project: str) -> Path:
    """功能基线：canonical 优先，legacy 仅迁移期 fallback，都缺则显式报错。"""
    paths = resolve_product_paths(project)
    if paths.feature_baseline_path.is_file():
        return paths.feature_baseline_path
    legacy = paths.legacy_feature_baseline_path if paths.legacy_fallback_enabled else None
    if legacy and legacy.is_file():
        return legacy
    raise MissingProductDataError(
        f"产品 {paths.canonical_product_id!r}（输入 {project!r}）的功能基线不存在。"
        f"尝试路径：\n  - canonical: {paths.feature_baseline_path}"
        + (f"\n  - legacy（迁移期）: {legacy}" if legacy else "")
        + "\n请在 docs 仓补齐 30-products/"
        + (LNKCRE_CANONICAL_DIR if paths.canonical_product_id == "lnkcre" else paths.canonical_product_id)
        + "/prd/baseline/feature-baseline.yaml。"
    )


def domain_knowledge_path_for_project(project: str) -> Path:
    """域知识入口解析（只读指引；返回最优先的**存在**入口）。

    优先级（requirement 契约）：
      a. 30-products/lnkcre/ontology/domain-knowledge.md
      b. 30-products/lnkcre/ontology/README.md（入口指向实际 authority）
      c. 30-products/lnkcre/INDEX.md（声明的 authority / source_ref）
    （mi-cre 迁移期 fallback 已随 2026-09 目录合并移除）
    """
    paths = resolve_product_paths(project)
    candidates = [
        paths.ontology_root / "domain-knowledge.md",
        paths.ontology_root / "README.md",
        paths.docs_root / "INDEX.md",
    ]
    if paths.legacy_fallback_enabled and paths.legacy_docs_root:
        candidates.append(paths.legacy_docs_root / "domain-knowledge.md")
    for cand in candidates:
        if cand.is_file():
            return cand
    listing = "\n".join(f"  - {c}" for c in candidates)
    raise MissingProductDataError(
        f"产品 {paths.canonical_product_id!r}（输入 {project!r}）的域知识入口不存在。"
        f"尝试路径（按优先级）：\n{listing}"
    )


def competitor_evidence_paths_for_project(project: str) -> tuple[Path, Path | None]:
    """竞品证据目录：(canonical 写入根, legacy 读取根或 None)。

    新生成的竞品分析 / .auth.json / 能力矩阵一律写入 canonical 根；
    legacy 根仅在迁移期用于读取（不得写入）。
    """
    paths = resolve_product_paths(project)
    legacy = (
        paths.legacy_competitor_root
        if paths.legacy_fallback_enabled and paths.legacy_competitor_root
        else None
    )
    return paths.competitor_evidence_root, legacy


# ─── 兼容层：ontology / term-aliases 既有解析链 ────────────────────────

_PRODUCT_CANONICAL_DIR: dict[str, str] = {
    "商管系统": LNKCRE_CANONICAL_DIR,
    "mi": LNKCRE_CANONICAL_DIR,
    "mi-cre": LNKCRE_CANONICAL_DIR,
    "mi_cre": LNKCRE_CANONICAL_DIR,
    "lnkcre": LNKCRE_CANONICAL_DIR,
    # langchat 产品目录已在 docs 仓改名 30-products/lnkchat/（对齐 /opt/code/lnkchat），
    # 新旧项目代号都解析到现行目录。
    "langchat": "lnkchat",
    "lnkchat": "lnkchat",
    # lnkcrm（商圈会员 CRM）2026-09-26 docs 侧 onboarding：30-products/lnkcrm/ontology/
    # 已有 draft ontology v0.1（147 功能清单证据锚定）。必须注册——未注册的 CRM 会话
    # 会静默回落商管 business-ontology（registry 规则 2 明令禁止的跨域回落）。
    "lnkcrm": "lnkcrm",
}


def _canonical_dirs_for(project: str) -> list[str]:
    """按优先级返回该产品的 30-products/ 候选目录名（canonical 在前，legacy 迁移期垫后）。"""
    cid = canonical_product_id(project)
    if cid == "lnkcre":
        dirs = [LNKCRE_CANONICAL_DIR]
        if _legacy_fallback_enabled():
            dirs.append(LNKCRE_LEGACY_DIR)
        return dirs
    canonical = _PRODUCT_CANONICAL_DIR.get(project, _PRODUCT_CANONICAL_DIR.get(project.lower()))
    return [canonical] if canonical else []


def _lanlnk_base() -> Path:
    """解析文档控制面基座（COMPANIES.md §3：COMPANY_BASE ∥ LANLNK_BASE，无静默默认）。

    绝不回落 /opt/code/docs/lanlnk——未设置、相对路径或缺 config/company.yaml
    时报错退出，防止其他公司会话静默读写 lanlnk 的 PRD 资料。
    """
    base = os.environ.get("COMPANY_BASE") or os.environ.get("LANLNK_BASE")
    if not base:
        raise SystemExit(
            "错误: 未设置 COMPANY_BASE（或兼容变量 LANLNK_BASE）。\n"
            "  export COMPANY_BASE=/opt/code/docs/<company>   # 如 lianyou / lanlnk"
        )
    path = Path(base)
    if not path.is_absolute():
        raise SystemExit(
            f"错误: COMPANY_BASE 必须是绝对路径（当前: {base}）。\n"
            "  export COMPANY_BASE=/opt/code/docs/<company>"
        )
    if not (path / "config" / "company.yaml").is_file():
        raise SystemExit(
            f"错误: {path} 不是已注册公司（缺 config/company.yaml）。\n"
            "  新公司请在 docs 仓库运行 scripts/onboard.sh company <slug> 创建。"
        )
    return path


def ontology_path_for_project(project: str) -> Path:
    base = _lanlnk_base()

    for subdir in _canonical_dirs_for(project):
        nested = base / "30-products" / subdir / "ontology" / "ontology.yaml"
        if nested.is_file():
            return nested
        flat = base / "30-products" / subdir / "ontology.yaml"
        if flat.is_file():
            return flat

    legacy = base / "out" / "prd" / project / "output" / "ontology.yaml"
    if legacy.is_file():
        return legacy

    return base / "config" / "ontology" / "business-ontology.yaml"


def term_aliases_path_for_project(project: str, skill_root: Path) -> Path:
    base = _lanlnk_base()

    for subdir in _canonical_dirs_for(project):
        nested = base / "30-products" / subdir / "ontology" / "term-aliases.yaml"
        if nested.is_file():
            return nested
        flat = base / "30-products" / subdir / "term-aliases.yaml"
        if flat.is_file():
            return flat

    legacy = base / "out" / "prd" / project / "output" / "term-aliases.yaml"
    if legacy.is_file():
        return legacy

    return skill_root / "references" / "term-aliases.yaml"


def codebase_features_path_for_project(project: str) -> Path:
    """Return the optional curated code-feature map for a project."""
    base = _lanlnk_base()
    return base / "raw" / f"prd-{project}" / "parsed" / "codebase-features.json"


def overrides_path_for_project(project: str) -> Path:
    """Return the optional manual capability-override file for a project.

    Applied AFTER archive evidence so project-specific facts (deliberate
    stubs, marketing-vs-code gaps, code-only capabilities) are not swept
    away by the archive-to-existing promotion.
    """
    base = _lanlnk_base()
    return base / "raw" / f"prd-{project}" / "parsed" / "capability-overrides.yaml"


class InvalidProjectError(ValueError):
    """Raised when --project contains path-traversal or otherwise unsafe characters."""


def validate_project(raw: str) -> str:
    """CLI boundary parser for --project: reject path-unsafe inputs.

    Project names are interpolated into filesystem paths (raw/prd-<project>/...,
    out/prd/<project>/...). Reject separators, traversal, and empty strings so
    a hostile or mistyped value cannot redirect file reads outside $LANLNK_BASE.
    """
    if not raw or not raw.strip():
        raise InvalidProjectError("--project must not be empty")
    cleaned = raw.strip()
    for fragment in ("/", "\\", ".."):
        if fragment in cleaned:
            raise InvalidProjectError(
                f"--project contains forbidden fragment {fragment!r}: {raw!r}",
            )
    for char in cleaned:
        if char < " " or char == "\x7f":
            raise InvalidProjectError(
                f"--project contains control character: {raw!r}",
            )
    return cleaned
