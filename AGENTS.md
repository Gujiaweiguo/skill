# AGENTS.md

## Repository Purpose

OpenCode skills repository for 蓝联科技 (Lanlnk). **Skill definitions** (markdown) + **rendering engines** (Python/Node.js). No runtime web app.

Two skill types:
- **OpenSpec skills** (10) in `.opencode/skills/openspec-*/` — REAL directories (not symlinks). Bundled upstream, **read-only**.
- **Custom skills** (14) in `skills/<category>/<name>/` — symlinks from `.opencode/skills/<name>`.

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

### OCR Image Extraction (DeepSeek-OCR-2)

```bash
# Extract structured text from image-heavy PPT/Word/Excel docs
# Uses DeepSeek-OCR-2 (VLM, 3B params, ~8GB VRAM, outputs markdown + bbox)
# PEP 723 inline deps — no need to modify material-importer pyproject.toml
uv run scripts/ocr_extract.py <input_dir> [<input_dir> ...] \
  --sql-dir <sql_ddl_dir> \
  --output-dir <output_dir> \
  [--skip-existing]   # resume after interruption (reads slides.jsonl checkpoint)

# Example: extract Haiding contract table structures from PPT images
uv run scripts/ocr_extract.py \
  /opt/code/docs/lanlnk/prd/商管系统/raw/02-competitors/海鼎/业务逻辑 \
  --sql-dir /opt/code/docs/lanlnk/prd/商管系统/input/02-competitors/海鼎/数据结构 \
  --output-dir /opt/code/docs/lanlnk/prd/商管系统/raw/02-competitors/海鼎/业务逻辑/_extracted
```

Outputs: `slides.jsonl` (per-image OCR + bbox), `tables.jsonl` (table names + SQL calibration), `all-ocr.md` (human-readable), `manifest.json`.

