### Requirement: Pure Function Operation

`render_manual.py` SHALL be a pure function of its inputs: `analysis.json`, `manifest.json`, and `style-fingerprint.json`. The script SHALL NOT make network calls, launch browsers, invoke LLMs, read source code, or perform any I/O outside reading the three input files and writing the three output files.

#### Scenario: No hidden dependencies

- **WHEN** `render_manual.py` is run with valid input files in a sandbox without network access
- **THEN** it completes successfully and produces all three output files

#### Scenario: Deterministic output

- **WHEN** `render_manual.py` is run twice with identical inputs
- **THEN** the two output sets are byte-identical (modulo the `generated_at` timestamp field, which is sourced from `analysis.json.generated_at`)

### Requirement: Triple Output Generation

A single invocation of `render_manual.py` SHALL produce three files in `$USERGUIDE_BASE/{name}/`: `操作手册.md`, `chunks.jsonl`, and `llms.txt`. The script SHALL NOT support generating a subset of outputs; if any output fails, the whole rendering is considered failed and partial outputs are deleted.

#### Scenario: All three outputs produced

- **WHEN** `render_manual.py` runs successfully
- **THEN** all of `操作手册.md`, `chunks.jsonl`, `llms.txt` exist in the output directory

#### Scenario: Partial failure rolls back

- **WHEN** rendering fails midway (e.g., `chunks.jsonl` write fails due to disk full)
- **THEN** any partial outputs already written are deleted, and the script exits with non-zero status

### Requirement: Markdown Manual Template

`操作手册.md` SHALL follow the template defined in `references/manual-template.md`. The manual SHALL include: a header with app name/version/generated date, a "快速开始" section, one "功能模块详解" section per route (with 操作步骤 and 界面元素说明 subsections), a "常见问题" section, and an appendix.

#### Scenario: Manual structure follows template

- **WHEN** `analysis.json` has 5 routes
- **THEN** `操作手册.md` has exactly 5 module subsections under "## 二、功能模块详解", each with "操作步骤" and "界面元素说明" subsections

#### Scenario: Failed screenshots render placeholders

- **WHEN** `manifest.json` marks a screenshot action as failed
- **THEN** the corresponding image position in `操作手册.md` is rendered as `> ⚠️ 截图失败：{reason}` instead of a broken `![](...)` link

### Requirement: Chunks JSONL Schema (LangChain Document)

`chunks.jsonl` SHALL contain one JSON object per line, each compliant with the LangChain `Document` shape: `{page_content: string, metadata: object}`. The `metadata` object SHALL include `app_name`, `version`, `module`, `subsection`, `step` (nullable), `page_url`, `screenshots[]`, `element_texts[]`, and `chunk_id`.

#### Scenario: One chunk per step

- **WHEN** a route's flow has 3 steps plus a page-load entry
- **THEN** `chunks.jsonl` contains 4 chunk lines for that route (1 page-load chunk + 3 step chunks)

#### Scenario: Chunk preserves screenshot association

- **WHEN** a step chunk's source step has a successful screenshot at `imgs/users_2_create_modal.png`
- **THEN** the chunk's `metadata.screenshots === ["imgs/users_2_create_modal.png"]`, allowing downstream RAG to render the image alongside retrieved text

#### Scenario: Element texts captured for retrieval

- **WHEN** a chunk describes a step involving buttons "新建" and "保存"
- **THEN** `metadata.element_texts` includes both "新建" and "保存", so text retrieval hits when users query those terms

#### Scenario: Chunk IDs globally unique

- **WHEN** `chunks.jsonl` is generated for an app with 10 modules averaging 3 chunks each
- **THEN** every `metadata.chunk_id` is unique (format: `{app_name}_{module_slug}_{subsection_slug}_{step_or_zero}`)

### Requirement: LLMS-Text Format Compliance

`llms.txt` SHALL follow the llmstxt.org specification: H1 = `{app_name} 操作手册`, optional blockquote summary, H2 sections per major chapter, each followed by a markdown link to the corresponding `操作手册.md` anchor.

#### Scenario: llms.txt has H1 and summary

- **WHEN** `llms.txt` is generated
- **THEN** the first line is `# {app_name} 操作手册` and the next non-empty line is a `> ` blockquote with a one-sentence summary

#### Scenario: Each chapter has anchor link

- **WHEN** `操作手册.md` has a chapter "## 二、功能模块详解 > 模块三：用户管理"
- **THEN** `llms.txt` contains a corresponding H2 (e.g., `## 用户管理`) followed by a link `[查看详情](操作手册.md#模块三用户管理)`

