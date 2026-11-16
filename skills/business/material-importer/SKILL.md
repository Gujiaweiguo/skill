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
  v8.3 — 2026-11-14（inspect-material-source-fragments）
  • provenance_inventory materials 片段来源观察：frontmatter source 完整字面路径
  优先（含 #/括号/空格/分号），仅明确不存在（ENOENT）且符合受限 .jsonl 片段
  语法时按首个 # 拆分容器与 fragment；ENOTDIR/EACCES/ELOOP 等观察失败不冒充
  不存在、不触发截断回退（完整字面路径 resolve 遇 ELOOP 自环——pathlib 包成
  RuntimeError 非 OSError——同样承接为观察失败，附 errno 证据，不崩溃不回退）；
  容器检查沿用同公司边界与观察失败语义
  • 新增 item 字段 source_expression_kind=local-file-fragment /
  source_container / source_fragment / anchor_verification=not-performed /
  container_accessibility / projection_accessibility 与顶层
  material_source_fragment_findings（kind=anchor-not-verified|
  container-missing|container-check-failed|container-boundary-violation，
  纳入 rc=3）；--full-hash 容器观察字段 container_sha256_observed/
  container_observed_at（当前观察，不冒充转换时哈希），默认不读容器正文、
  不核验锚点；missing_original 在容器缺失时记容器并保留原声明与 fragment
  • wrong_source_suspects 片段分支：fragment-not-verified / container-missing /
  container-check-failed / boundary-violation（--full-hash 容器字节读取失败
  同落 container-check-failed），不落 resolvable-in-base/
  无需修复，不进回填候选，不建议自动重转；非片段/none/缺来源/描述性
  source/raw 网页行为保持不变
  v8.2 — 2026-11-14（recognize-web-capture-provenance 复核遗漏补充，第三批）
  • 文首旧 source/source_path 一条 URL 一条本地路径（两种顺序）不再只取首条：
  双方都保留（URL 进声明表与 external_sources_unverified；本地取先出现的
  非URL 命中照常解析，source_kind=mixed），本地缺失/越界照常报告，
  不以有效 URL 掩盖本地来源问题
  • 旧 source/source_path 的 URL 形态命中只认文首连续注释区（head_comment_region_end
  同口径）；正文、围栏代码块、后置注释中的 URL 命中不是有效网页来源（不进外部
  清单、不进本地解析、也不当缺失文件）。本地路径命中的既有全头检索兼容行为
  不变（不收紧）
  v8.1 — 2026-11-14（recognize-web-capture-provenance 独立复核修复，第二批）
  • 游离存档哈希零路径：unresolved-hash-binding（零/多路径统一）与
    invalid-hash（零路径也报）不再静默；local_archive_observations 键一致存在
  • 同头部多值声明不选首条：多条不同 sha256_observed → declared-hash-conflict
    （hash_check=unresolved-declared-hash，不按首条判 match/mismatch）；
    多条不同 observed_at → observed-at-conflict；多条不同抓取时间 →
    source_declaration_conflicts（kind=captured-at，外部条目不带单一权威时间）
  • local_archive 值形态非法（空值/URL 形态）不做文件系统解析：
    invalid-archive-declaration（issue=empty-value|url-shaped），
    不再产生 EISDIR/假 missing；只做加法发现，未放宽任何既有规则
  v8 — 2026-11-14（recognize-web-capture-provenance）
  • provenance_inventory 识别 raw MD 文首中文抓取头（来源 URL/抓取时间/source_url）：
    HTTP(S) 按外部来源分维表达（external-url/not-scanned/unknown-scope），绝不联网、
    绝不走文件路径解析；未核验外部声明单列 external_sources_unverified（rc=3），
    URL-only 不再误报 missing_source/missing_original
  • 新增报告节 source_declaration_conflicts / source_declaration_errors /
    local_archive_findings 与 item.source_declarations（含行位置）；
    wrong_source_suspects 按 source_kind 分支（external-not-verified），
    外部声明不进本地回填候选
  • local_archive 独立存档观察：仅明确声明、当前哈希实际计算、两时点分列
    （declared_observed_at vs observed_at）、越界不读取、不按同名 HTML 推断、
    不升级 recorded-at-conversion
  v7 — 2026-11-14（harden-material-import-provenance）
  • 新增 scripts/provenance_inventory.py：只读溯源体检（四类链接状态 + source_nature/
    accessibility/hash_check 三维分维、boundary-violation 单列、抽样口径显式、退出码
    0/1/2/3、--repair-candidates 候选分级、多公司基座隔离）
  • 转换指纹与增量重跑：convert_excel manifest 新增 options/outputs/backend/
    fingerprint_format；convert_doc MD 内联 output_body_sha256（正文范围哈希）；
    两入口新增 --check（零写入）/ --skip-up-to-date / --force-overwrite-modified，
    模式×状态矩阵逐格实现（见「溯源生命周期」专节）
  • manifest 预写检查：任何输出写入前校验目标 _manifest.json，损坏/结构非法/记录冲突
    → 该项失败且已有字节保留，不再静默清空历史
  • Office ~$ 锁文件输入侧守卫（convert_doc/extract_images 单文件 exit 3，convert_excel
    批量 skip）；文件名中部 ~$ 投影只进体检 garbage-candidate 候选清单
  • backfill_source.py：回填分级持久化（provenance_class + source_sha256_at_backfill
    + backfilled_at），兼容读取旧 backfilled 记录，新增 wrong_source_suspects
  • 新增唯一共享证据边界 references/provenance-evidence-boundary.md（消费方引用不复制）
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
  v7 起：回填写入随产物持久化分级（`provenance_class: candidate-association` +
  `source_sha256_at_backfill` + `backfilled_at`，不再用裸 `source_sha256` 字段名）；
  已有 source 的文件不改写，但声明来源不可解析时会进报告 `wrong_source_suspects`（仅建议）。