SQL DDL files provide ground-truth table/field names for OCR calibration (corrects形近字 like `DtI`→`Dtl`).

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
- **YAML OrderedDict 陷阱**（跨 skill）：Python 代码中 **永远不要把 `OrderedDict` 直接 `yaml.dump` 到文件**。`yaml.dump(OrderedDict(...))` 会写入 `!!python/object/apply:collections.OrderedDict` tag，导致 `yaml.safe_load` 报 `ConstructorError`。Python 3.7+ 普通 `dict` 已保序，直接用 `dict`。如需恢复已被污染的文件，用 `yaml.unsafe_load` 读取→转 `dict`→重写。详见 product-prd-generator `references/troubleshooting.md`。
- **YAML 双引号嵌套陷阱**（跨 skill）：YAML 双引号字符串内含英文双引号会断解析。例如 `- "| 铺位状态 | 解约后铺位状态变为「空置」 | 悦商 |"` 如果写成 `"空置"`（英文双引号）会导致 YAML parser 在 `"空置"` 处认为字符串结束。**修复**：YAML 列表项内的 markdown 表格行如果含引号含义的中文词，用 `「」` 替代英文 `""`。
- **YAML 部分重写截断陷阱**（跨 skill，product-prd-generator）：**永远不要用 `yaml.safe_dump` 部分重写大 YAML 文件中的某个模块**。用正则 `\n[a-zA-Z]` 查找下一个模块边界时无法匹配中文字符（如 `\n合同管理:` 的 `合` 不是 ASCII 字母），导致 `end` 错误地指向文件末尾，后续所有模块被截断删除。**正确做法**：(1) 用纯文本操作 `str.index("模块名:")` 精确匹配中文字符串做边界定位；(2) 或对整个文件 `safe_load → safe_dump` 全量重写（接受格式变化）。已在事故中丢失 6 个模块约 5000 行。
- **多来源文档合并优先级**（product-prd-generator）：当多个客户/竞品描述同一套系统时，按"系统家族"而非"来源目录"分优先级。例如海鼎/华侨城/锦和同属海鼎系统家族，合并时海鼎骨架优先，其他只补证据。家族检测靠扫描路径段（不限 `/02-competitors/`），因为家族成员会出现在 `01-customer-requirements/` 里。变体标题通过 `_FAMILY_CLAUSE_ALIASES` 归一到标准条款名（如"正式合同"→"新合同申请"）。
- **xlsx/markitdown 噪音模式**（product-prd-generator）：markitdown 转换 xlsx 时会产生 `Unnamed: N` 列名和 `NaN` 空值，这些会污染 nearby_text。`_extract_nearby_text` 已内置清洗（strip NaN/Unnamed）。纯日期条目（"2026年11月"）和枚举块（"业态代码"下的 200 个行业分类码）需要显式过滤——前者加到 `_NOISE_TEXT_PATTERNS`，后者加到 `_SKIP_SCENARIOS`。
- **OCR 引擎选择**（跨 skill，图片型资料抽取）：本地 RTX 5060 Ti 是 Blackwell 架构（sm_120），**PaddleOCR 不可用**（paddlepaddle-gpu 2.6.2 只编译到 sm_90，inference 时 segfault；3.x GPU wheel 装不上）。**DeepSeek-OCR-2 是首选**（VLM，3B BF16，8GB VRAM，直接输出 markdown+bbox，中文精度业界顶级）。EasyOCR（torch+Blackwell CUDA）可用但只输出纯文本行，无法还原表格结构。Tesseract 不用（需 apt 装系统包破坏 uv 隔离，纯 CPU 慢）。脚本走 PEP 723 inline deps，不影响 material-importer 主依赖。OCR 形近字（`DtI`→`Dtl`）用 SQL DDL schema 做后校准。
- **OCR 增量 checkpoint**（material-importer）：`ocr_extract.py` 每张图 OCR 完立即 append 到 `slides.jsonl`（`flush()` 后再继续）。`--skip-existing` 从已有 `slides.jsonl` 读取已处理图片路径，跳过不重跑。聚合输出（`tables.jsonl`/`all-ocr.md`/`manifest.json`）只在最后从 `slides.jsonl` 重建。这样即使超时被 kill，已处理的结果不丢，下次 `--skip-existing` 续跑。
- **Markdown 矩阵表格列名陷阱**（跨 skill，product-prd-generator/bid-doc-master/word-master）：YAML `markdown` 字段里的 markdown 表格列名**不能含特殊字符**（`→`/`←`/`*`/`#` 等）。分隔符行 `| → |` 不是合法对齐说明符（合法的是 `---`/`:---`/`---:`/`:---:`），会导致 markdown 解析器无法识别表格结构，整张表格渲染为纯文本。**修复**：把特殊字符合并到相邻列（如 `| 源模块 | → | 目标模块 |` → `| 联动路径（源→目标） |`）。影响范围：所有用 markdown 矩阵渲染的 skill（product-prd-generator `render.py` 的 `markdown` 字段、bid-doc-master 表格、word-master 表格）。
- **ontology 与 field-specs 全局同步**（product-prd-generator）：`business-ontology.yaml` 的 `sub_functions` 如果有旧名称而 `module-field-specs.yaml` 没有对应实体，渲染器会**静默产生空 `####` 标题**（有标题无内容，不报错）。每次大改后必须做全局同步检查：`for mod in specs: assert ont_subs[mod] == set(specs[mod].keys())`。常见原因：重命名实体后只改了 field-specs 忘了改 ontology，或删除实体后只删了 field-specs 忘了删 ontology。
- **PRD→实施交接边界**（跨系统规划）：做商管/CRM/供应链等产品 PRD 后，默认只输出“目标蓝图 + PRD-vs-代码差异 + 分期 + 验收链路”交接文档，不在 PRD skill 会话里直接修改业务系统代码。业务系统（如 `/opt/code/mi`）自己基于交接文档拆 OpenSpec change、迁移、接口、前端和测试。避免 PRD 生成上下文漂移成实现上下文。
- **分期按业务闭环而非模块名**（跨系统规划）：P0 必须是可上线运营的最小端到端闭环，不是“每个核心模块做一点”。商管例：资源→招商→合同→财务→营运/物业→退出→资源释放；CRM 例：线索→客户→商机→报价/合同→回款/服务→续约。P1 放交付可用性与管控增强（移动端、报表、流程增强、关键分析/对账），P2 放数据决策/集团管控/深度集成，P3 放非主闭环拓展能力。
- **资源/对象 taxonomy 要先统一再分期**（跨系统规划）：不要用窄词误导阶段范围。商管“铺位/位置/资源”包含铺位、单元、场地、广告位、车位、多经点位；CRM“客户”可能包含线索、联系人、企业客户、门店、渠道伙伴、会员等。先定义统一对象模型和别名，再做差异与实施阶段。
- **AI 产品族术语口径**（跨 skill，product-prd-generator/strategy-brief-generator/company-intro-generator 都会碰到）：蓝联 AI 产品族有 3 个产品，代号演变历史必须记住：(1) **LnkChatBI** = CREAISkill 文档里的 `mysqlbot` = 更早的 `SQLBot`，三者同一产品（rebrand-migration spec 实证，代码 header 仍保留 `X-SQLBOT-ASK-TOKEN`）。(2) **langchat** 是第三方开源 fork（git remote: `Gujiaweiguo/langchat`），蓝联零源码改造；蓝联在它之上构建岗位 AI Skill 工作流产品。(3) **mymaxkb 产品已被 langchat 取代**——OrchestratorAgent 代码里 `system: maxkb` / `MaxKBApiExecutor` 是 legacy 标识符，产品实际为 langchat。写 PRD/方案/汇报时统一用现名（LnkChatBI / langchat），代码引用保留 legacy 名并加注。术语权威来源：`$LANLNK_BASE/prd/AI产品族架构.md` §9 术语对照表。
- **deep task 大产出拆分策略**（跨 skill，delegation 经验）：一个 deep task 一次性生成 8 个大文件（每个 200-8000 行）会卡住——实测 LnkChatBI PRD task 跑 31 分钟后 0 文件产出，被迫取消手工重写。**正确做法**：(1) 8 文件套件拆成 2-3 个 task（每个 3-4 文件）；(2) 或先 fire task 做简单文件（功能清单/需求清单/差距分析），再手工写核心文件（产品PRD）；(3) 给 task 明确的 per-file 行数上限（如"每个文件不超过 500 行"），避免模型在单文件上耗尽 token。

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

