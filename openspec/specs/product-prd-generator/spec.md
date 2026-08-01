# product-prd-generator

## Purpose

通用产品 PRD 生成 Skill。以现有代码库作为产品基线，结合客户需求、竞品资料、手册、蓝图、
截图和图片证据，生成统一功能清单、差距分析和内部产品 PRD。适用于商管/会员/CRM/供应链等多业务系统，
并支持多产品（商管系统 / langchat / LnkChatBI）配置化扩展。

> **Path 迁移说明**：本 spec 原 delta 引用 `$LANLNK_BASE/out/prd/<project>/output/ontology.yaml`
> 作为项目级配置路径。自 document-control-plane 迁移（commits `73d534e` / `b2611ff`）后，
> 项目级配置的权威路径变为 `$LANLNK_BASE/30-products/<canonical-dir>/ontology.yaml`。
> 路径解析 helper 实现了三级 fallback（30-products → out/prd legacy → config 默认），
> 本 spec 的 scenarios 反映当前权威路径。

## Requirements

### Requirement: Multi-project ontology loading

The skill SHALL support loading product-specific ontology.yaml per `--project` argument, falling back to
商管系统 defaults when project-specific config is absent.

#### Scenario: --project 商管系统 (default, backward compat)

- **WHEN** `_load_aliases(skill_root)` or `_load_ontology()` is called without `project` parameter
- **THEN** ontology is loaded from `$LANLNK_BASE/config/ontology/business-ontology.yaml` (via fallback,
  since no project-specific ontology exists for 商管 in `30-products/mi-cre/`)
- **AND** term-aliases is loaded from `skill_root/references/term-aliases.yaml`
- **AND** behavior is byte-identical to pre-change

#### Scenario: --project langchat

- **WHEN** `_load_aliases(skill_root, project="langchat")` is called
- **AND** `$LANLNK_BASE/30-products/langchat/ontology.yaml` exists
- **THEN** ontology is loaded from that path
- **AND** term-aliases is loaded from `$LANLNK_BASE/30-products/langchat/term-aliases.yaml`
- **AND** 商管 modules (招商/合同/财务/营运/物业/系统/推广/资源) are NOT loaded

#### Scenario: --project LnkChatBI

- **WHEN** `_load_aliases(skill_root, project="LnkChatBI")` is called
- **AND** `$LANLNK_BASE/out/prd/LnkChatBI/output/ontology.yaml` exists (legacy path; LnkChatBI
  not yet migrated to 30-products/)
- **THEN** ontology is loaded from that path
- **AND** term-aliases is loaded from `$LANLNK_BASE/out/prd/LnkChatBI/output/term-aliases.yaml`
- **AND** langchat concepts (Workflow/Capability/SkillRelease) are NOT loaded

#### Scenario: --project 不存在 (fallback)

- **WHEN** `_load_aliases(skill_root, project="不存在的项目")` is called
- **AND** no project-specific ontology exists in any resolved path
- **THEN** ontology is loaded from `$LANLNK_BASE/config/ontology/business-ontology.yaml` (fallback)
- **AND** no exception raised

### Requirement: Configurable competitors root

The skill SHALL support a `--competitors-root` CLI argument to override the default three-hop relative path
used by coverage-validate mode.

#### Scenario: --competitors-root not passed (default)

- **WHEN** `--mode coverage-validate` is invoked without `--competitors-root`
- **THEN** the legacy behavior is preserved: `extra = docs_root.parent.parent.parent / "materials" / "13-competitors"`

#### Scenario: --competitors-root passed

- **WHEN** `--mode coverage-validate --competitors-root /custom/path` is invoked
- **AND** `/custom/path` is a directory
- **THEN** `--extra-docs-root /custom/path` is added to the doc_map command

#### Scenario: --competitors-root passed but path missing

- **WHEN** `--competitors-root /nonexistent` is invoked
- **THEN** `extra.is_dir()` returns False
- **AND** no `--extra-docs-root` is added (silent skip, matches current behavior)

### Requirement: Path resolution helpers