## 溯源生命周期（只读体检 / 转换指纹 / 增量重跑，v7）

图片 / text-sparse / OCR 的**证据边界规则**唯一权威源：
`references/provenance-evidence-boundary.md`（检测三态、页级锚点、OCR=检索线索、
fresh-clone 三项要求、evidence_state 逐项映射表）。本 skill 与消费方（competitor-product-analyzer）
引用该文件，不复制规则文本。

### 只读溯源体检（provenance_inventory.py）

```bash
uv run {baseDir}/scripts/provenance_inventory.py [--base $COMPANY_BASE] [--report PATH] \
    [--full-hash] [--repair-candidates] [--sample-bytes N]
```

- **零业务写入**：纯读盘点 incoming/raw(.md/.csv/.notes.md)/_manifest.json/materials，
  报告写 stdout 或显式 `--report` 路径（绝不默认写 docs 基座）；运行前后基座字节不变（测试钉死）。
- **分维表达**（不压缩合并）：每条目 `source_nature`（declared/inferred/none）×
  `accessibility`（accessible/missing/permission-denied/not-scanned/backend-unavailable）×
  `hash_check`（match/mismatch/not-applicable/no-declared-hash/unknown-scope），
  另有 `link_state`（observed/declared/inferred/unknown-unavailable）描述来源链接定性。
- **推断永不升级**：路径结构/文件名/`_index.json` 的 imported_from 推断一律 `inferred`
  （附候选与依据），唯一候选也不等于已验证原件身份。
- **默认哈希策略**：只哈希有声明哈希需比对的对象；`--full-hash` opt-in 全量。
- **抽样口径显式**：无效投影诊断默认读前 64 KiB，报 `sampled_bytes`/`sample_nul_count`
  /`nul_scope`（sample|full，全文件计数仅在完整读取时报）；UTF-8 严格解码失败报
  `encoding-invalid`；短文档/空白文档不判垃圾；文件名中部含 `~$` 的投影只进
  `garbage-candidate` 候选清单（不拦截、不删除、不单独定罪）。
- **authored 前缀声明**：materials frontmatter `source` 值以半角 `authored:` 前缀
  开头（strip 后整串前缀、大小写敏感小写；仅认 frontmatter source 字段，raw 注释区/
  正文不认）→ authored 声明：`source_nature=declared`、`link_state=not-applicable`、
  `accessibility=not-applicable`（与 not-scanned 区分）、`hash_check=not-applicable`；
  不计入 missing_original/missing_source 及任何 gaps、不产生 repair_candidates。
  顶层清单 `authored_declarations[]`（path/source_verbatim/line）纳入 rc=3 发现
  （存在 authored 声明即「有发现」，同 external 先例）；authored 不参与本地扫描
  范围。`source: none` 行为不变。
