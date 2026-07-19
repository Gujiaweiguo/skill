---
name: product-prd-generator
description: |-
  通用产品 PRD 生成 Skill。以现有代码库作为产品基线，结合客户需求、竞品资料、手册、蓝图、截图和图片证据，
  生成统一功能清单、差距分析和内部产品 PRD。适用于商管/会员/CRM/供应链等多业务系统。
  支持两种模式：
  - `--mode generate`（默认）：全量生成 PRD + 功能清单 + 差距分析 + 版本规划 + 实施分期，用于首次生成或主干重构。
  - `--mode coverage-validate`：新材料入库后对照现有 PRD + 代码做覆盖度校验，输出客户×竞品覆盖度矩阵和增量 gap 报告，不重跑全量 PRD，适用于 PRD v1.x 持续完善。
  触发场景："做一份商管 PRD"、"出产品 PRD"、"整理客户需求和竞品资料出 PRD"、"客户/竞品资料入库了看增量 gap"、
  "新材料入库后做覆盖度校验"、"PRD v1.x 持续完善"、"功能清单"、"差距分析"、"版本规划与实施分期"、
  "商管/会员/CRM/供应链产品规划"、"基于现有产品做版本规划"。
  仅面向内部产品规划与决策，不生成报价/方案/投标文件（那些交给 company-intro-generator / pricing-generator / bid-doc-master），
  不直接修改业务系统代码（业务系统自己基于本 skill 输出的交接文档拆 OpenSpec change）。
compatibility: Requires Python 3.10+ and uv. Reuses material-importer for doc-to-md conversion and image extraction. Reads code from specified code-root (default /opt/code/mi). Outputs to $LANLNK_BASE/out/prd/<项目>/output/.
---

# Product PRD Generator

## DocSpec 质量基线

本 skill 生成的 PRD、功能清单、差距分析、需求证据表和 review 清单必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `DocSpec-通用文档质量规范.md`、`PRD质量规范.md` 和 `文档验收清单.md`。跨 PRD/方案/投标等多个文档类 skill 的质量经验，通过 `compound-learning` 回流到 DocSpec；只影响本 skill 的限制写入本 skill references。

## References 索引（按需读，不要全读）

| 文件 | 何时读 |
|---|---|
| `references/troubleshooting.md` | 第一次跑本 skill、踩坑时、修改 SKILL.md 前。必读 |
| `references/coverage-validate-mode.md` | 跑 `--mode coverage-validate` 模式时。覆盖度矩阵评分规则、增量 gap 检测逻辑 |
| `references/feature-taxonomy.md` | 抽取功能清单时。功能分类与命名规范 |
| `references/prd-template.md` | 渲染 PRD 时。PRD 章节骨架模板 |
| `references/reconciliation-schema.json` | 写 `parsed/capability-reconciliation.json` 时。中闯产物的 schema |
| `references/review-template.md` | 写 `review/pending-items.md` 时。待确认事项模板 |
| `references/term-aliases.yaml` | 跑术语归一（Step 4）时。术语别名表，扩充覆盖率靠加这个文件 |

## 目标

将多来源材料合成为内部产品规划资产：

- 当前产品基线
- 客户需求汇总
- 竞品能力证据
- 功能清单
- 差距分析
- 版本规划
- PRD

## 适用场景

- 多业务系统产品规划（商管/会员/CRM/供应链等）
- 多客户需求汇总
- 多竞品资料归纳
- 基于现有产品进行版本规划
- 需要保留界面截图、流程图、表单图等视觉参考

> **域知识隔离**：本文件只记录**通用 PRD 方法论**。各业务系统的域专属知识（术语/单据流/算法/竞品基线）存放在**各项目目录**下的 `域知识.md`。当前已有：
> - `$LANLNK_BASE/out/prd/商管系统/域知识.md` — 商管系统域知识
> - 未来新增会员/CRM 时创建 `$LANLNK_BASE/out/prd/会员系统/域知识.md`

## 不做什么

- 不生成报价
- 不做强竞品胜负排序
- 不删除原始文件
- 不丢图片证据
- 不直接把内容入 materials 入库
- 不把未确认内容写成最终结论

## 输入来源

### 1. 当前产品代码基线

- `/opt/code/mi`

### 2. 原始文档

- `$LANLNK_BASE/out/prd/商管系统/input/00-current-product/`
- `$LANLNK_BASE/out/prd/商管系统/input/01-customer-requirements/`
- `$LANLNK_BASE/out/prd/商管系统/input/02-competitors/`

### 3. 转换后的中间资料

- `$LANLNK_BASE/out/prd/商管系统/raw/`

## 目录规范