The skill SHALL expose two public helper functions in `product_prd_generator/_paths.py`:

- `ontology_path_for_project(project: str) -> Path`
- `term_aliases_path_for_project(project: str, skill_root: Path) -> Path`

Both MUST:

- Return a `Path` object (never raise on missing project-specific file)
- Implement three-tier fallback semantics (document-control-plane `30-products/` → legacy `out/prd/` → default)
- Be importable from outside the module without side effects
- Resolve `$LANLNK_BASE` at call time (not import time) via `os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk")`

#### Scenario: project-specific ontology exists in 30-products (migrated path)

- **WHEN** `ontology_path_for_project("langchat")` is called
- **AND** `$LANLNK_BASE/30-products/langchat/ontology.yaml` is a file
- **THEN** returns `$LANLNK_BASE/30-products/langchat/ontology.yaml`

#### Scenario: project-specific ontology in legacy out/prd path (pre-migration)

- **WHEN** `ontology_path_for_project("LnkChatBI")` is called
- **AND** no `30-products/LnkChatBI/ontology.yaml` exists (LnkChatBI not in canonical dir map)
- **AND** `$LANLNK_BASE/out/prd/LnkChatBI/output/ontology.yaml` is a file
- **THEN** returns `$LANLNK_BASE/out/prd/LnkChatBI/output/ontology.yaml`

#### Scenario: project-specific ontology missing, fallback engaged

- **WHEN** `ontology_path_for_project("商管系统")` is called
- **AND** no project-specific ontology exists in `30-products/mi-cre/` or `out/prd/商管系统/output/`
- **THEN** returns `$LANLNK_BASE/config/ontology/business-ontology.yaml`
- **AND** does not raise even if the fallback path also does not exist (caller handles missing file)

#### Scenario: project-specific term-aliases exists

- **WHEN** `term_aliases_path_for_project("langchat", skill_root=Path("/skill"))` is called
- **AND** `$LANLNK_BASE/30-products/langchat/term-aliases.yaml` is a file
- **THEN** returns that path (NOT `skill_root/references/term-aliases-langchat.yaml`)

#### Scenario: project-specific term-aliases missing, fallback engaged

- **WHEN** `term_aliases_path_for_project("商管系统", skill_root=Path("/skill"))` is called
- **AND** no project-specific term-aliases exists
- **THEN** returns `/skill/references/term-aliases.yaml`

### Requirement: Project-scoped code scanning rules

The skill SHALL support loading project-specific code-map scanning rules from
`references/code-map-rules-<project>.yaml`, falling back to legacy hardcoded 商管 behavior when the
yaml is missing.

#### Scenario: --project 商管系统 with yaml present (default path)

- **WHEN** `extract(code_root, project="商管系统", skill_root=<skill_root>)` is called
- **AND** `<skill_root>/references/code-map-rules-商管系统.yaml` is a file
- **THEN** rules are loaded from that yaml
- **AND** `specs_root = code_root / "openspec/specs"` (per yaml)
- **AND** `matrix_path = code_root / "artifacts/alignment/product-definition-matrix.md"` (per yaml, matrix.enabled=true)
- **AND** spec_capabilities count and matrix_rows count match pre-Phase-B behavior

#### Scenario: --project langchat with yaml present

- **WHEN** `extract(code_root, project="langchat", skill_root=<skill_root>)` is called
- **AND** `<skill_root>/references/code-map-rules-langchat.yaml` is a file
- **THEN** rules are loaded from that yaml
- **AND** `specs_root = code_root / "openspec/specs"` (per yaml)
- **AND** matrix scanning is skipped (matrix.enabled=false)
- **AND** spec_capabilities contains langchat domain IDs (assistant-workflow-*, api-key-*, admin-*)
- **AND** spec_capabilities does NOT contain 商管 IDs (asset-budget-planning, lease-contract-management)
- **AND** matrix_rows is empty tuple

#### Scenario: --project LnkChatBI with yaml present