- **多公司隔离**：复用 `_company_base.resolve_company_base()`（无静默默认公司）；
  匹配索引/指纹/manifest 只在当前基座内构建，同名原件/相同相对路径不跨公司匹配复用；
  声明来源解析（含 symlink）越出基座 → `boundary-violation` 单列且不读取目标内容。
- **退出码**：0=完成无缺口 / 1=工具失败 / 2=用法错误 / 3=完成且有发现（缺口清单含缺来源、
  缺哈希、缺原件、歧义匹配、manifest 损坏/记录冲突/产物缺失、边界问题、**未核验外部
  网页声明、声明冲突/错误、存档发现、materials 片段锚点未核验**）。
- **declared `source: none` 非缺口**：raw 投影声明 `none` 与 materials 同语义——
  `source_nature=none`、authored 标记非缺口，退出 missing_original/missing_source 与
  repair 候选（raw 分支 accessibility/hash_check 维持本分支既有映射）。
- **raw 声明解析 frontmatter 回退**：注释载体（行内/块 `source:`/`source_path:`）命中
  优先、零变化；仅当注释载体无任何 source 命中时，回退读 frontmatter `source` 字段
  （`declared_via=frontmatter`），值进入与注释值相同的处理链（URL/none/本地解析全语义）。
- **raw 声明哈希 frontmatter 回退**：注释载体（行内/块 `source_sha256`/
  `source_sha256_at_backfill`）命中优先、零变化；仅当注释载体无任何哈希命中时，
  回退读 frontmatter `source_sha256_at_backfill`（`hash_via=frontmatter`，
  引号剥离同 source 回退），作为 declared hash 进入既有哈希比对链。
  **「有发现」不是工具故障**——rc=3 时报告仍是完整可用的证据；URL-only 文章"未核验"
  即 rc=3，**不承诺体检归零**。
- `--repair-candidates`：对缺溯源产物产候选（唯一 basename 匹配 → candidate-association
  级，附候选原件当前哈希；多候选/无依据 CSV↔sheet 映射 → unresolved；已有 source →
  wrong_source_suspects 仅评估建议）。recorded-at-conversion 只按 D7 三要件对既有记录判定
  （转换器签名 + 同基座来源 + 合法转换时哈希），仅证明存在转换时点的来源声明；
  verified-historical 为更高独立核验概念，本工具永不自动授予。历史回填/重转/清理
  **必须**由 Owner 基于本工具 dry-run 报告另行授权后才执行。

#### 网页抓取声明识别（v8，recognize-web-capture-provenance）

针对「公众号文章等网页抓取后存的 raw MD」：中文抓取头是与本地文件来源**并列的独立
声明形态，不改写成 source 路径去迎合本地检查。

- **支持字段**（只在文首有界注释区识别，半角/全角冒号均可）：
  `来源 URL`（含紧凑写法 `来源URL`）、`source_url` → 网页来源；`抓取时间` → 声明日期；
  `local_archive` / `local_archive_sha256_observed` / `local_archive_observed_at` →
  显式本地存档声明（见下节）。示例（与测试同构、真实锚点格式）：

  ```markdown
  <!--
  来源 URL: https://mp.weixin.qq.com/s/xxxx
  抓取时间: 2026-11-07
  账号名: 某公众号
  -->
  ```

- **头部边界**：只采集文首空白后**连续 HTML 注释区**（受 4000 字符头上限约束）；
  正文、代码块、正文后置注释里的 URL 一律不认；未闭合或被截断的注释不给有效来源。
  支持字段保留原值与 1-based 行位置（`item.source_declarations[]`，每条含
  field/kind/value/value_normalized/line）。