```text
/opt/code/docs/lanlnk/out/prd/商管系统/
├── input/
│   ├── 00-current-product/
│   ├── 01-customer-requirements/
│   └── 02-competitors/
├── raw/
├── parsed/
├── review/
└── output/
```

## 材料处理原则

1. 原始文件保持不动。
2. 先转 markdown，再做功能提取。
3. 图片必须保留，用于界面与流程借鉴。
4. 任何竞品资料只能作为“能力证据”，不能默认代表完整覆盖。
5. 资料缺失时，标记为“未发现”或“待确认”，不能推断为不存在。
6. 代码与文档冲突时，不强行合并，进入 gap 分析。

## 标准流程

### Step 1: 原始文档转换
复用 `material-importer` 的转换能力：

- 支持 `docx / pptx / xlsx / pdf`
- 生成对应 markdown
- 提取图片到 `raw/*_media/`

### Step 2: 材料识别
识别来源类型：

- `current-product`
- `customer-requirements`
- `competitor`

识别资料类型：

- 操作手册
- 功能手册
- 蓝图方案
- 汇报方案
- 业务逻辑
- 用户场景
- 功能清单

### Step 3: 功能抽取
抽取字段至少包括：

- 功能名
- 模块
- 原始术语
- 标准术语
- 功能描述
- 场景
- 角色
- 流程
- 规则
- 表单/字段
- 接口/集成
- 图片证据
- 来源文件
- 来源页码/位置
- 置信度
- 结构类型（功能 / 数据结构 / 流程 / 权限）

**通用补充要求**：
- 如果资料同时包含"数据逻辑 / 表结构 / 字段说明"，必须单独标记为"数据结构"，不要压成普通功能标题。
- "用户组 / 岗位 / 角色 / 授权组 / 数据权限 / 模块权限 / 流程审批链 / 委派 / 候选人"必须优先识别为权限或流程类需求。
- 业务对象（合同/客户/订单等）材料里出现的表格标题，不要默认当成普通需求名；需要保留它们的层级和上下文。
- 术语变体多的域（如商管合同条款），只在**精确章节标题**命中时才标记为特殊结构类型，避免噪音扩散。
- 多来源合并时，选定一个**权威结构模板来源**（如商管的海鼎），其他来源只补证据，不做平均融合。

> **商管域专属补充要求**（条款组识别/海鼎家族合并/家族别名归一）见 `$LANLNK_BASE/out/prd/商管系统/域知识.md`。

### Step 4: 术语归一
把不同材料里的说法统一映射到标准功能名。每个域有自己的术语别名表。

> **商管术语归一实例**（租户服务/资产管理/合同管理等）见 `$LANLNK_BASE/out/prd/商管系统/域知识.md`。

### Step 5: 当前产品映射
对每个功能标记状态：

- `existing`
- `partial`
- `missing`
- `explicitly-not-do`

并补充：

- `confidence`: `high | medium | low`
- `signals`: 代码与文档的辅助判断信号

### Step 6: 合并与对齐
生成统一能力视图：

- 代码事实
- 文档事实
- 客户需求
- 竞品证据

冲突时进入 gap 分析，不直接覆盖。

### Step 7: 输出
至少生成：

- 功能清单
- 竞品功能清单
- 差距分析
- 需求证据表
- PRD

## 中间产物

### `parsed/current-code-map.json`
代码侧事实，来自 `/opt/code/mi`。

### `parsed/current-doc-map.json`
文档侧事实，来自 `raw/*.md` 和 `raw/*_media/`。

### `parsed/capability-reconciliation.json`
统一后的能力对齐结果。

### `review/pending-items.md`
需要人工确认的问题。

## 代码输入规则

`/opt/code/mi` 作为当前产品基线，优先读取：

- 路由
- 页面组件
- API / service
- model / schema
- permission / role
- tests
- OpenSpec specs
- alignment artifacts
- evidence artifacts

代码的作用是定义“当前实际做到了什么”，不是定义“应该做什么”。

## 状态规则

使用统一状态：

- `existing`
- `partial`
- `missing`
- `explicitly-not-do`

说明：

- `existing`：已有且证据充分
- `partial`：有实现，但不完整
- `missing`：当前未见实现
- `explicitly-not-do`：明确不做

## 置信度规则

- `high`：代码与文档一致，且证据充分
- `medium`：有部分证据，但存在缺口或歧义
- `low`：仅有弱证据，或存在明显冲突

## review 机制

所有自动抽取结果先进入 `review/`，人工确认后再写入 `parsed/` 或 `output/`。

### `review/pending-items.md` 记录内容

- 模块归属不清
- 术语映射不清
- 代码与文档冲突
- 竞品资料无法确认
- 图片只能辅助判断，不能单独定论

## 输出目录