- **WHEN** `extract(code_root, project="LnkChatBI", skill_root=<skill_root>)` is called
- **AND** `<skill_root>/references/code-map-rules-LnkChatBI.yaml` is a file
- **THEN** rules are loaded from that yaml
- **AND** matrix scanning is skipped
- **AND** spec_capabilities contains LnkChatBI domain IDs (datasource-*, chat-*, custom-prompt-*)

#### Scenario: yaml missing, fallback engaged (backward compat)

- **WHEN** `extract(code_root, project="X")` is called with `skill_root=None` or yaml missing
- **THEN** legacy hardcoded rules apply
- **AND** `specs_root = code_root / "openspec/specs"`
- **AND** `matrix_path = code_root / "artifacts/alignment/product-definition-matrix.md"`
- **AND** behavior is byte-identical to pre-Phase-B

#### Scenario: unknown project, fallback engaged

- **WHEN** `extract(code_root, project="不存在的项目", skill_root=<skill_root>)` is called
- **AND** `<skill_root>/references/code-map-rules-不存在的项目.yaml` does NOT exist
- **THEN** legacy hardcoded rules apply (no exception)

### Requirement: Code-map rules yaml schema

The skill SHALL recognize a yaml schema for `references/code-map-rules-<project>.yaml` with the following
top-level keys:

- `project`: string (project name)
- `description`: string (short description)
- `specs`: object with `path` (string, relative to code_root)
- `matrix`: object with `enabled` (bool) and `path` (string, only when enabled)
- `future_scanners`: object (optional, for future scanner placeholders; all entries `enabled: false` in Phase B)
- `exclude_paths`: list of strings (glob patterns, applied to all scanners)

#### Scenario: minimal valid yaml

- **WHEN** a yaml file contains only `project`, `specs.path`, `matrix.enabled: false`
- **THEN** loading succeeds
- **AND** `future_scanners` defaults to empty dict
- **AND** `exclude_paths` defaults to empty list

#### Scenario: future_scanners placeholders

- **WHEN** a yaml contains `future_scanners.fastapi_routes.enabled: false` with `include_patterns` and `exclude_patterns`
- **THEN** `_load_code_map_rules` parses the entry without error
- **AND** code_map.py does NOT invoke any fastapi_routes scanner (Phase B scope: schema only, not activation)

### Requirement: Production-ready input directories for non-商管 projects

The skill SHALL have production-ready directory infrastructure for `langchat` and `LnkChatBI` projects under
`$LANLNK_BASE`, mirroring the existing `商管系统` directory conventions.

#### Scenario: langchat raw directory ready

- **WHEN** the user invokes `--project langchat --docs-root $LANLNK_BASE/raw/prd-langchat`
- **THEN** `$LANLNK_BASE/raw/prd-langchat/` exists with subdirectories `00-current-product/`,
  `01-customer-requirements/`, `02-competitors/` (each containing a `.gitkeep` placeholder)
- **AND** the run completes without directory-not-found errors (empty content is acceptable)

#### Scenario: LnkChatBI raw directory ready

- **WHEN** the user invokes `--project LnkChatBI --docs-root $LANLNK_BASE/raw/prd-LnkChatBI`
- **THEN** `$LANLNK_BASE/raw/prd-LnkChatBI/` exists with the same 3 subdirectories
- **AND** the run completes without directory-not-found errors

#### Scenario: langchat incoming directory ready

- **WHEN** the user drops original langchat customer-requirement or competitor files into
  `$LANLNK_BASE/incoming/prd-langchat/`
- **THEN** the directory exists and accepts files
- **AND** `material-importer` skill can read from this path

#### Scenario: LnkChatBI incoming directory ready

- **WHEN** the user drops original LnkChatBI files into `$LANLNK_BASE/incoming/prd-LnkChatBI/`
- **THEN** the directory exists and accepts files

### Requirement: Documentation reflects new paths

The docs repo metadata SHALL list the new langchat/LnkChatBI paths so maintainers can discover them.

#### Scenario: BACKUP.md updated

