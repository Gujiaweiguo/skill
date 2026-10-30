---
name: material-importer
description: |-
  素材导入与结构化 Skill。将原始文档（PPT/Word/Excel/图片）批量转换为 Markdown，提取图片，
  按内容 AI 拆分到 8 大类结构化素材库（company/cases/products/qual/impl/svc/hr/bid）。
  核心能力：markitdown 文本转换链路 + convert_excel.py（PEP 723）按复杂度分流
  （简单表→Markdown table、复杂表→CSV，含合并传播、双行表头展平、Excel 序列号日期、.xls 自动转换）+
  extract_images.py 图片提取 + DeepSeek-OCR-2（VLM，BF16，3B）图片型资料 OCR + pytesseract 证照有效期检查 +
  case_matcher.py 案例匹配（行业×3/场景×2.5/关键词×1.5/规模×1/完整度×0.5 加权，供 company-intro-generator/bid-doc-master 调用）+
  validate_material.py 校验 + scan_raw_index.py 索引重建；三级目录 incoming→raw→materials，
  含 raw/_index.json 关系索引、P1.5 空章节清理、P2 多文件混合拆分、P3 质量评估、P4 交互式确认。
  触发场景："整理素材"、"导入公司资料"、"把 incoming/ 里的文件入库"、"入库新案例"、
  "检查证照有效期"、"检查素材质量"、"案例匹配"、"做方案素材够不够"。
  被 product-prd-generator / competitor-product-analyzer / strategy-brief-generator /
  project-proposal-generator / requirement-evaluator 复用作为文档转换与素材库基础设施。
  不修改业务系统代码、不生成对外方案/PRD/投标文件，只产出结构化素材供下游 skill 消费。
compatibility: >
  Requires Python 3.10+ and uv.

  Quick start:
  ```bash
  export COMPANY_BASE=/opt/code/docs/lanlnk    # 或 /opt/code/docs/lianyou 等其他公司
  # 兼容变量 LANLNK_BASE 仍有效（等价）；多公司契约见 /opt/code/docs/COMPANIES.md
  cd skills/business/material-importer
  uv sync
  ```

  Falls back from markitdown → python-pptx/python-docx/openpyxl if unavailable.
  Excel complexity routing: convert_excel.py (PEP 723, needs openpyxl + libreoffice for .xls).
  OCR (optional, heavy): DeepSeek-OCR-2 (VLM) for image-heavy docs via `scripts/ocr_extract.py`.
    GPU deps (torch, transformers, etc.) are NOT in pyproject.toml — install at user level:
    ```
    pip install --user torch transformers einops addict easydict accelerate matplotlib torchvision
    # Model auto-caches to ~/.cache/huggingface/ on first run (~8GB VRAM, ~5GB disk)
    ```
    Run with system python3 (NOT `uv run` — uv venv lacks torch by design):
    ```
    python3 scripts/ocr_extract.py <media_dir> --output <output_dir>
    ```
    PEP 723 inline deps in the script header document requirements but are not the primary run path.
  Cert expiry: pytesseract (optional, CPU-only, lightweight).