- **URL 规则**：HTTP(S) 单个完整 URL（有 hostname、无用户凭据/控制符/空白附注）→
  外部来源（`source_kind: external-url`，`accessibility: not-scanned`，
  `hash_check: unknown-scope`，MD 自身读取状态单列 `projection_accessibility`）；
  绝不联网、绝不走文件路径解析/哈希。`file://`/`ftp://` 等报告 unsupported-scheme
  （不当相对路径）；畸形值进 `source_declaration_errors` 并保留原值，不做 basename
  推断回填。旧 `source:`/`source_path:` 字段完整值为 scheme 形态时同样走外部分支，
  但**只认文首连续注释区内的命中**（v8.2）——正文、围栏代码块、后置注释里的旧
  source/source_path URL 不是有效网页来源（不进外部清单、不进本地解析、也不当
  缺失文件）；本地路径命中的既有全头检索兼容行为不变（不收紧）。
- **日期只是声明**：`抓取时间` 保留原文、语义标记 `declared`；不推断时区、不校验
  抓取真实发生，不得当作已核验历史事实。**不要求历史 MD 增补字段、不伪造 extractor
  签名**——工具识别既有声明，不回写任何 MD。
- **多声明**：相同 URL 按去首尾空白后的精确值归组（保留全部位置）；不同 URL 记
  `source_declaration_conflicts`（`kind` 缺省为 URL 冲突，`urls` 列全部值），不选权威。
  多条不同 `抓取时间` 同样记 `source_declaration_conflicts`（`kind: captured-at`，
  `values`/`lines` 逐条保留）——外部条目此时**不带单一权威时间**（不选首条）。
  本地 source 与网页 URL 并存时
  （`source_kind: mixed`）顶层保留本地结果，URL 进独立清单，互不掩盖。
  **旧 source/source_path 多条命中同理不隐藏（v8.2）**：一条 URL 一条本地路径
  （无论顺序）时双方都保留——URL 命中（限文首区）全部进声明表与外部未核验清单，
  本地取先出现的非 URL 命中照常解析校验（`declared_source`/`declared_via` 指向
  本地声明），本地缺失/越界/哈希诊断照常输出，不以有效 URL 掩盖。
- **报告新增字段/节**（始终存在、稳定排序、纳入 rc=3 判定）：
  `items[].source_declarations[]`（field/kind/value/value_normalized/line，URL 类附
  status）；`items[].external_urls`；顶层 `external_sources_unverified[]`（path/url/
  declarations[]/captured_at/captured_at_semantics=declared/verification=not-performed）、
  `source_declaration_conflicts[]`、`source_declaration_errors[]`（issue=
  malformed/not-url/unsupported-scheme，原值保留）、`local_archive_findings[]`、
  `external_verification`（status=not-performed 或 no-external-declarations）。
  **`scan.complete` 只覆盖声明的本地扫描范围**——未联网不影响本地枚举完整性判定，
  外部 URL 可达性一律 not-performed，报告不得解读为"全来源已核验"。
- **修复候选隔离**：有效/冲突/畸形外部声明都不进 `repair_candidates`（不当"无来源可
  自动补本地source"）；`wrong_source_suspects` 对 external-url 条目记
  `external-not-verified`（绝不落 resolvable-in-base），mixed 条目沿用本地判断。

#### 本地网页存档观察（local_archive，可选显式声明）

- **只认显式声明**：`local_archive: <基座内路径>`；附近存在同名 HTML **不构成**存档
  关系，工具绝不按文件名推断或写入元数据。仅有存档声明不消除真正 missing_source。
- **观察字段**（`items[].local_archive_observations[]`，每条明确路径独立一项）：
  `declared_path`/`declared_line`/`accessibility`（accessible|missing|
  permission-denied|inaccessible|boundary-violation）/`sha256_observed`（当前字节
  实际计算，即使无 --full-hash——仅明确关联对象，开销有界）/`observed_at`（本次
  观察时点）/`declared_sha256_observed`/`declared_observed_at`/`hash_check`
  （match-observed|mismatch-observed|unresolved-declared-hash|no-declared-hash|
  not-applicable；`unresolved-declared-hash` = 有哈希声明但未绑定——多值冲突或
  路径数 ≠ 1，不冒充无声明也不按首条判定）。
- **声明值形态**（独立复核第二批）：`local_archive` 值为空或 URL 形态（scheme://）
  时**不做文件系统解析**（空值不得解析为基座目录、URL 不得当相对路径猜路径），
  记 `invalid-archive-declaration` 发现（issue=empty-value|url-shaped，原值保留），
  不产生 accessible/missing/read-error 假观察。