```text
output/
├── 产品PRD.md
├── 功能清单.md
├── 竞品功能清单.md
├── 差距分析.md
├── 需求证据表.md
├── PRD实施交接包.md
├── suggested-openspec-changes.yaml
└── mi-consumption-prompt.md
```

## PRD 结构

1. 产品背景
2. 当前产品基线
3. 客户需求汇总
4. 功能清单
5. 差距分析
6. 版本规划
7. 界面 / 流程参考
8. 风险与待确认项
9. 附录

## 关键约束

- 原始文件不删
- 图片不删
- 原词保留，标准词唯一
- 未确认项必须进 review
- 竞品缺失不等于不存在
- 代码 partial 不等于 complete
- 所有结论必须可追溯到证据

## 运行方式

### OpenCode 对话调用（默认给用户）

用户不需要手工复制 CLI。日常建议在 `/opt/code/docs` 启动 OpenCode，让 agent 使用本 skill；需要运行 CLI 时，由 agent 自行进入 `/opt/code/skill/skills/business/product-prd-generator` 执行内部命令。

首版 PRD：

```text
请使用 product-prd-generator 为“商管系统”生成首版 PRD、功能清单、差距分析和 PRD 实施交接包。

上下文：
- 当前产品代码基线：/opt/code/mi
- PRD 原始/转换资料根：$LANLNK_BASE/raw/prd-商管系统
- PRD 输出目录：$LANLNK_BASE/out/prd/商管系统/output
- parsed 目录：$LANLNK_BASE/raw/prd-商管系统/parsed

要求：
1) 先读取 /opt/code/skill/skills/business/product-prd-generator/SKILL.md 和 DocSpec PRD 质量规范
2) 自动执行需要的内部命令，不要让我手工复制长命令
3) 输出完成后列出关键产物路径
4) 确认生成 PRD实施交接包.md、suggested-openspec-changes.yaml、mi-consumption-prompt.md
5) 不修改 /opt/code/mi，不创建 MI 的 OpenSpec change
```

增量覆盖度校验：

```text
请使用 product-prd-generator 对“商管系统”运行 coverage-validate，检查新材料带来的覆盖度变化和增量 gap。

上下文：
- 当前产品代码基线：/opt/code/mi
- PRD 资料根：$LANLNK_BASE/raw/prd-商管系统
- PRD 输出目录：$LANLNK_BASE/out/prd/商管系统/output
- parsed 目录：$LANLNK_BASE/raw/prd-商管系统/parsed
- baseline：$LANLNK_BASE/raw/prd-商管系统/parsed/coverage-baseline.json

要求：
1) 先读取 /opt/code/skill/skills/business/product-prd-generator/SKILL.md，再自动执行 coverage-validate 并更新 baseline
2) 输出客户需求覆盖度矩阵、竞品覆盖度矩阵、增量gap报告
3) 生成 suggested-openspec-changes.yaml 和 mi-consumption-prompt.md
4) 汇总本轮 P0/P1/P2 缺口、待复核项和是否适合直接交给 MI
5) 不修改 /opt/code/mi，不创建 MI 的 OpenSpec change
```

### CLI 执行参考（agent 内部）

以下命令是 OpenCode agent 的内部执行参考，不作为用户日常操作入口。

#### generate 模式（默认）

全量生成 PRD + 功能清单 + 差距分析。

```bash
cd skills/business/product-prd-generator
uv sync
uv run product-prd-generator --project 商管系统 \
  --code-root /opt/code/mi \
  --docs-root $LANLNK_BASE/raw/prd-商管系统 \
  --skill-root /opt/code/skill/skills/business/product-prd-generator \
  --parsed-dir parsed \
  --output-dir output
```

#### coverage-validate 模式

新材料（客户需求/竞品资料）入库后，对照现有 PRD + 代码做覆盖度校验，输出矩阵和增量 gap，不重跑全量 PRD。适用于 PRD v1.x 持续完善。

```bash
cd skills/business/product-prd-generator
uv run product-prd-generator --project 商管系统 \
  --code-root /opt/code/mi \
  --docs-root $LANLNK_BASE/raw/prd-商管系统 \
  --skill-root /opt/code/skill/skills/business/product-prd-generator \
  --parsed-dir $LANLNK_BASE/raw/prd-商管系统/parsed \
  --output-dir $LANLNK_BASE/out/prd/商管系统/output \
  --mode coverage-validate \
  --baseline $LANLNK_BASE/raw/prd-商管系统/parsed/coverage-baseline.json \
  --update-baseline
```

可选参数：
- `--customers 万达,深圳中旅,...`：限定纳入矩阵的客户
- `--competitors 海鼎,明源,...`：限定纳入矩阵的竞品
- `--baseline <path>`：上次运行的签名快照，用于增量检测
- `--update-baseline`：本次运行结束后更新 baseline

输出文件：