当用户在完成 OpenCode/skill/OpenSpec 工作后说「复利工程」「沉淀这次经验」「把这次 OpenCode/PRD/投标/方案经验沉淀一下」时，**优先加载 `compound-learning` skill**。

`compound-learning` 是纯提示词 meta-skill，负责开发、调试、部署、文档、方案、PRD、投标、手册、交接包工作的经验复盘与分流写入。它不生成业务文档或代码本身，而是在工作完成后判断哪些经验值得沉淀、写到哪里、哪些不应写入。

兜底分流规则：

1. 项目内复利（只影响当前项目）→ 写入目标项目 `AGENTS.md` / docs / OpenSpec。
2. 公共 OpenCode 使用复利（影响多个项目或人如何操作 OpenCode）→ 写入 `/opt/code/docs/opencode` 对应手册并更新更新日志。
3. Skill 自身复利（影响某个 skill 或跨 skill 规则）→ 写入本仓库 `AGENTS.md`、对应 `SKILL.md` 或 `references/troubleshooting.md`。
4. 项目/产品域知识 → 写入 `$LANLNK_BASE/prd/<项目>/域知识.md`。
5. 交接模式/跨系统验收 → 写入对应 `交接包/README.md` 或模板文件。
6. 改了共享文件（如 `domain-tags.md` / `term-aliases.yaml`）→ 检查同步另一边。
7. 用户要求提交时，建议 commit：`docs: persist lessons via 复利工程`。

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
| `$LANLNK_BASE/prd/商管系统/域知识.md` | product-prd-generator (商管 project only; 域知识跟着项目走，不放 skill 目录) |
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