- **两时点哈希分列**：`local_archive_sha256_observed` + `local_archive_observed_at`
  是历史声明观察，本次 `sha256_observed` + `observed_at` 是当前观察；一致也只证明
  当前字节一致，**不提升网页来源真实性、不触发 recorded-at-conversion**。
- **发现清单**（`local_archive_findings[]`）：missing（≠网页原件不存在，两者分列）/
  read-error（带 errno 依据）/boundary（跨公司、基座外绝对路径、越界符号链接——
  不读取目标内容、不复用其他公司同名存档）/invalid-hash（含零路径的非法格式哈希）/
  hash-mismatch-observed/archive-conflict（多条不同路径：逐项保留，不选首条权威）/
  declared-hash-conflict（多条不同 sha256_observed：逐值分列，不选首条为比对基准）/
  observed-at-conflict（多条不同观察时间：不选首条为权威时点）/
  invalid-archive-declaration（local_archive 值为空/URL 形态：不解析不猜路径）/
  unresolved-hash-binding（游离哈希**零路径或多路径**均无法唯一绑定：不静默
  套用到任何一条）。
- **本 capability 不改**：source 回填写入（backfill_source.py）、转换器签名/代际、
  fragment 或描述性复合来源的自然语言拆分——均留独立范围。

#### materials 片段来源观察（.jsonl#锚点，受限回退，v8.3）

只针对 **materials frontmatter `source`** 的受限片段形态（真实锚点：
`raw/_extracted/slides.jsonl#溯源系统证书-1.png`——OCR 抽取登记的"容器#图片名"）：

- **字面路径优先**：完整 source 先按原流程解析；同公司内**现存普通文件**（文件名
  含 `#`、括号、空格、分号也算）直接沿用完整字面来源，不拆、不检查另一条截断
  路径。越界/resolve 错误/stat 错误直接终止（保留该诊断），**不借截断回退掩盖**；
  现存目录/非普通文件按观察失败报告（不当作有效文件或缺失）。
- **受限语法**（唯一回退条件 = 完整路径明确 ENOENT）：首个 `#` 两侧非空，左侧以
  `.jsonl` 结尾且非 `scheme://`、无控制字符/中文分号；右侧无空白、控制字符、
  中文分号、ASCII/全角括号。额外 `#` 与 `%xx` **原样保留不解码**，不把 fragment
  当路径。空片段/URL/描述性文本/非 .jsonl 一律不拆，保留原有 missing_original
  诊断（联友其余四条描述性来源即此类，缺口靠人工复核解释，不由工具猜测消除）。
- **容器观察**（`container_accessibility`：accessible|missing|permission-denied|
  inaccessible|not-regular-file|boundary-violation）：沿用同公司边界与观察失败
  语义；越界（含跨公司 symlink）不读目标内容、不跨公司复用同名容器。容器可访问
  时 `source`=容器基座内相对路径、`hash_check=unknown-scope`、
  `projection_accessibility` 单列材料自身读取状态；**锚点一律
  `anchor_verification=not-performed`**——默认不读容器正文、不在内容中匹配
  fragment、不做文本解码（容器坏编码不是锚点失败），`scan.complete` 不代表锚点
  已核验。
- **报告**：顶层 `material_source_fragment_findings[]`（始终存在，按 path/kind/
  容器/fragment 稳定排序；每项含 declared_source 原整串、source_container、
  source_fragment、kind、reason），独立计入 rc=3——容器存在也是发现
  （anchor-not-verified）。容器缺失时 `missing_original` 记**容器**而非原整串，
  并保留原声明与 fragment。`--full-hash` 观察容器记
  `container_sha256_observed`/`container_observed_at`（当前观察，**不写
  source_sha256、不冒充转换时哈希**）；字节读取失败（任意 OSError：EACCES/
  EIO/…）与 stat 存在分开表达——`container_accessibility` 仍记 stat 观察、
  `container_hash_error` 保留 errno、`container_hash_check=not-completed`、
  `hash_check=not-applicable`，finding kind 与 repair 诊断一致为
  container-check-failed，不产生容器哈希、`anchor_verification` 保持
  not-performed。
- **修复诊断**：片段条目已有声明，永不进 `repair_candidates`、不自动生成来源
  回填；`wrong_source_suspects` 记 verifiability=fragment-not-verified /
  container-missing / container-check-failed / boundary-violation（附人工核查
  建议），不落 resolvable-in-base/无需修复，不建议自动重转。