| 文件 | 用途 |
|---|---|
| `output/PRD客户需求覆盖度矩阵.json` | 结构化矩阵，供下游工具消费 |
| `output/PRD客户需求覆盖度矩阵.md` | 人类可读矩阵 |
| `output/PRD竞品覆盖度矩阵.json` / `.md` | 同上，竞品维度 |
| `output/增量gap报告.md` | 本次新材料带来的新缺口（已匹配 + 未匹配分开） |
| `output/suggested-openspec-changes.yaml` | 按 P0/P1/P2 给目标项目消费的建议 change 清单 |
| `output/mi-consumption-prompt.md` | 到 `/opt/code/mi` 或目标项目后可直接粘贴的消费提示词 |
| `review/evidence-weak-items.md` | 机器无法确定的证据强度，需人工确认 |

两种模式对比：

| 维度 | generate | coverage-validate |
|---|---|---|
| code_map / doc_map / reconcile | ✅ | ✅ |
| render（全量 PRD） | ✅ | ❌ |
| 覆盖度矩阵 | ❌ | ✅ |
| 增量 gap | ❌ | ✅ |
| 弱证据 review | ❌ | ✅ |
| 适用场景 | 首次生成 / 主干重构 | 持续完善 / 新材料校验 |

证据强度评分规则详见 `references/coverage-validate-mode.md` §6。

### 新竞品/新资料入库流程

新增竞品或老竞品增加资料时，流程与现有覆盖度校验完全相同：

1. **转换原始文档**：用 `material-importer` skill 把 docx/xlsx/pdf 转成 md + 提取图片
2. **放入正确目录**：
   - 竞品操作手册/蓝图/功能手册 → `$LANLNK_BASE/raw/prd-商管系统/02-competitors/{竞品名}/`
   - 竞品数据结构/PRD 草案 → `$LANLNK_BASE/materials/13-competitors/{竞品名}/`
   - demo 探测数据 → `$LANLNK_BASE/out/prd/商管系统/competitor-analysis/{竞品名}/`
3. **跑覆盖度校验**：`--mode coverage-validate` 会自动扫描上述三个目录
4. **看 gap 报告**：`增量gap报告.md` 的"竞品未匹配能力汇总"会列出新增竞品有多少能力被识别
5. **扩 ontology**：如果新竞品术语未归一，在 `references/term-aliases.yaml` 中补充别名映射

> **术语归一瓶颈**：矩阵单元格是否填充取决于 `term-aliases.yaml` 的覆盖率（当前 ~19%）。新竞品的能力名称如果不在别名表中，会显示为"—"，但不影响基础设施正确性。持续扩充 term-aliases 是提升矩阵覆盖率的唯一路径。

## 交付原则

这个 Skill 的核心不是"写 PRD"，而是：

- 抽能力
- 统一术语
- 对齐代码
- 找 gap
- 再生成 PRD

### PRD→目标项目实施交接

`generate` 模式会额外输出三份实施交接产物：

| 文件 | 用途 |
|---|---|
| `PRD实施交接包.md` | 面向目标项目团队的人类可读交接包，包含边界、状态概览、建议拆分、回写要求 |
| `suggested-openspec-changes.yaml` | 结构化建议 change 清单，供目标项目会话读取和二次确认 |
| `mi-consumption-prompt.md` | 在 `/opt/code/mi` 或其他目标项目 OpenCode 会话中直接粘贴的提示词 |

交接规则：

1. PRD 侧只提供证据、优先级和建议拆分，不在目标项目仓库创建 change。
2. 目标项目会话必须重新读取自己的 `AGENTS.md`、`openspec/specs/`、代码和测试基线。
3. 首版 PRD / 大差异 / 多 change 先用 `Prometheus` 输出 Implementation Plan v1。
4. 单个明确增量 gap 用 `Sisyphus` 创建普通 OpenSpec change。
5. 执行用 `Atlas`；verify 失败或根因复杂时再切 `Hephaestus - Deep Agent`。

## 已知限制

