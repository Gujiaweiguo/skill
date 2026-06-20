# AGENTS.md

## Repository Purpose

OpenCode skills repository for 蓝联科技 (Lanlnk). **Skill definitions** (markdown) + **rendering engines** (Python/Node.js). No runtime web app.

Two skill types:
- **OpenSpec skills** (10) in `.opencode/skills/openspec-*/` — REAL directories (not symlinks). Bundled upstream, **read-only**.
- **Custom skills** (11) in `skills/<category>/<name>/` — symlinks from `.opencode/skills/<name>`.

## Critical Paths

| What | Where |
|------|-------|
| Edit skills here | `skills/<category>/<name>/` |
| OpenCode symlinks | `.opencode/skills/<name>` → `../../skills/...` (relative) or `/opt/code/skill/skills/...` (absolute) |
| OpenSpec commands | `.opencode/command/opsx-*.md` |
| External data | `$LANLNK_BASE` = `/opt/code/docs/lanlnk` (not in this repo) |
| Config | `config/lanlnk.yaml` |

**Never edit** `.opencode/skills/openspec-*/` — these are upstream artifacts.

## Environment Setup

```bash
export LANLNK_BASE=/opt/code/docs/lanlnk   # required for all business skills
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
