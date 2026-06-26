# AGENTS.md

## Repository Purpose

OpenCode skills repository for 蓝联科技 (Lanlnk). **Skill definitions** (markdown) + **rendering engines** (Python/Node.js). No runtime web app.

Two skill types:
- **OpenSpec skills** (10) in `.opencode/skills/openspec-*/` — REAL directories (not symlinks). Bundled upstream, **read-only**.
- **Custom skills** (12) in `skills/<category>/<name>/` — symlinks from `.opencode/skills/<name>`.

## Critical Paths

| What | Where |
|------|-------|
| Edit skills here | `skills/<category>/<name>/` |
| OpenCode symlinks | `.opencode/skills/<name>` → `../../skills/...` (relative) or `/opt/code/skill/skills/...` (absolute) |
| OpenSpec commands | `.opencode/command/opsx-*.md` |
| External data (business skills) | `$LANLNK_BASE` = `/opt/code/docs/lanlnk` (not in this repo) |
| External data (user guides) | `$USERGUIDE_BASE` = `/opt/code/docs/UserGuide` (not in this repo) |
| Config | `config/lanlnk.yaml` |

**Never edit** `.opencode/skills/openspec-*/` — these are upstream artifacts.

## Environment Setup

```bash
export LANLNK_BASE=/opt/code/docs/lanlnk           # required for business/ppt/word skills
export USERGUIDE_BASE=/opt/code/docs/UserGuide     # required for doc-generator skill
```

Python skills use **uv exclusively** (never pip). Each skill has its own `.venv`:
```bash
cd skills/<category>/<skill> && uv sync && uv run <entry-point>
```

PPT skills use Node.js (`pptxgenjs`):
```bash
cd skills/ppt/ppt-master && npm install   # one-time
```

## External Data ($LANLNK_BASE)

```
/opt/code/docs/lanlnk/
├── incoming/     # raw source files dropped by user
├── raw/          # markitdown-converted .md + extracted images (_media/ dirs)
├── materials/    # structured output (01-company-overview through 07-personnel)
├── proposals/    # generated proposals + content packages
└── bidding/      # generated bid docs + content packages
```

Three-tier flow: `incoming/` → `raw/` → `materials/`. Content packages go to `proposals/<client>/content-packages/` or `bidding/<project>/content-packages/`.

## Tools & Commands

### Validators (run before rendering)

```bash
# Material files (56 files in materials/)
cd skills/business/material-importer
uv run scripts/validate_material.py $LANLNK_BASE/materials [--json]

# Word content packages (.word-content.md)
cd skills/word/word-master
uv run scripts/validate_package.py <file-or-dir> [--verbose] [--json]

# PPT YAML configs
cd skills/ppt/ppt-master/templates/proposal-pptx
uv run ../../scripts/validate_ppt_package.py <yaml-or-dir> [--verbose] [--json]
```

### Generators

```bash
# Word .docx from content package
cd skills/word/word-master
uv run python -m src.main <content.word-content.md> [--output out.docx] [-v]

# PPT .pptx from YAML config (3 modes: proposal/intro/tender)
cd skills/ppt/ppt-master/templates/proposal-pptx
uv run python compile.py <config.yaml> [--base ref.pptx] [--output out.pptx]

# Bid doc content packages from tender file
cd skills/business/bid-doc-master
uv run python -m src.main extract <tender.docx> [-o raw.json]
uv run python -m src.main generate <tender_info.json> --bidder "广州市蓝联科技有限公司" [--slide]

# Pricing spreadsheet from YAML
cd skills/business/bid-doc-master
uv run scripts/pricing_compiler.py <pricing.yaml> [--output out.xlsx]

# Operation manual from analysis + manifest (doc-generator skill)
cd skills/docs/doc-generator
uv run python scripts/render_manual.py \
  --analysis <analysis.json> \
  --manifest <manifest.json> \
  --style-fingerprint <style-fingerprint.json> \
  --output-dir <output-dir>
```

### Case Matcher

```bash
cd skills/business/material-importer
uv run scripts/case_matcher.py --industry 商业地产 --scenarios 会员营销,积分 [--limit 5] [--json]
uv run scripts/case_matcher.py --list-tags   # list all industries + scenarios
```

Scoring weights: industry ×3.0, scenario ×2.5, keyword ×1.5, scale ×1.0, completeness ×0.5.

### Cert Checker

```bash
cd skills/business/material-importer
uv run scripts/check_cert.py $LANLNK_BASE/materials [--json]
```

## Architecture Notes