- **PDF 转换需要 poppler-utils**：`apt install poppler-utils`。无 sudo 权限时，PDF 无法用 markitdown 转换，需要 LibreOffice 预转换或手动转 md。当前项目有 6 个竞品 PDF 受此影响（政策文件，影响小）。
- **匹配率 ~19%**：瓶颈是**术语覆盖率**（ontology 572+ 术语），不是匹配策略。两阶段匹配提升精确度但不提升召回率。继续扩 ontology 术语是唯一提升路径。
- **business-ontology.yaml 运行时依赖**：doc_map 从 `$LANLNK_BASE/config/ontology/business-ontology.yaml` 加载。文件缺失时退化为纯 term-aliases 匹配（匹配率回到 ~12%）。
- **YAML OrderedDict 序列化陷阱**：在 ontology/specs 中使用 `OrderedDict` 后 `yaml.dump` 会写入 Python 特有的 tag（`!!python/object/apply:collections.OrderedDict`），导致 `yaml.safe_load` 报 ConstructorError。**必须用普通 dict**。详见 troubleshooting.md。
- **field-specs YAML 完整性**：`module-field-specs.yaml` 在多次编辑后可能丢失实体（如 OrderedDict 序列化失败导致 yaml.safe_load 无法读取→数据丢失）。每次大改后应验证实体数量：`len(mfs['招商管理'])` 等。
- **噪音过滤可能误判**：`_is_noise_text` 过滤编号、元数据、表格残留、图片路径、JSON 块、句子型文本。极端情况下可能误杀合法标题。
- **word-master .venv 依赖**：word_export 调用 word-master 时依赖其目录下的 `.venv`。如果 word-master 目录未 `uv sync`，会报 `ModuleNotFoundError: docx`。
- **OCR 数据结构去重陷阱**：OCR 提取的表名标题（如 `数据结构 m3newcontractrequest（新合同申请）`）经过 `_normalize_term()` 后全部归一到同一业务术语（如 `lease-contract-management`）。`_parse_requirements()` 用 `normalized` 做 dict key 去重，导致 117/214 张表被吞。已修复：以 `数据结构` 开头的标题用 heading 原文做 key。新增 OCR 数据源时注意这个模式。
- **OCR all-ocr.md 噪音**：`ocr_extract.py` 生成的人类可读汇总 `all-ocr.md` 会被 `_iter_markdown_files()` 当作需求源解析，产生图片文件名噪音。PRD 生成前必须删除 `_extracted/all-ocr.md`，只保留 `haiding-data-model.md`。
- **Ontology 必须与 field-specs 双同步**：`module-field-specs.yaml` 中新增的实体不会自动出现在 PRD 中——渲染器 `_render_blueprint_modules()` 按 `business-ontology.yaml` 的 `sub_functions` 遍历，只渲染 ontology 中存在的实体。**新增实体必须同时加到两个文件**，否则 field-specs 有内容但 PRD 不显示，且不会有报错。
- **产品PRD.md 为唯一权威输出**：Markdown 渲染器（`render.py`）和 Word 渲染器（`word_export.py`）是两套独立逻辑，同时维护容易内容分叉。当前暂停 docx 生成，只维护 `产品PRD.md`。运行时不传 `--docx-output` 参数即可。
- **YAML 部分重写致命陷阱**：**永远不要用 `yaml.safe_dump` 部分重写大 YAML 文件中的某个模块**。原因：`safe_dump` 会重新格式化整段内容，且用正则查找下一个模块边界时 `\n[a-zA-Z]` 不匹配中文字符（如 `\n合同管理:` 的 `合` 不是 ASCII 字母），导致 `end` 定位到文件末尾，后续所有模块被截断删除。**正确做法**：用纯文本操作（`str.index("模块名:")` 精确匹配中文字符串），或对整个文件 `safe_load → safe_dump`（全量重写）。已在一次事故中丢失合同管理+财务管理+运营+物业+系统+推广共 6 个模块约 5000 行 YAML。
- **Ontology sub_functions 必须与 field-specs 全局同步**：ontology 的 `sub_functions` 有旧名称而 field-specs 没有对应实体时，渲染器会产生**空 `####` 标题**（有标题无内容）。这不是报错而是静默问题。每次大改后应做全局同步检查：`ont_subs == spec_keys` for all modules。

> 商管域专属已知限制（资产管理空壳/集团驾驶舱图表库缺失/销售五源模型）见 `$LANLNK_BASE/out/prd/商管系统/域知识.md`。
- **AI 产品 PRD 适配说明**（非商管系统场景）：本 skill 的 `term-aliases.yaml`、`business-ontology.yaml`、CLI（`uv run product-prd-generator`）**硬编码商管域**（8模块：招商/合同/财务/营运/物业/系统/推广 + 商管术语），对 AI 产品（LnkChatBI/OrchestratorAgent/langchat 等）会产生严重噪音。**AI 产品 PRD 必须手工生成**，不要运行 CLI。手工生成时遵循 SKILL.md 的**通用方法论**（7步流程/状态规则/置信度/review机制/分期方法论/PRD→代码术语映射），但**忽略商管域专属内容**（ontology/term-aliases/单据驱动渲染/三层架构/移动端一体化）。AI 产品的功能域按产品实际组织（如 ChatBI 的功能域 = 对话问数/Text-to-SQL/RAG校准/数据源/嵌入/MCP/系统管理），不是商管的招商/合同/财务。已完成的 AI 产品 PRD 样板：`$LANLNK_BASE/out/prd/{LnkChatBI,OrchestratorAgent,langchat}/output/`。