change: >
  v6 — 2026-10-30
  • convert_doc.py v2：pptx 新增页级 text-sparse 复核信号（同 slide 正文 ≤50 字且 ≥1 图，
    规则集 ppt-evidence-ruleset-v1，常量不建配置系统）
  • 检测信号三态语义：pptx_suspects / pptx_text_sparse 各支持 发现 / none /
    undetermined (detect-error)；检测失败不再渲染成 none（修复 v1 混淆），advisory 不阻断转换
  v5 — 2026-08-07
  • 新增 scripts/sanitize_markdown.py：规范化 OCR/markitdown 产出的 Markdown
  • ocr_extract.py write_markdown_summary + batch_competitor_import.py process_vendor
    在写入 .md 前自动 sanitize（HTML 表格/超长行/深嵌套引用包进 ```html fence）
  • 防止 marksman 等 Markdown LSP parser 触发 "depth limit exceeded" 栈溢出
  v4 — 2026-07-11
  • OCR 环境说明修正：明确 GPU 依赖（torch/transformers）装在 ~/.local 用户级，不在 skill venv
  • OCR 调用方式修正：用 python3 scripts/ocr_extract.py（非 uv run）
  • batch_competitor_import.py 新增 read_text_auto()：UTF-8→GB18030→UTF-16 自动编码检测
  v3 — 2026-07-11
  • P1 Excel 转换按复杂度分流：简单表→Markdown，复杂表→CSV
  • 新增 convert_excel.py：合并传播、双行表头展平、日期转换、.xls 自动转换
  • 一个源文件只产出一种格式，不混 .md 和 .csv
  v2 — 2026-06-18
  • 简化目录结构：移除 incoming/raw/，转换结果统一进 raw/
  • 新增 P1.5 空章节清理：自动移除空壳章节、占位文本、base64 噪音
  • 新增 P2 拆分触发条件：显式化 4 条必须拆分规则 + 命名规范
  • 新增 P5b 关系索引维护：raw/_index.json 追踪 raw→materials 引用
---

# Material Importer — 素材导入与结构化 Agent Pipeline

## DocSpec 质量基线

本 skill 生成的素材质量报告、缺口分析、入库建议和结构化素材说明必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `DocSpec-通用文档质量规范.md` 和 `文档验收清单.md`。素材来源、质量等级、缺失项和待人工确认项必须保留。

基于 `原始素材 → markitdown 转换 → AI 分类 → 质量评估 → 交互确认 → 标准化入库` 的方案。

## 目录结构（三级）

```
$COMPANY_BASE/                     ← 🏢 当前公司根（config/company.yaml 必须存在）
├── incoming/                      ← 🟢 原始素材入口
│                                  只放原始文件（PPTX/DOCX/XLSX/图片）
│                                  转换后由 Agent 清理，不留残余
│
├── raw/                           ← 🟡 中间产物
│   ├── 原始文件.pptx.md             markitdown 转换结果
│   ├── 原始文件_media/              提取的图片
│   └── _index.json                 自动维护的使用关系索引
│
└── materials/                     ← 🔵 最终产出
                                   结构化素材（8 大类，供查询/引用）
```

路径变量：
- `$COMPANY_BASE` = 当前公司根（变量协议：`COMPANY_BASE ∥ LANLNK_BASE`，路径下必须有 `config/company.yaml`，否则报错——无静默默认）
- `$INCOMING_DIR` = `$COMPANY_BASE/incoming/`（原始素材入口）
- `$RAW_DIR` = `$COMPANY_BASE/raw/`（Markdown + 图片 + _index.json）
- `$MATERIALS_DIR` = `$COMPANY_BASE/materials/`（结构化素材，8 大类）
- `$SCRIPTS_DIR` = `{baseDir}/scripts`

公司清单与结构由各公司 `config/company.yaml` 自描述（契约见 `/opt/code/docs/COMPANIES.md`）；公司级行业/场景标签优先读 `$COMPANY_BASE` 下 company.yaml 的 `materials.domain_tags` 所指文件，缺失时回退本 skill 的 `references/domain-tags.md`。

> ⚠️ **只有两个 raw**：转换结果统一进 `raw/`，不存在 `incoming/raw/`。  
> 之前遗留的 `incoming/raw/` 是早期 pipeline 产物，应删除。

## 核心原则

1. **不是简单转换**：是对原始内容的理解、拆分、重组
2. **质量优先**：无意义内容不收录，缺失项标记提醒
3. **交互式确认**：每批导入后输出质量报告，逐条请用户确认
4. **多文件混合拆分**：一次多份文件混入，AI 自动拆分到对应类别

## 原件为源契约（P0 政策）

- `$COMPANY_BASE/incoming/` 里的**原件是唯一权威源**；raw/materials 全部是派生投影，
  Markdown **不是**结构权威（可能丢结构，例如 pptx 合并单元格表格在 md 投影中会错位）。
- 每个派生产物必须携带 provenance（source 路径 + sha256）：
  convert_excel.py 写 `raw/<dir>/_manifest.json` 与 MD 文首 `<!-- ... -->` 头；
  markitdown 投影回填 source: 到 materials frontmatter。
- 消费方引用素材时必须带**源锚点**（sheet/幻灯片/单元格，如 `凭证式样!O2`），
  不能只给 md 行号——行号随投影重生成漂移。
- 结构可疑的投影（合并表格、跨列错位）升级为**原生/视觉重读**原件：
  `uv run scripts/pptx_table_guard.py detect <file-or-dir> [--json]`（合并格/列数>10/表头空置>30% 三规则，
  实测命中明源 21 列合并表头案例）；命中后
  `uv run scripts/pptx_table_guard.py escalate <file.pptx> --slides N[,M]` 定向渲染 PNG + provenance.json，
  再用 ocr_extract.py 做 OCR。
- 存量投影溯源回填：`uv run scripts/backfill_source.py <base> [--dry-run] [--json-report PATH]`
  （materials 补 `source:` 指向 incoming 原件；raw/*.md 文首补 source+sha256 注释块；
  仅唯一匹配才写，未匹配清单见报告 JSON。2026-10-16 已跑：materials 701→971，raw 369 个）。

## Pipeline

```
incoming/ 里的原始文件（PPTX/DOCX/XLSX/图片）
    ↓