- **WHEN** a maintainer reads `BACKUP.md` §7 「当前目录结构概览」
- **THEN** they see langchat and LnkChatBI listed alongside 商管系统 in the lanlnk/out/ block
- **AND** the structure matches the actual filesystem

#### Scenario: indexes/lanlnk.md updated

- **WHEN** a maintainer reads `indexes/lanlnk.md` `out/prd/` 子项目 section
- **THEN** they see entries for `prd-langchat/` and `prd/LnkChatBI/` with status 「目录就绪，等待素材」

### Requirement: check-drift.sh compatibility

The new directories SHALL NOT trigger false drift warnings in `check-drift.sh`.

#### Scenario: check-drift.sh passes after Phase C

- **WHEN** `bash /opt/code/docs/scripts/check-drift.sh` is run after Phase C
- **THEN** section [1] 关键文件检查 passes (BACKUP.md etc. exist)
- **AND** section [2] 顶层目录 vs 索引记录 shows no new drift (the script checks `/opt/code/docs/`
  top-level only; new `lanlnk/raw/prd-X/` subdirs are not in scope)
- **AND** section [5] skill 契约最小校验 still passes (bid-doc-master symlink, PRD feature list,
  proposals dir, pricing-basis.yaml all unchanged)

### Requirement: Test coverage for multi-product helpers

The skill SHALL include unit tests covering the fallback semantics of `_paths.ontology_path_for_project`,
`_paths.term_aliases_path_for_project`, and `code_map._load_code_map_rules`.

#### Scenario: pytest discovers and runs all unit tests

- **WHEN** `cd skills/business/product-prd-generator && uv run pytest tests/ -v` is invoked
- **THEN** pytest discovers tests/test_paths.py + tests/test_code_map_rules.py + tests/test_integration_e2e.py
- **AND** all unit tests in test_paths.py (8 scenarios) pass
- **AND** all unit tests in test_code_map_rules.py (5 scenarios) pass
- **AND** integration tests in test_integration_e2e.py either pass (env available) or skip with clear reason

#### Scenario: ontology fallback test passes

- **WHEN** `ontology_path_for_project("不存在的项目")` is invoked in a test
- **THEN** the returned path equals `$LANLNK_BASE/config/ontology/business-ontology.yaml`
- **AND** no exception is raised

### Requirement: SKILL.md reflects multi-product reality

The skill documentation SHALL accurately describe the current multi-product support, removing obsolete
"AI 产品必须手工生成" warning and adding onboarding instructions for new products.

#### Scenario: obsolete warning removed

- **WHEN** a maintainer reads SKILL.md 已知限制 section
- **THEN** the paragraph starting 「AI 产品 PRD 适配说明」 (originally line 472) is removed
- **AND** a brief forward-pointer to 「添加新产品的步骤」 replaces it

#### Scenario: new onboarding section added

- **WHEN** a maintainer reads SKILL.md
- **THEN** a new section 「## 添加新产品的步骤」 exists
- **AND** it documents a 6-step recipe (ontology / term-aliases / raw / incoming / code-map-rules / verify)

### Requirement: troubleshooting.md includes ontology design guidance

The troubleshooting guide SHALL include a section guiding maintainers on how to design ontology for a new project.

#### Scenario: new section accessible

- **WHEN** a maintainer reads references/troubleshooting.md
- **THEN** a section 「## 如何为新项目设计 ontology」 exists
- **AND** it covers: design principles / required fields / anti-patterns / verification method

### Requirement: 复利工程 沉淀 records 4-Phase refactor

The docs repo 复利工程 更新日志 SHALL include an entry summarizing the 4-Phase multi-product refactor experience.

#### Scenario: entry added

- **WHEN** a maintainer reads `/opt/code/docs/opencode/90-复利工程/更新日志.md`
- **THEN** a new entry dated 2026-07-19 exists describing:
  - path 硬编码 → 配置化 fallback 模式
  - skeptical re-scan 发现 Risks 误判（coverage_validate.py + word_export.py）
  - future_scanners 占位 schema 模式