## 设计决策

### 六维需求框架（Rule 1C + 2B + 3B）

需求提取采用 leaf-only（只有叶子标题成为需求），heading 层级提供场景上下文：

```
depth 1 → scenario（场景，不单独成需求）
depth 2 → sub_scenario（子场景，不单独成需求）
depth 3+ → function（叶子标题 = 需求）
```

每条需求携带六维：`scenario | sub_scenario | function | nearby_text(首段) | source_customer | priority`

**nearby_text（Rule 2B）**：heading 后第一段（≤200字），用于提取痛点/描述。
**优先级（Rule 3B）**：`min(customers,3) + status_score + value_keyword_score`。unmatched ≠ missing（unmatched 得 1 分，missing 得 2 分）。

### 两阶段匹配

```
Phase 1: scenario + function → 加权分类到 ontology 模块
         scenario match ×3, sub_scenario ×2, function ×1, term ×0.5
Phase 2: 只在模块的 sub_functions 术语里匹配（longest first）
Fallback: Phase 2 无匹配 → flat alias matching（现有行为）
```

**效果**：精确度提升（匹配到正确业务域），召回率持平（瓶颈是术语覆盖不是策略）。

### Alias 长度排序

`_normalize_term` 按 alias 长度**降序**匹配。确保 "合同模板"（4字）优先于 "合同"（2字）。**不排序会导致宽泛 alias 抢匹配。**

### Dedup key: (normalized_term, source_file)

**不用 `normalized_term` 单独做 key**。宽泛 alias 会把不同 heading 归一化到同一 term，跨文件 dedup 会坍缩它们。用 `(normalized_term, source_file)` 保留不同文档的独立需求。

### 章节号清除

`_strip_section_prefix` 去除 heading 前的编号（"2.3.3 合同台账" → "合同台账"）。不清除会导致 "2.3.3" 开头的 heading 无法匹配。

### reconcile stale gap 清理

doc feature 匹配到 spec capability 后，移除 `"spec has no doc evidence yet"` 等过时 gap。**不清理会导致每个已匹配 capability 都带着过时 gap，污染输出。**

### unmatched 需求排序策略

深度优先（depth 1-2 的核心模块优先）+ 客户数倒序（多客户共同需求优先），封顶 80 条。

### doc_map.py 三种提取方式

| 方式 | 正则 | 解决什么问题 |
|------|------|-------------|
| `_HEADING` | `^#{1,6}\s+` | 标准 markdown 标题 |
| `_BOLD_HEADING` | `^\*\*(.+?)\*\*$` | 万达文档用 `**加粗**` 当标题（无 # 前缀） |
| `_TABLE_ROW` | `^\|(.+?)\|(.+?)\|` | 中旅/锦和/安居文档用 xlsx 表格列当功能点 |

**`_TABLE_ROW` 必须带 `re.MULTILINE`**：否则 `^$` 锚点不匹配多行文本，一行都提取不到。

### 图片证据去重与区段限制

- **`seen` set 去重**：`_collect_image_refs` 用 `seen` 避免同一图片重复挂到多个 feature。
- **区段限制**：`_nearby_image_refs` 只挂标题所在区段内的图片（从当前标题到下一个 `#` 标题之间），避免所有图片挂到第一个标题。
- **media_dir stem 双候选**：`foo.docx.md` 的 stem 是 `foo.docx`，但 media_dir 可能叫 `foo_media`。双候选 `[md_path.stem, md_path.stem.rsplit(".",1)[0]]` 解决此问题。

### term-aliases.yaml 用英文 spec capability ID 做 key

**原因**：reconcile 的 `by_id` 字典用 spec ID 做 key。aliases 必须把中文 heading 映射到这些英文 ID，否则匹配失败。

### word_export 跨 skill 调用

**不用 `python3` 直接调用 word-master**，而是在 word-master 目录下用 `uv run python -m src.main`。内容包路径必须 `.resolve()` 转绝对路径。`nearby_text` 可能含控制字符（\x00-\x1f），必须 `_sanitize` 后才能写入 docx。

### 单据驱动渲染：来源参考 + 空实体检测

**来源参考（sources）是强制性的**。每个 document spec 必须有 `sources` 字段，标注具体文档+章节（如 `"海鼎合同管理手册 §新合同申请单"`）。render.py 的 `_render_field_spec_module` 会渲染 `**来源参考**` section。

**没有 sources 的 document = 主观臆想，不是 PRD**。用户明确要求："每个场景都要在客户需求或竞品处找到参考，而不是你主观的想法"。

**空实体检测**：ontology 中有 sub_function 但 module-field-specs 中无对应 documents 时，render 输出 `"- ✅ capability"` 一行——这看起来"已处理"但实际无内容。**要么给它 documents with fields，要么不要创建 sub_function**。