### PPT: Two Compiler Paths
- **`templates/proposal-pptx/compile.py`** (python-pptx) — unified template, 3 modes (proposal/intro/tender). Modifies a 62-slide reference PPT. This is the primary path.
- **`templates/proposal-template/compile.js`** (PptxGenJS) — used only for 立项报告 (project proposals). Separate from the unified template.

PPT 3-master convention: 首尾页 → layout 0 (标题幻灯片), 目录页 → layout 1 (节标题), 内容页 → layout 2 (标题和内容).

### Word: Template-Aware Renderer
`word-master/src/renderer.py` loads a `.docx` base template, calls `_clear_template_body()` to remove placeholder content, then builds cover → TOC → chapters. Template map:
- `bidding-technical` / `bidding-commercial` → dedicated base templates
- `proposal` / `report` / `intro` / `bidding-standard` / `bidding-compilation` → all alias to `bidding-technical-base.docx`

### Bid-Doc-Master: Two-Step CLI
1. `extract` — parse tender file → structured JSON
2. `generate` — JSON → content packages (technical bid .word-content.md + optionally .slide-content.md)

### Pricing Compiler YAML Schema
Expects `categories` (list of `{name, items}`), NOT nested `items.software`. Each item needs `id`, `name`, `description`, `first_unit_price`, `first_qty`, `new_unit_price`, `new_qty`.

### Doc-Generator: Runtime-First SPA Manual Generator
`skills/docs/doc-generator/` produces图文并茂 operation manuals for any SPA (Vue3/React/Next/Nuxt) by:
1. P1 runtime probing via builtin `playwright` skill (loads mid-execution via `skill(name="playwright")`)
2. P2 plan generation using text/role/placeholder locators (NEVER CSS selectors)
3. P3 screenshot execution with per-page failure tolerance
4. P4 pure-function rendering via `scripts/render_manual.py` (no browser/network/LLM)

Outputs 3 files to `$USERGUIDE_BASE/{software_name}/`:
- `操作手册.md` — human-readable manual
- `chunks.jsonl` — LangChain `Document`-format chunks with rich metadata for RAG
- `llms.txt` — llmstxt.org-compliant summary

Input/Output separation: `$USERGUIDE_BASE/_input/{name}/` (references, config.yaml, .auth.json) ↔ `$USERGUIDE_BASE/{name}/` (outputs). First run auto-creates the input dir.

Renderer is a pure function — all "intelligence" lives in P1-P3 (agent-driven). The renderer's contract is `references/analysis-schema.md` + `references/screenshot-plan-schema.md` + `references/style-fingerprint.md`.

## LSP Warning

LSP reports many false errors in this repo:
- `docx` and `openpyxl` type stubs cause "not a known attribute" errors throughout `renderer.py` and `pricing_compiler.py` — these are **not real errors**.
- Stale diagnostics for `test_reader.py` / `test_generator.py` in bid-doc-master — these files don't exist. LSP cache artifact.

**Do not attempt to "fix" these.** Run the actual tool (`uv run ...`) to verify real behavior.

## Conventions