- **非目标**：不解析四条描述性/复合来源、不剥括号、不推断"同名.md"、不扩大
  materials URL 支持、不改 raw 网页识别、不改转换器与回填写入、不要求公司资料
  增补字段；本能力不承诺全库清零（未核验计数独立存在）。后续片段类型（非
  .jsonl）需独立扩展用例与范围，不做通用 fragment 解析框架。

### 转换指纹与增量重跑（convert_doc / convert_excel）

指纹五要素：原件身份+字节哈希、转换器代际（EXTRACTOR_VERSION）、有效选项快照
（convert_excel：date_coerce/header_row/header_scan）、可得时后端版本、预期输出清单+输出指纹。
- convert_excel：指纹记在 `raw/<dir>/_manifest.json`（`options`/`outputs[{path,sha256,bytes}]`/
  `backend`/`fingerprint_format: 1`；整文件哈希只在 manifest 外置记录）。
- convert_doc：MD 文首 provenance 块内联 `output_body_sha256` +
  `output_digest_scope: post-provenance-header`（范围哈希 = 排除文首溯源头的正文范围，
  以 `output_digest_scope` 标记行为头的确定性边界——markitdown 正文自身可能以注释行开头，
  按"连续注释段尾"取边界会漂移；**不做整文件自引用**）。已知残余风险 R2：头块自身被改写
  不在内联保护范围内，完整性要求高的场景走 manifest 外置记录。旧产物无指纹行 = unknown。
- `fingerprint_format`（指纹元数据格式）与 `EXTRACTOR_VERSION`（转换内容语义）分离维护、
  互不倒推；旧产物缺指纹 = `unknown`（不判 up-to-date、不强制重转）。

**模式×状态矩阵**（六态×三模式，`scripts/_fingerprint.py` 为唯一实现，测试逐格钉死）：

| 状态 | 旧默认（无旗标） | `--check` | `--skip-up-to-date` |
|---|---|---|---|
| unknown（有已有输出） | 重转覆盖（=现状，无从检测修改） | 报告 unknown，零写入 | **保留已有输出**+报告需显式重转 |
| unknown（首转/无输出） | 重转 | 报告 unknown，零写入 | 重转（补齐语义不被拦截） |
| up-to-date | 重转（=现状幂等重写） | 报告 | 跳过 |
| source/options/converter-changed | 重转覆盖 | 报告对应状态 | 重转 |
| output-missing | 重转补齐 | 报告 | 重转补齐 |
| output-modified / conflict | **不覆盖**：跳过+报告证据 | 报告+两侧证据 | 跳过+报告 |

`--force-overwrite-modified` 是唯一显式覆盖例外（打印被覆盖清单）；`--check` 任何情况零业务
写入。下游影响只输出 needs_recheck 路径清单，不触碰 `_index.json` 人工 `needs_review`；
多 sheet/改名/路由变化产生的旧输出进 orphan-outputs 盘点，**永不自动删除**。

### manifest 预写检查与锁文件守卫

- convert_excel 在本项目**任何输出写入前**解析+结构校验目标 `_manifest.json`：不可解析/
  结构非法（非记录数组、缺 source_path）/同 source_path 内容冲突 → 该项失败、manifest 与
  已有输出字节保留、显式报告；批量继续其他独立项目并汇总失败。半成功（输出写而 manifest
  未更新）必须报错，不是可接受状态。