### 实体命名三原则

PRD 中的实体/单据名称必须满足：

1. **短**（≤4-5字）：优先用高辨识短名
2. **可搜**：在模块上下文中是高辨识词，搜索一次命中
3. **不撞**：不与同模块其他实体共用前缀

### 台账/预警/报表：不创建实体

以下三类内容**不应作为业务模块的 sub_function**：

- **台账** = 报表视图，不是数据实体
- **预警** = 跨模块通用功能，放在系统管理/预警配置
- **自定义报表** = 系统功能，放在系统管理/自定义报表

### 模块结构遵循客户心智模型

当客户需求文档已有清晰的模块归类时，**遵循客户的结构**，不要自创分类。**原则**：source documents 的结构 IS the requirements。

> 商管模块结构实例（中旅/海鼎/华侨城具体归类）见 `$LANLNK_BASE/out/prd/商管系统/域知识.md`。

### 业务单据流：上游导入支持

业务流程中的单据不是孤岛——每个单据应支持从前序单据导入数据。实现模式：下游单据有 `来源` 字段（直接新建/从前序单据转入），选择后联动 `来源单号`。被导入的字段标注"自动带出"，且可修改覆盖。

> 商管单据链实例（招商洽谈→报价→意向→条件报批→合同→应收）见 `$LANLNK_BASE/out/prd/商管系统/域知识.md`。

### 复杂模块三层架构：实体库 + 配置矩阵 + 操作差异矩阵

复杂模块（合同/财务/会员等）的 PRD 不要在每个实体（生成/模板/变更/终止）里重复列字段。采用三层架构：

```
第一层：实体库（单一事实源）— 全部字段唯一定义位置
第二层：配置矩阵 — 控制哪些字段对哪种类型可见（开关表），不列字段定义
第三层：操作差异矩阵 — 每种操作类型只列"能改什么/锁定什么/触发什么"（差异表），不列字段定义
```

> 商管合同/财务的具体实例见 `$LANLNK_BASE/out/prd/商管系统/域知识.md`。

### `markdown` 字段支持矩阵渲染

`_render_field_spec_module()` 对 document spec 中 `markdown` 字段（字符串列表）的渲染——原样输出为 markdown 块。用于嵌入表格矩阵，不需要 `fields` 定义。渲染顺序：`##### doc_name` → 场景 → fields（如有）→ markdown（如有）→ 约束 → 来源 → 流程。

### 竞品对比分析作为设计基线

做模块 PRD 优化前，先对全部竞品/客户做横向对比分析，提取架构共识和独特概念，按 P0/P1/P2/P3 分层。

> 商管竞品对比基线（12家来源）见 `$LANLNK_BASE/out/prd/商管系统/域知识.md`。

### 模块 PRD 优化方法论（可执行清单）

0. **审计现状**（先审再定策略）：读权威手册目录 → grep 当前 PRD 已有实体和字段量 → 计算覆盖率 → 判断是"需要重构"（覆盖率<50%或结构有重复）还是"只需增强"（覆盖率≥80%且结构合理）。**审计结果决定后续工作量。**
1. **读权威手册目录**：以此作为分类基础
2. **竞品横向对比**：提取架构共识+独特概念
3. **定架构**：用三层架构定信息架构，讨论确认后再动手
4. **补全实体库**：单一事实源实体按手册目录补全所有标题和字段
5. **重写非实体库实体**：模板→控制矩阵，变更→差异矩阵，操作类→操作矩阵
6. **加操作流水线矩阵**：如果模块的单据构成 pipeline，新增"流转矩阵"实体
7. **吸收竞品概念**：独特概念单独建实体
8. **配置分组矩阵**：15+ 平铺字段时按主题分组
9. **双同步**：field-specs + ontology 同步
10. **验证**：只生成 MD；验证 ontology 与 field-specs 实体数一致

### 移动端一体化架构（而非独立中台）

**架构选型方法论**：审批场景是决定性因素。

- 独立中台方案下，审批流程需要跨两个 BPM 引擎协调，一致性风险高
- 一体化方案下，一个 BPM 引擎在 PC 端运行，移动端通过 API 获取待办/提交审批，零同步问题
- **决策标准**：如果移动端需要处理 PC 端发起的审批流程，必须选一体化

**关键洞察**：移动端的价值在前端体验（GPS/扫码/拍照/离线缓存/消息推送/手写签名/语音录入），不在后端。

### 操作型 vs 主数据型分离

**判断标准**：如果功能有状态流转（状态机），它是操作型（事务单据），归业务流程模块；如果功能是静态属性维护，它是主数据型，归资源/基础数据模块。

### 移动端功能文档的数据标注规范