P0: 环境检测 + 素材盘点（检查依赖 + 扫描已有素材）
    ↓
P1: 文档转换（按格式分流）
    ├── PPTX/DOCX/PDF → convert_doc.py（markitdown + 溯源头；pptx 自动跑 guard 表格检测 + 页级 text-sparse 扫描，均 advisory）→ raw/*.md
    │     └── pptx 可疑表格（合并/超宽/表头空置）→ pptx_table_guard.py escalate 定向渲染 + OCR 重读原件
    ├── XLSX/XLS  → convert_excel.py 按复杂度分流 → raw/*.md | raw/csv/*.csv
    └── 图片      → extract_images.py 提取图片 → raw/*_media/
    ↓
P1.5: 空章节清理（AI 自动移除空壳章节、占位文本、base64 噪音）
    ↓
P2: AI 内容识别与拆分（分类映射见 references/domain-tags.md）
    ↓
P3: 质量评估（评分标准见 references/quality-standards.md）
    ↓
P4: 交互确认（输出导入报告，用户确认后入库）
    ↓
P5: 标准化输出 → materials/（素材模板 + 证照OCR + validate_material.py 校验）
    ↓
P5b: 关系索引维护 → raw/_index.json（记录 raw→materials 引用关系）
```

### P0 环境检测

**P0.0 公司确定（多公司路由，必跑第一步）**

按优先级确定当前公司，绝不猜默认：

| 顺序 | 判定 | 动作 |
|---|---|---|
| ① | cwd 位于 `/opt/code/docs/<company>/` 下 | 该公司 |
| ② | 用户消息点名公司（如「入库 lianyou 的素材」） | 该公司 |
| ③ | 均无法判定 | 用 question 询问（列出已发现公司：`ls /opt/code/docs/*/config/company.yaml`） |

```bash
export COMPANY_BASE=/opt/code/docs/<company>   # 确定后导出，后续脚本全走它
```

```bash
uv sync                    # 安装依赖（含 markitdown、python-pptx、openpyxl 等）
uv run {baseDir}/scripts/validate_material.py $MATERIALS_DIR  # 校验已有素材
```

### P1 文档转换

按源文件格式分流到不同转换器。

#### PPTX / DOCX / PDF

```bash
# 文本转换（Markdown）——PDF 必须用 skill venv 内的 markitdown（见下方陷阱）
uv run {baseDir}/scripts/convert_doc.py "incoming/原始文件.pptx" "raw/原始文件.pptx.md"  # 推荐：自动带溯源头 + pptx 可疑表格检测
uv run markitdown "incoming/原始文件.pptx" > "raw/原始文件.pptx.md"  # 回退：裸转换，无溯源（违反 P0 契约，仅应急）