- Office `~$` 锁文件：**输入侧** basename 前缀在调用 openpyxl/libreoffice/markitdown 之前
  拦截——convert_doc / extract_images 单文件 exit 3（skipped 语义，非格式错误），convert_excel
  批量列 skipped 不阻断整批；**投影侧**文件名中部 `~$` 只是体检候选线索（见上）。
  前缀规则只作用输入侧，不适用于历史投影。既有 OOXML(PK)/PDF(%PDF-)/OLE2 魔数守卫保持不变。


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
- **text-sparse 实测基线（2026-10-30 海鼎试点）**：81 页混合型方案 PPT 检出 17 页（21%），其中真实"界面截图+标签文字"页约 2/3、封面/分隔/致谢预期误报约 1/3；text-sparse 页回看可能**修正业务语义**（实证：正文标签"线上商城商品录入"回看实为"商品数量录入单含审批流"），但回看不改变证据层级上限（proposal 仍 medium）。回看入口优先用既有 `_media` 投影（`image_s<N>_*`），原件 python-pptx 提取为备选
- 检测失败语义 = `undetermined (detect-error: 原因)`，与 `none`（成功无发现）严格区分；v1 及更早转换的旧 raw 产物没有 `pptx_text_sparse` 行仍是合法产物（不回填、不重转），该行只出现在 v2 起重新转换的文件
- **MD 内联指纹不保护头块自身（R2，设计 D3 明示）**：convert_doc 的 `output_body_sha256` 只覆盖文首注释块之后的正文；头块被手工改写无法内联检出（自引用无解），完整性要求高的走 manifest 外置记录
- **exit 3 / 新旗标对既有调用方是新增枚举**：convert_doc/extract_images 单文件遇 `~$` 锁文件 exit 3（skipped 语义）；目前无调用方依赖"非 0 即崩"语义
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
- **模式×状态矩阵取代"默认覆盖 vs 冲突不覆盖"并存表述（v7，设计 D2）**：unknown 态旧默认保持现状覆盖（兼容性来源）；一旦指纹在册且检出 output-modified/conflict，**全部模式**不静默覆盖，`--force-overwrite-modified` 为唯一例外——"新安全模式不覆盖人工修改"是全模式统一约束，不是新旗标专属
- **MD 内联指纹用正文范围哈希（设计 D3）**：文件内字段不可能包含自身的整文件 SHA-256（自引用无解）；范围 = 文首 provenance 块之后到 EOF；整文件哈希只在 manifest 外置记录
- **溯源修复候选三级不互相冒充（设计 D7）**：candidate-association / recorded-at-conversion / reconverted 随产物持久化；recorded-at-conversion 须 D7 三要件齐备且仅证明存在转换时点来源声明；当前原件哈希≠历史记录哈希属 freshness 维度（source-changed），不算记录不可信
- **多公司基座隔离（设计 D11）**：体检/匹配索引/指纹以单一基座为 scope；无效公司上下文沿用 resolver 失败语义（无 lanlnk 回退）；越界声明只报告不跟随读取
- **锁文件两侧规则（设计 D5）**：输入侧 basename `~$` 前缀拦截（在格式转换/外部依赖调用之前）；投影侧文件名中部 `~$` 仅候选线索——两侧是两回事，互不套用

## 维护规则

- 任何写 `$COMPANY_BASE` 的脚本必须过五道闸门：dry-run 先行 / 唯一匹配才写 / 分桶上限 / validator 前后基线 diff 零新增错误 / has-source 绝不重写
- 改 SKILL.md / AGENTS.md 触发 pre-commit 的 `check_skill_ecosystem.sh --ci`——提交前本地先跑
- 共享文件 `references/domain-tags.md` 被 product-prd-generator / compound-learning 读取，改动需同步 AGENTS.md「Shared files」表和 `check_docs_consistency.sh` 的 `SHARED_FILES` 数组
- 修复新坑 → 先加回归测试再修代码；驱动修复的金样例登记在 `tests/fixtures_registry.json`（引用外部仓路径+sha，不复制二进制）
- convert_excel 逻辑变更须 bump `EXTRACTOR_VERSION`（manifest 溯源依赖它区分产物代际）；指纹元数据格式变化（加字段/改语义）则 bump `fingerprint_format`——两者分离维护、互不倒推（v7 设计 D6）
- 共享文件 `references/provenance-evidence-boundary.md`（证据边界唯一权威源）被 competitor-product-analyzer 读取，改动需同步 AGENTS.md「Shared files」表和 `check_docs_consistency.sh` 的 `SHARED_FILES` 数组
- 批量导入 ≥50 件必须分层抽样质检：抽 20 份分层样本（厂商×来源型×子目录），按 5 维准则评分——内容健全性 / frontmatter 准确性（含 id 唯一性）/ 溯源链可解析 / 表格完整性 / OCR 可信度；批级通过率 <90% 的维度视为批缺陷。依据 2026-10-17 质检实证：4 个缺陷中 3 个纯机械流程不可见。