### Requirement: Reference Material Ingestion

Before P4, the skill SHALL ingest reference materials from `$USERGUIDE_BASE/_input/{name}/references/`. Supported formats: `.md`, `.txt`, `.html` (direct read); `.docx`, `.pptx` (via `markitdown`); `.pdf` (via `pypdf`); `urls.txt` (one URL per line, fetched via `webfetch`). Unsupported formats SHALL be skipped with a warning.

#### Scenario: Markdown reference read directly

- **WHEN** `_input/mysqlbot/references/阿里云RDS操作手册.md` exists
- **THEN** the agent reads the file content and uses it as input to style fingerprint extraction

#### Scenario: DOCX reference via markitdown

- **WHEN** `_input/mysqlbot/references/友商手册.docx` exists
- **THEN** the agent invokes `markitdown 友商手册.docx` (reusing material-importer's installation) to extract text before fingerprint extraction

#### Scenario: URL reference fetched

- **WHEN** `_input/mysqlbot/references/urls.txt` contains `https://help.aliyun.com/rds/quick-start`
- **THEN** the agent invokes `webfetch` on each URL and merges the retrieved content into the reference pool

#### Scenario: Unsupported format skipped with warning

- **WHEN** `_input/mysqlbot/references/scan.jpg` exists but `.jpg` is not a supported reference format
- **THEN** the agent emits a warning "Unsupported reference format: .jpg, skipped" and continues with other references

### Requirement: Style Fingerprint Extraction

Reference materials SHALL be reduced to a `style-fingerprint.json` with five dimensions: `chapter_depth` (1-3), `step_density` (`low`/`medium`/`high`), `screenshot_frequency` (`low`/`medium`/`high`), `table_preference` (`none`/`minimal`/`heavy`), `faq_style` (`none`/`short`/`detailed`). The fingerprint SHALL be merged from all references, with explicit `_input/{name}/config.yaml` overrides taking precedence.

#### Scenario: Fingerprint extracted from reference

- **WHEN** the reference manual has 3-level chapter nesting, ~1 screenshot per 2 steps, and detailed FAQ
- **THEN** `style-fingerprint.json` is `{chapter_depth: 3, step_density: "medium", screenshot_frequency: "medium", table_preference: "minimal", faq_style: "detailed"}`

#### Scenario: Config override takes precedence

- **WHEN** reference-derived fingerprint has `screenshot_frequency: "low"` but `config.yaml` has `screenshot_density: "high"`
- **THEN** the final `style-fingerprint.json` has `screenshot_frequency: "high"`, and a `sources` field records which dimensions came from config override

#### Scenario: No references produces default fingerprint

- **WHEN** `_input/{name}/references/` is empty or missing
- **THEN** `style-fingerprint.json` defaults to `{chapter_depth: 2, step_density: "medium", screenshot_frequency: "medium", table_preference: "minimal", faq_style: "short"}`

### Requirement: Failed-Screenshot Placeholder Rendering

When `manifest.json` indicates a screenshot failed, the renderer SHALL emit a clearly visible placeholder in `操作手册.md` and SHALL omit the screenshot path from the corresponding chunk's `metadata.screenshots` (so RAG does not reference non-existent files).

#### Scenario: Placeholder markdown syntax

- **WHEN** a screenshot at step 2 of "用户管理" failed with reason "selector timeout"
- **THEN** `操作手册.md` shows `> ⚠️ 截图失败：selector timeout（步骤 2）` instead of an image link

#### Scenario: Failed screenshot excluded from chunk metadata

- **WHEN** the same failed screenshot exists
- **THEN** the step-2 chunk in `chunks.jsonl` has `metadata.screenshots: []` (empty array), not the missing path

### Requirement: Single-Source Multi-Output Consistency

The three outputs (`操作手册.md`, `chunks.jsonl`, `llms.txt`) SHALL be derived from the same in-memory representation built from `analysis.json` + `manifest.json`. The renderer SHALL NOT re-read or re-parse the application. Module titles, element lists, and step counts SHALL match exactly across all three outputs.

#### Scenario: Module count matches across outputs

- **WHEN** `analysis.json` has 5 routes
- **THEN** `操作手册.md` has 5 module sections, `chunks.jsonl` references 5 distinct `module` values in metadata, and `llms.txt` has 5 H2 section entries

#### Scenario: Element texts consistent across outputs

- **WHEN** a route has 4 elements extracted
- **THEN** the same 4 element texts appear in `操作手册.md`'s "界面元素说明" table and in the corresponding `chunks.jsonl` chunks' `metadata.element_texts`