# 图片提取（支持 PPTX/DOCX，自动修正 Markdown 图片路径）
uv run {baseDir}/scripts/extract_images.py incoming/   # 批量处理
uv run {baseDir}/scripts/extract_images.py incoming/ --json  # Agent 程序化读取
```

> **text-sparse 页级复核信号（convert_doc.py v2 起，仅 pptx）**：
> - **语义 = 「建议回看原件该页」的人工复核提示**：不代表已识别图示/流程/箭头/业务含义，
>   不自动触发 OCR（是否 OCR 由人工决定）；素材导入层只产信号，不做竞品业务解释
> - **判定仅基于同一 slide**：正文可见字符（非空白）≤ 50 且图片形状 ≥ 1
>   （常量 `TEXT_SPARSE_MAX_VISIBLE_CHARS` / `TEXT_SPARSE_MIN_PICS`，规则集
>   `ppt-evidence-ruleset-v1`）；不计 slide number 注释、图片文件名、provenance 注释与
>   suspects 元数据，与整份 PPT 文本总量无关
> - **三态信号**（`pptx_suspects` 与 `pptx_text_sparse` 两行各自独立，互不影响）：
>   发现 → `pptx_text_sparse: slide N (text-sparse)`；
>   成功无发现 → `pptx_text_sparse: none`；
>   检测失败 → `pptx_text_sparse: undetermined (detect-error: 原因)`。
>   **失败永不渲染成 none**——下游必须区分「未判定」与「无发现」
> - **误报边界**：封面、目录、章节分隔页（少文有图）按正常稀疏页对待，被标记属预期误报；
>   信号只提示回看，不阻断任何流程；正文/边界提取失败保持 undetermined，绝不判 sparse
> - 检测是 advisory：失败时文本转换产物照常写出（source/source_sha256/extracted_by/fidelity
>   provenance 不受影响），原因进信号行 + stderr
> - **下游使用方式**：引用被标记页时锚点写 `source_sha256 + slide N`（页级锚点），
>   不能只用 md 行号（行号随重转换漂移）；OCR/图片投影是原件的派生投影，
>   **不能替代回看原始 PPT**；该页是否真有业务图示由下游人工/竞品分析回看判定

> **转换陷阱（2026-08-19 实测）**：
> 1. **PDF 转换必须用 `uv run markitdown`**（skill venv 内）。系统 PATH 上的 markitdown 通常缺 PDF 后端（pdfminer），对 PDF 返回 rc!=0 或空输出；venv 内版本正常。
> 2. **.doc（OLE2 老格式）不在直接支持列表**：需先 `soffice --headless --convert-to docx --outdir <tmp> <file>` 转 docx 再 markitdown（与 .xls 的处理同理）。
> 3. **convert_excel.py 不递归子目录**：多目录批量转换须逐目录调用（`for d in ...; do uv run scripts/convert_excel.py <in> <out>; done`）。
> 4. **文件名含 `[` 时 `find -name "stem*"` 会误判**（glob 字符类）：核对产物是否存在用 `ls` 而不是 find -name。
> 5. **extract_images.py 默认输出到 `$COMPANY_BASE/raw`**（2026-09-01 事故后收紧行为）：必须先 `export COMPANY_BASE=<绝对路径>`；`COMPANY_BASE` 为相对路径（如裸 `lanlnk`）或根下缺 `config/company.yaml` 时直接报错，无静默默认。显式 `--raw-dir` 解析结果若落在 skill 仓库内部（相对路径事故形态）会被硬拦截——转换产物永远属于 docs 仓库。

#### XLSX / XLS — 按复杂度分流

> **核心原则：一个源文件只产出一种格式，不混 .md 和 .csv。**
>
> Markdown table 不适合宽表格（42 列在渲染器里没法看），CSV 可被脚本直接 `csv.DictReader` 加载。

```bash
uv run {baseDir}/scripts/convert_excel.py <input_dir> <output_dir> \
    [--no-date-coerce] [--header-row N] [--no-header-scan]
```

路由规则（文件级判定）：

| 条件 | 输出格式 | 示例 |
|------|----------|------|
| 仅 1 个 visible sheet 且 ≤8 列 且 无合并 | Markdown table（1 个 `.md`） | 功能清单(5列)、岗位列表(4列) |
| 其余（多 sheet / >8 列 / 有合并） | CSV（每 sheet 一个 `.csv`） | ERP 权限表(42列)、合同模板(18 sheet) |

脚本内置处理：
- **合并单元格值传播**：openpyxl 只有左上角有值，传播到全部覆盖区域
- **双行表头展平**：R1 分组合并 + R2 字段名 → 单行真实字段名
- **表头错位自动扫描**（默认开）：row1 稀疏（标题行）时在前 5 行内找首个占比 >0.6 且提升 ≥0.2 的行作真实表头；之前的行进「前言区」（CSV → `.notes.md` 顶部 / MD → 引用块），永不丢弃；`--header-row N` 显式指定、`--no-header-scan` 关闭
- **Excel 序列号日期 → ISO（列级判定）**：仅当该列 ≥2 个数值且全部落在 `30000<val<100000`（约 1982–2173 年）时整列转换（`42404` → `2016-04-01`）；年份/编码等小数值不再误转，`--no-date-coerce` 可完全关闭
- **百分比显示**：number_format 含 `%` 的数值按 Excel 显示语义渲染（`0.15` → `15%`），其他格式不变
- **批注/数据验证导出**：cell 批注 + list 类数据验证；CSV 路径写同名边车 `<name>.csv.notes.md`，MD 路径追加文末
- **尾部全空列裁剪**：截断尾部无值列（前导空列保留），消除 200+ 尾部空逗号
- **MD 表格转义**：单元格内换行 → `<br>`、`|` → `\|`（CSV 路径由 csv 模块引号处理）
- **.xls / 误标 .xlsx（OLE2）自动转换**：检测魔数 `D0CF11E0`，用 libreoffice headless 转换

产物结构：

```
raw/<source_dir>/
├── 简单表.md                    # 简单表的 Markdown table
├── csv/                         # 复杂表的 CSV
│   ├── 复杂表_sheet1.csv         #   单 sheet: <stem>.csv
│   ├── 多sheet表_基本信息.csv     #   多 sheet: <stem>_<sheet>.csv
│   │   └── *.csv.notes.md         #   有批注/数据验证时的边车（可选）
│   └── 多sheet表_结算周期.csv
└── _manifest.json                #   溯源清单（source 路径/sha256/extractor 版本/产物/fidelity）
                                  #   CSV 无内联头，溯源由 manifest 覆盖；MD 另有文首 <!-- --> 注释块
                                  #   （无索引 .md，不混格式）
```

### P1.5 空章节清理（新增）

转换后的 markdown 可能包含来自原始文档的空壳章节、占位文本和内嵌图片噪音。**此步骤由 AI 自动完成**，不依赖脚本。

清理规则：

| 清理项 | 规则 | 示例 |
|--------|------|------|
| **空章节** | 标题下无实质内容（仅空白/标点/换行）→ 移除该章节 | `## XXXX集团现状`（下面空）→ 删 |
| **占位文本** | 纯占位符（`XXXX`、`…`、`……`、纯标点行）→ 移除 | `XXXX集团` → 处理为上下文推断 |
| **内嵌 base64 图片** | 超过 500 字符的 data URI → 替换为 `[图片: 第N页]` | `![](data:image/png;base64,iVBOR...)` → `[图片: 第15页]` |
| **空行坍缩** | 连续 3+ 空行 → 压缩为 1 行 | 保留基本排版结构 |
| **HTML 表格/超长行污染**（v5） | 含 `<table>/<td>/<tr>/<th>` 的行、>500 字符的 OCR 幻觉重复行、≥3 层嵌套引用 → 自动包进 ` ```html ` fence | `<table><td>...</table>` 单行 → 包 fence 避免 marksman LSP 栈溢出 |

执行方式：

```
读取 raw/*.md → AI 逐段判断内容有效性 → 清理后覆盖原文件
```

### P2 AI 内容识别与拆分

分类映射表见 `references/domain-tags.md`（可按需调整业务线标签）。

#### 拆分触发条件（必须执行）

以下情况 **必须拆分**，不得保留为单一大文件：

| 条件 | 处理方式 | 示例 |
|------|---------|------|
| 一份文件含 **2+ 个客户案例** | 按客户名称拆为独立文件 | `XX公司介绍.pptx` 含天河城/喜街/宝能 3 个案例 → `天河城案例.md`、`喜街案例.md`、`宝能案例.md` |
| 一份文件**混合产品+案例+公司简介** | 按 `03-products/`、`02-cases/`、`01-company/` 类别拆分 | `CRE系统介绍.pptx` → 产品描述归 products，案例归 cases |
| 单文件 **> 500 行**且内容不属于单一类别 | 提示用户确认是否拆分，列出各章节归类建议 | 用户确认后执行 |
| 一份文档产出**多类素材**（技术文件） | 按类型拆分：案例 + 实施 + 服务 + 人员 + 资质 | 投标方案 → 实施方法论归 impl，服务归 svc，案例归 cases |

#### 拆分后命名规则

```
raw/
├── 原始文件名_子类.md              ← 拆分后的文件
├── 原始文件名_产品A.md
└── 原始文件名_案例B.md
```

拆分后源文件保留（作为完整参考），拆分出的文件以 `原始文件名_子类.md` 命名。

### P3 质量评估

评分标准见 `references/quality-standards.md`（8 类素材逐项 checklist + 红线规则，可按需调整）。

| 评分 | 含义 | 处理 |
|------|------|------|
| ⭐⭐⭐ | 完整 | 直接入库 |
| ⭐⭐ | 部分缺失 | 入库 + 标记 ⚠️ |
| ⭐ | 严重缺失 | 拒绝，说明原因 |

### P4 交互确认

1. 输出导入报告（新增/更新/跳过/丢弃），逐条列出缺失项
2. 用户确认或补充信息
3. 最终写入素材库

### P5 标准化输出

**素材模板** — 统一 YAML frontmatter 格式：
```markdown
---
id: "case-YYYYMMDD-NNN"
type: "案例"
name: "世欧广场会员系统小程序"
domain: ["商管", "会员"]
status: "complete"
created: "YYYY-MM-DD"
source: "raw/原始文件.pptx.md"
---
```

**证照模板** — 增加 issued/expires/issuer/cert_no/images 字段。
**文件命名**：中文可读名，案例以客户+项目命名，资质以证书全称命名。
**ID 规则**：`{type}-YYYYMMDD-NNN`（case-/prod-/qual-/impl-/svc-/hr-）。

### P5b 关系索引维护（新增）

每次入库/更新素材时，自动维护 `raw/_index.json`，记录"哪个 raw 文件被哪些 material 消费了"。

```json
{
  "蓝联科技_投标解决方案.docx.md": {
    "imported_at": "2026-06-18",
    "imported_from": "incoming/蓝联科技_投标解决方案.docx",
    "source_id": "raw:蓝联科技_投标解决方案.docx.md",
    "content_sha256": "<SHA-256 of raw file bytes>",
    "consumed_by": [
      "materials/03-products/系统实施与服务体系.md",
      "materials/05-bid/投标模板.md"
    ],
    "unconsumed_sections": [
      "公司简介部分 - 未在 materials 中引用"
    ],
    "needs_review": false
  },
  ...
}
```

`source_id` 与 `content_sha256` 是可选字段。`source_id` 格式为 `raw:<COMPANY_BASE>/raw` 下的相对 POSIX 路径；它标识 raw 路径，不声称识别原始输入文件。`content_sha256` 仅在对 raw 文件实际字节计算 SHA-256 后写入。`scan_incomplete` 同为可选字段：仅当索引重建时 raw/ 或 materials/ 存在无法访问的路径（权限等）才出现且为 `true`——表示该条目的 `consumed_by`/`needs_review` 基于不完整观察，**人工清理对应 raw 文件前必须先消除访问失败并重扫**；stderr 会同步列出失败位置。旧索引缺少这些字段仍可读取；`imported_from` 是路径推断值，空值不应被解释或提升为原始文件身份。`consumed_by` 等引用继续使用公司基座下的相对路径，不复制 material 内容。

该索引只记录摄取来源路径、文件指纹及 raw/material 路径引用关系，是摄取 provenance；它不是 ontology、证据结论或决策 authority。
跨 skill 引用 raw/material 来源时，使用共享 `source-reference.schema.json` 表达路径与身份；该 schema 由 product-prd-generator 维护，material-importer 不把它当语义证据或业务决策。

**维护规则**：
- 新建 material 时 → 在 `consumed_by` 中添加引用路径
- 修改 material 时 → 检查 source 是否变动，更新 `consumed_by`
- 清理 raw 文件前 → 检查 `consumed_by` 是否为空，非空则提示用户确认
- `unconsumed_sections` 由 AI 判断（对比 raw 文件内容 vs materials 中实际使用的部分）

**索引重建**（raw/ 有大量未索引文件时批量扫描）：
```bash
uv run {baseDir}/scripts/scan_raw_index.py                 # 与现有索引合并
uv run {baseDir}/scripts/scan_raw_index.py --no-merge       # 完全覆盖
```

> **scan_raw_index.py 已知限制（2026-08-19 实测）**：
> 1. `imported_from` 为推断值，**跨主题目录结构时可能推断错**（如 raw/prd-商管系统/02-competitors/明源/ 下推断成 incoming/prd-商管系统/... 而真实入口在 incoming/商管系统竞对/...）——重建后应抽查修正。
> 2. 素材被消费后 `needs_review` **不会自动翻转**——人工蒸馏入库后需手工置 false 并清理占位性 unconsumed_sections。
扫描 raw/ 下所有 .md 文件（排除 _media/），对每个文件检测 materials/ 引用，自动推断源路径和时间戳。默认合并模式保留手动维护的字段。

**证照有效期检查**：
```bash
uv run {baseDir}/scripts/check_cert.py $COMPANY_BASE/materials
uv run {baseDir}/scripts/check_cert.py $COMPANY_BASE/materials --json  # Agent 程序化读取
```

**素材文件校验**：
```bash
uv run {baseDir}/scripts/validate_material.py $MATERIALS_DIR          # 文本报告
uv run {baseDir}/scripts/validate_material.py $MATERIALS_DIR --json   # JSON 输出
```

**案例匹配**（company-intro-generator / bid-doc-master 生成时调用）：
```bash
uv run {baseDir}/scripts/case_matcher.py --industry 商业地产 --scenarios 会员营销,积分 --limit 5
uv run {baseDir}/scripts/case_matcher.py --keywords 私域,商城 --json   # JSON 输出
uv run {baseDir}/scripts/case_matcher.py --list-tags                   # 列出所有行业和场景标签
```
匹配维度：行业（×3）、场景（×2.5）、关键词（×1.5）、规模相近度（×1）、完整度（×0.5）。

### P6 资料缺口审查

两种模式，完整框架见 `references/gap-analysis.md`：
- **方案介绍模式**（触发："检查素材够不够做XX方案"）— 5 层覆盖率评分
- **投标模式**（触发："检查XX项目投标还缺什么"）— 9 维度符合性 + 风险评分

## 使用示例

> 用户："把 incoming/ 里的文件都入库"

```
Agent:
   扫描到 2 份文件，按以下流程处理：
   ✅ 动感小西关技术文件.docx → 转换为 Markdown + 提取图片
   ✅ 动感小西关报价文件.xlsx → 转换为 Markdown
   ✅ P1.5: 空章节清理 → 移除 3 个空壳章节，压缩 2 处 base64 图片
   ✅ P2: 内容拆分 → 识别出 6 类素材（技术文件含实施+服务+案例+资质+人员）
   ✅ P5b: 更新 _index.json

   AI 识别并拆分为 6 类素材：
   ✅ [实施] 蓝联科技实施方法论 — 评分 ⭐⭐⭐ 完整
   ✅ [服务] 技术支持与服务体系 — 评分 ⭐⭐⭐ 完整
   ✅ [案例] 动感小西关会员小程序 — 评分 ⭐⭐
   ⚠️ [资质] ISO27001认证 — 评分 ⭐⭐ 缺有效期
   ⚠️ [人员] 项目团队 — 评分 ⭐ 缺具体人员姓名
   ❌ [x] 重复内容（公司简介）— 已存在，跳过

   需确认：ISO27001 有效期？项目团队具体人员信息？

   关系索引已更新：
   ✅ raw/蓝联科技_投标解决方案.docx.md
      → consumed_by: 系统实施与服务体系.md
      → unconsumed_sections: [公司简介, 客户案例] 建议进一步提取
```

## 已知限制

- Excel 列级日期投票对整体落在 30000~100000 的非日期数字列（如月租金 45000）仍会误转 → `--no-date-coerce` 兜底
- `scan_raw_index.py` 的 `imported_from` 是推断值，跨主题目录结构时可能推错；`needs_review` 不会自动翻转（详见上文 2026-08-19 实测注记）
- `.ppt`（旧二进制）python-pptx 不支持 → pptx_table_guard 报 skipped；`.doc/.xls` 需 libreoffice 预转换
- markitdown 对损坏 OOXML 会静默当纯文本转换 → convert_doc 有魔数守卫（PK / %PDF-），但裸 `uv run markitdown` 回退路径无守卫
- OCR（DeepSeek-OCR-2）依赖用户级 GPU 环境，不在 skill venv 内；缺 GPU 时 ocr_extract.py 不可用
- `text-sparse` 阈值常量（≤50 字 + ≥1 图）对封面/目录/章节分隔页有**预期误报**；v1 不做页型豁免，信号仅为回看提示、不阻断流程
- 检测失败语义 = `undetermined (detect-error: 原因)`，与 `none`（成功无发现）严格区分；v1 及更早转换的旧 raw 产物没有 `pptx_text_sparse` 行仍是合法产物（不回填、不重转），该行只出现在 v2 起重新转换的文件
- 更多坑位与修复规则见 `references/troubleshooting.md`

## 设计决策

- **原件为源契约（P0）**：见上文「原件为源契约」专节——source 永指 incoming 原件，raw/materials 只是投影
- **列级日期投票 vs 逐格**：列内 ≥2 数值且全部 30000<val<100000 才整列转，一票反例否决；数字分支历史上只有误报没有漏报（真日期走 datetime 分支），故宁可漏转不可误转
- **CSV vs MD 路由**：文件级判定（单 visible sheet + ≤8 列 + 无合并 → MD，否则 CSV）；MD 宽表在渲染器里不可读，CSV 可被 DictReader 直接消费；一个源文件只产出一种格式
- **表头扫描默认开启**：真实凭证表普遍带标题前言区，默认开避免人工指定 `--header-row`；前言进 `.notes.md` 顶部，永不丢弃
- **pptx guard 只升级不预跑 OCR**：convert_doc 对 pptx 自动跑 detect（轻量、纯 python-pptx），命中才 escalate 渲染 PNG + OCR（重、需 GPU）——按需付费
- **text-sparse 在 convert_doc.py 内直接用 python-pptx 逐 slide 计算**：不扩展 pptx_table_guard.py（guard「报告工具恒 exit 0」哲学与三态语义改造正交）；也不解析转换后 md 推断稀疏页（markitdown 的 slide 分界不可靠，且拿不到「同一 slide 的图片存在情况」）
- **检测三态语义（v2）**：`none` 仅表示「检测成功且无发现」；检测失败渲染 `undetermined (detect-error: 原因)`——修复 v1 把 guard 失败渲染成 `pptx_suspects: none` 的语义混淆；检测是 advisory，失败不阻断转换产物
- **EXTRACTOR_VERSION 1→2**：输出新增 text-sparse/ruleset 注释行，按维护规则 bump 代际（manifest 溯源依赖它区分产物代际）；旧 raw 产物不回填不重转
- **扫描行宽基准**：表头占比用尾部裁剪后的行宽计算（香格里拉 257 列事故），`_trim_trailing` 必须先于 `_detect_preface`

## 维护规则

- 任何写 `$COMPANY_BASE` 的脚本必须过五道闸门：dry-run 先行 / 唯一匹配才写 / 分桶上限 / validator 前后基线 diff 零新增错误 / has-source 绝不重写
- 改 SKILL.md / AGENTS.md 触发 pre-commit 的 `check_skill_ecosystem.sh --ci`——提交前本地先跑
- 共享文件 `references/domain-tags.md` 被 product-prd-generator / compound-learning 读取，改动需同步 AGENTS.md「Shared files」表和 `check_docs_consistency.sh` 的 `SHARED_FILES` 数组
- 修复新坑 → 先加回归测试再修代码；驱动修复的金样例登记在 `tests/fixtures_registry.json`（引用外部仓路径+sha，不复制二进制）
- convert_excel 逻辑变更须 bump `EXTRACTOR_VERSION`（manifest 溯源依赖它区分产物代际）
- 批量导入 ≥50 件必须分层抽样质检：抽 20 份分层样本（厂商×来源型×子目录），按 5 维准则评分——内容健全性 / frontmatter 准确性（含 id 唯一性）/ 溯源链可解析 / 表格完整性 / OCR 可信度；批级通过率 <90% 的维度视为批缺陷。依据 2026-10-17 质检实证：4 个缺陷中 3 个纯机械流程不可见。