一体化架构下，移动端功能文档用 **「数据访问」** 标注（API 实时访问/写入 PC 端），**不用**「数据流向」（同步/回传——这是已废弃的独立中台旧概念）。PC 端模块如有对应移动端执行功能，加 **「执行端在移动端」** 跨模块引用标注。

### 实施分期方法论（闭环优先，适用于商管/CRM/供应链）

PRD 生成后，必须输出一份“PRD vs 代码差异及实施建议”交接文档，按业务闭环而非模块名分期。该方法是跨系统可复用的，未来做 CRM、供应链等产品 PRD 时同样适用。

**分期标准**：

| 阶段 | 判断标准 | 商管实例 | CRM 实例 |
|---|---|---|---|
| **P0** | 可上线运营的最小端到端闭环 | 资源→招商→合同→财务→营运/物业→退出→资源释放 | 线索→客户→商机→报价/合同→回款/服务→续约 |
| **P1** | 交付可用性与管控增强 | 移动端、报表设计器、流程增强、销售五源、招商/合同/财务增强 | 移动端、自定义报表、流程增强、客户分层、商机漏斗分析 |
| **P2** | 数据决策与集团管控 | 经营看板、集团驾驶舱、预算深化、深度集成 | 客户画像、流失预警、续约预测、BI 看板 |
| **P3** | 非主闭环拓展能力 | 企划/推广、资产管理对接、NOI/CAP | 营销自动化、社交 CRM、CDP 对接 |

**关键原则**：
1. **P0 是闭环不是切片**：不能"每个核心模块做一点"就交付。P0 验收必须跑通端到端业务场景，不能按模块孤立验收。
2. **对象 taxonomy 先于分期**：先统一资源/对象模型和别名（商管"铺位"≠只有商铺；CRM"客户"≠只有一种客户），再做差异分析。
3. **移动端/报表/流程前移到 P1**：交付可用性（移动协同）和客户验收能力（报表/流程配置）不是 P2 锦上添花。
4. **企划/营销/高级分析后移到 P3**：非主闭环能力不进 P0/P1，即使代码已有基础。
5. **财务 P0 必须包含变更/终止/清算/保证金/预存款/发票**：只做到"出账收款"不是闭环，要能退出。

**验收链路模板**（P0 必须输出）：
```
对象建档 → 核心业务流程入口 → 关键单据流转 → 财务/结算闭环 → 退出/释放 → 可重新进入
```

**交接文档结构**（PRD 侧输出，业务系统侧执行）：
1. PRD 目标蓝图摘要
2. 当前代码能力概览（按能力域对照）
3. P0/P1/P2/P3 分期与每项必须包含的内容
4. P0 端到端验收主链路
5. 建议的 OpenSpec change 拆分（P0 拆 5-7 个，P1 拆 4-6 个方向）
6. 人工待确认问题清单

**边界**：PRD 侧只输出交接文档，不直接修改业务系统代码。业务系统基于交接文档自行拆任务、做迁移、接口、前端和测试。

### PRD→代码术语映射是验收前提

PRD 是中文业务单据与流程，代码 OpenSpec/能力名是英文工程 ID。两者之间必须有显式映射，否则：
- 验收时无法判断"代码已有的 capability 是否对应 PRD 的业务单据"。
- 差异分析会变成主观猜测。

**做法**：交接文档的"能力域对照"表必须同时列出 PRD 业务名和代码 OpenSpec 能力 ID，并标注状态（existing/partial/missing/defer）。

**案例**：商管 PRD 中"预存款"对应代码 `surplus` / `advance charge`，但语义不完全一致，需要独立预存款账户模型。不做映射就会误判为"已有"。

## 维护规则

修改本 skill 时，如发现新的非显而易见行为或踩到新坑：

1. **判断归属**：通用方法论 → 留在本文件；域专属知识 → 写入项目目录下 `域知识.md`（如 `$LANLNK_BASE/out/prd/商管系统/域知识.md`）
2. **更新本文件**的「已知限制」和「设计决策（通用方法论）」章节
3. **如是诊断流程**，更新 `references/troubleshooting.md`
4. **修改 term-aliases.yaml 时**，同时检查 `material-importer/references/domain-tags.md` 是否需要同步
5. **修改 business-ontology.yaml 时**，它是共享文件（`$LANLNK_BASE/config/ontology/`），其他 skill 也依赖
6. **新增实体时**，必须同时更新 field-specs 和 ontology 的 `sub_functions`。每次大批量修改后做全局同步检查
7. **新增域知识文件时**（如会员系统），在项目目录下创建 `域知识.md`，并在本文件「适用场景」下添加引用

**判断标准**：如果一个行为或坑"下次的我"读到代码不一定能立刻理解为什么这么做，就应该记录。