- **Conventional commits**: `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `refactor: ...`
- **No CI, no linting, no formatter** — repo is markdown + Python scripts
- **Generated artifacts** gitignored: `_analysis_report.json`, `test/*.docx`, `output/`
- **Domain tags** shared between `material-importer/references/domain-tags.md` and `company-intro-generator` — update both if changing tags
- **winshang-crawler** is self-contained (own `src/`, `pyproject.toml`, separate git history)

## Knowledge Persistence

AI agents don't have cross-session memory. All "memory" lives in files that are read at session start. Convention: **persist non-obvious behavior into files so future sessions don't re-derive or re-break**.

### What to record

- A behavior that reading the code alone wouldn't explain **why** (not what)
- A bug fix that was non-obvious (regex flag, path resolution, venv mismatch)
- A design decision with a rejected alternative that looks tempting

### What NOT to record

- Standard library/framework usage
- Self-explanatory code
- One-off issues unlikely to recur

### Tiered requirements by skill complexity

| Complexity | Examples | SKILL.md sections | `references/troubleshooting.md` |
|---|---|---|---|
| **Complex** (multi-module package) | product-prd-generator, bid-doc-master, doc-generator | 「已知限制」+「设计决策」+「维护规则」 | Required |
| **Medium** (single script / template engine) | material-importer, word-master, ppt-master, company-intro-generator | 「已知限制」 | Optional |
| **Simple** (thin wrapper) | winshang-crawler, crela-daily-skill | — | — |

### Layering — where knowledge goes

| Layer | Location | Read when | Examples |
|---|---|---|---|
| **Cross-cutting** (applies to all skills) | This file (`AGENTS.md`) | Every session start | uv mandatory, word-master calling pattern |
| **Skill-specific** (only relevant to one skill) | Skill's `SKILL.md` + `references/` | Skill triggered | doc_map regex choices, reconcile stale cleanup |
| **Shared files** (used by multiple skills) | Each skill keeps a copy + note here | Either skill triggered | domain-tags, term-aliases |

**Promote up, don't duplicate.** If a lesson applies to 2+ skills, move it to `AGENTS.md`. If it only matters to one skill, keep it local.

### 「复利工程」触发词

当用户在完成 skill 工作后说「复利工程」，执行以下检查清单：

1. **回顾改动**：本次改了什么（代码、bug 修复、设计决策）
2. **分流经验**：对每个非显而易见的行为/修复/决策，判断去向：
   - 跨 skill 通用 → 写入 `AGENTS.md`
   - 本 skill 特有 → 写入 `SKILL.md`（「已知限制」/「设计决策」）
   - 诊断流程 → 写入 `references/troubleshooting.md`
3. **检查分级要求是否满足**：
   - 复杂 skill → 有「已知限制」+「设计决策」+「维护规则」？有 `references/troubleshooting.md`？
   - 中等 skill → 有「已知限制」？
   - 简单 skill → 不强制
4. **共享文件检查**：改了 `domain-tags.md` / `term-aliases.yaml`？→ 同步另一边
5. **依赖图检查**：集成模式有变化？→ 更新本文件「Skill Dependencies」依赖图
6. **提交**：`docs: persist lessons via 复利工程`

## Skill Dependencies & Integration Patterns

### Dependency graph

```
material-importer ─┬─← product-prd-generator  (doc→md conversion, image extraction)
                   └─← company-intro-generator (case retrieval, cert check)

word-master ───────┬─← product-prd-generator  (.docx export)
                   ├─← company-intro-generator (.docx export)
                   └─← bid-doc-master          (technical/commercial bid .docx)

ppt-master ────────┬─← company-intro-generator (PPT generation)
/proposal-pptx     └─← bid-doc-master          (slide content .pptx)

doc-generator ─────← playwright skill          (runtime screenshots)

knowledge/cre ─────← product-prd-generator     (business-ontology.yaml: 8 modules, 482 terms)

product-prd-generator ─← word-master + material-importer + knowledge/business-ontology.yaml
```

### word-master calling pattern (3 consumers)

```python
# MUST run in word-master dir with uv — NOT python3 (venv mismatch)
subprocess.run(
    ["uv", "run", "python", "-m", "src.main", str(content_path.resolve()), "--output", str(output)],
    cwd=str(word_master_dir),  # skills/word/word-master
)
# content_path MUST be absolute — subprocess cwd changes, relative paths break
# Content package format: .word-content.md (see word-master/src/parser.py)
```

### material-importer reuse (2 consumers)

- **doc→md conversion**: markitdown + LibreOffice (.doc/.xls pre-conversion) → `raw/*.md` + `raw/*_media/` image dirs
- **Case retrieval**: `scripts/case_matcher.py` — scoring weights: industry ×3.0, scenario ×2.5, keyword ×1.5, scale ×1.0, completeness ×0.5
- **Cert check**: `scripts/check_cert.py` — expiry date extraction

### Shared files (update both sides when changing)

| File | Skills sharing it |
|---|---|
| `material-importer/references/domain-tags.md` | material-importer, company-intro-generator |
| `product-prd-generator/references/term-aliases.yaml` | product-prd-generator (currently solo, but structure ready for sharing) |
| `$LANLNK_BASE/knowledge/business-ontology.yaml` | product-prd-generator (runtime dependency; ready for company-intro-generator, bid-doc-master) |

## OpenSpec Workflow

CLI v1.1.1 on PATH. Each change = `openspec/changes/<name>/`.

| Command | Action |
|---------|--------|
| `/opsx-new` | Start new change |
| `/opsx-ff` | Generate all artifacts at once |
| `/opsx-apply` | Implement tasks from tasks.md |
| `/opsx-verify` | Validate implementation |
| `/opsx-archive` | Finalize |

Transient artifacts (`proposal.md`, `design.md`, `tasks.md`, `specs/`) are gitignored. Archives go to `openspec/changes/archive/`.

## Adding a New Custom Skill

```bash
# 1. Create skill directory
mkdir -p skills/<category>/<name>

# 2. Write SKILL.md
cat > skills/<category>/<name>/SKILL.md << 'EOF'
---
name: <name>
description: <trigger description>
compatibility: <runtime requirements>
---
<instructions>
EOF

# 3. Add pyproject.toml if Python
# 4. Create symlink
ln -s ../../skills/<category>/<name> .opencode/skills/<name>

# 5. uv sync if Python, npm install if Node
```
