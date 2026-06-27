---
name: product-prd-generator
description: 面向已有商管系统的 PRD 生成 Skill。以 /opt/code/mi 作为当前产品基线，结合客户需求、竞品资料、手册、蓝图、截图和图片证据，生成统一功能清单、差距分析和内部产品 PRD。
compatibility: Requires Python 3.10+ and uv. Reuses material-importer for doc-to-md conversion and image extraction. Reads code from /opt/code/mi.
---

# Product PRD Generator

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

- 商管系统产品规划
- 多客户需求汇总
- 多竞品资料归纳
- 基于现有产品进行版本规划
- 需要保留界面截图、流程图、表单图等视觉参考

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

- `$LANLNK_BASE/prd/projects/商管系统/input/00-current-product/`
- `$LANLNK_BASE/prd/projects/商管系统/input/01-customer-requirements/`
- `$LANLNK_BASE/prd/projects/商管系统/input/02-competitors/`

### 3. 转换后的中间资料

- `$LANLNK_BASE/prd/projects/商管系统/raw/`

## 目录规范

```text
/opt/code/docs/lanlnk/prd/projects/商管系统/
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

**补充要求**：
- 海鼎这类资料如果同时包含“数据逻辑 / 表结构 / 账款模型 / 字段说明”，必须单独标记为“数据结构”，不要压成普通功能标题。
- “用户组 / 岗位 / 角色 / 授权组 / 数据权限 / 模块权限 / 流程审批链 / 委派 / 候选人”必须优先识别为权限或流程类需求。
- 账款、合同、组织、用户、流程等材料里出现的表格标题，不要默认当成普通需求名；需要保留它们的层级和上下文。
- 合同条款类结构只在**精确章节标题**命中时才标记为“合同条款组”，例如“结算周期”“账款条款”“进场条款”“免租条款”“预存款条款”“自定义条款”“合同模板”“合同保存草稿”。
- 仅因正文里出现“合同”二字，不要把普通功能误判为条款组；像“合同模板管理”“合同编号”“结算周期名称”这类派生标题应保持原始类型，避免噪音扩散。
- 合同资料合并时，**海鼎优先**：海鼎作为结构模板来源，其他合同来源只补充术语、差异和证据；同名条款冲突时优先保留海鼎的章节骨架和字段命名。
- 华侨城、锦和虽然可能出现在客户需求目录里，但其合同/蓝图资料同样属于海鼎体系的变体，合并时应按"海鼎家族"看待，不要当成独立模板家族。
- 家族变体标题通过 `_FAMILY_CLAUSE_ALIASES` 归一到海鼎标准条款名（如"正式合同"→"新合同申请"、"固定租金计算方式"→"账款条款"），使三家来源在合并时自然对齐。

### Step 4: 术语归一
把不同材料里的说法统一映射到标准功能名。

例如：

- 租户服务平台 / 商户服务 / 客户服务 / 租户门户 → 租户服务
- 资产台账 / 资产建档 / 资产登记 → 资产管理相关能力
- 合同签约 / 合同生效 / 合同清算 → 合同管理相关能力

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
└── 需求证据表.md
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

```bash
cd skills/business/product-prd-generator
uv sync
uv run product-prd-generator --project 商管系统 \
  --code-root /opt/code/mi \
  --docs-root $LANLNK_BASE/prd/projects/商管系统/raw \
  --skill-root /opt/code/skill/skills/business/product-prd-generator \
  --parsed-dir parsed \
  --output-dir output
```

## 交付原则

这个 Skill 的核心不是"写 PRD"，而是：

- 抽能力
- 统一术语
- 对齐代码
- 找 gap
- 再生成 PRD

## 已知限制

- **PDF 转换需要 poppler-utils**：`apt install poppler-utils`。无 sudo 权限时，PDF 无法用 markitdown 转换，需要 LibreOffice 预转换或手动转 md。当前项目有 6 个竞品 PDF 受此影响（政策文件，影响小）。
- **匹配率 ~19%**：瓶颈是**术语覆盖率**（ontology 572+ 术语），不是匹配策略。两阶段匹配提升精确度但不提升召回率。继续扩 ontology 术语是唯一提升路径。
- **business-ontology.yaml 运行时依赖**：doc_map 从 `$LANLNK_BASE/knowledge/business-ontology.yaml` 加载。文件缺失时退化为纯 term-aliases 匹配（匹配率回到 ~12%）。
- **YAML OrderedDict 序列化陷阱**：在 ontology/specs 中使用 `OrderedDict` 后 `yaml.dump` 会写入 Python 特有的 tag（`!!python/object/apply:collections.OrderedDict`），导致 `yaml.safe_load` 报 ConstructorError。**必须用普通 dict**。详见 troubleshooting.md。
- **field-specs YAML 完整性**：`module-field-specs.yaml` 在多次编辑后可能丢失实体（如 OrderedDict 序列化失败导致 yaml.safe_load 无法读取→数据丢失）。每次大改后应验证实体数量：`len(mfs['招商管理'])` 等。
- **噪音过滤可能误判**：`_is_noise_text` 过滤编号、元数据、表格残留、图片路径、JSON 块、句子型文本。极端情况下可能误杀合法标题。
- **word-master .venv 依赖**：word_export 调用 word-master 时依赖其目录下的 `.venv`。如果 word-master 目录未 `uv sync`，会报 `ModuleNotFoundError: docx`。
- **OCR 数据结构去重陷阱**：OCR 提取的表名标题（如 `数据结构 m3newcontractrequest（新合同申请）`）经过 `_normalize_term()` 后全部归一到同一业务术语（如 `lease-contract-management`）。`_parse_requirements()` 用 `normalized` 做 dict key 去重，导致 117/214 张表被吞。已修复：以 `数据结构` 开头的标题用 heading 原文做 key。新增 OCR 数据源时注意这个模式。
- **OCR all-ocr.md 噪音**：`ocr_extract.py` 生成的人类可读汇总 `all-ocr.md` 会被 `_iter_markdown_files()` 当作需求源解析，产生图片文件名噪音。PRD 生成前必须删除 `_extracted/all-ocr.md`，只保留 `haiding-data-model.md`。

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

### 海鼎多表/权限流程材料

海鼎资料里经常把“数据逻辑 / 表结构 / 账款模型 / 字段说明 / 流程定义 / 用户组 / 岗位 / 权限”拆成不同文档块。抽取时要：

1. 保留它们的结构类型，而不是都当成 feature。
2. 数据结构、流程、权限优先进入需求清单和 review 清单。
3. 涉及多个表或流程节点时，PRD 里要允许“主表 / 明细 / 关联 / 流程节点 / 权限对象”并存。

### 实体命名三原则

PRD 中的实体/单据名称必须满足：

1. **短**（≤4-5字）：`条件报批` 优于 `租赁条件报批`
2. **可搜**：在模块上下文中是高辨识词。`条件报批` 搜一次命中；`租赁报批` 和 `租赁政策`/`租赁期限`/`租赁合同` 混在一起难区分
3. **不撞**：不与同模块其他实体共用前缀。`招商` 模块里避免多个 `租赁xxx`

**实际案例**：`租赁条件 → 租赁报批 → 条件报批`，迭代 3 次才找到最优名称。

### 台账/预警/报表：不创建实体

以下三类内容**不应作为业务模块的 sub_function**：

- **台账** = 报表视图，不是数据实体。合同台账就是合同列表+状态筛选，不需要单独定义
- **预警** = 跨模块通用功能（合同到期/资源空置/证照到期/零销售/坪效/租售比），放在**系统管理/预警配置**
- **自定义报表** = 系统功能，放在**系统管理/自定义报表**

**参考**：中旅需求清单将预警配置/自定义报表/模板配置/工作流程配置统一放在「系统管理」下。

### 业务单据流：上游导入支持

业务流程中的单据不是孤岛——每个单据应支持从前序单据导入数据：

```
招商洽谈 → 报价单 → 意向合同 → 条件报批 → 合同生成 → 应收生成
```

**实现模式**：合同生成单据有 `合同来源` 字段（直接新建/从意向合同转入/从条件报批转入），选择后联动 `来源单号`。被导入的字段标注"自动带出（来源单号→xxx）"，且可修改覆盖。

### 招商计划：节点里程碑模型

招商计划不是扁平的任务分派，而是**每个铺位按节点跟踪里程碑**：

- 9 个标准节点：待招商→目标客户接洽→洽谈中→方案评审→意向签订→合同评审→合同签订→交铺装修→开业
- 每个节点有：节点名称/类型(手工|自动)/计划完成日/实际完成日/状态/关联单据
- **手工节点**：用户录入完成时间+附件（如技术对接）
- **自动节点**：系统随业务单据联动（意向书审核→意向签订完成，合同生效→合同签订完成）
- **预警**：即将逾期/已逾期/长期无进度

**来源**：万达技术标准 §6 铺位级招商计划管理。

### 模块结构遵循客户心智模型

当客户需求文档已有清晰的模块归类时，**遵循客户的结构**，不要自创分类：

- 中旅将预警配置放在系统管理 → 我们也放系统管理，不放在合同管理
- 海鼎将企划(推广)独立成模块 → 我们也独立，不合并到运营管理
- 华侨城将物料管理(14个子项)放在物业管理 → 我们也放物业，不放运营

**原则**：source documents 的结构 IS the requirements。

### OCR 图片型资料 → PRD 数据模型（Pipeline）

图片型 PPT/Word 资料（如海鼎业务逻辑介绍）的表结构信息无法通过 markitdown 提取。完整 pipeline：

```
ocr_extract.py (DeepSeek-OCR-2)
  → slides.jsonl + tables.jsonl (OCR 原始结果 + SQL 校准表名)
ocr_to_features.py
  → haiding-data-model.md (bold-heading 格式，每张表一条)
_parse_markdown()
  → requirements (function="数据结构 m3contract（合同表）")
_render_data_model()
  → PRD section 3A (按域分层的表结构概览)
```

**bold-heading 格式约束**：`_BOLD_HEADING` 正则 `^\*\*(.+?)\*\*\s*$` 要求 bold 文本独占一行。字段信息必须放在下一行，不能同行。否则正则不匹配，OCR 数据全部丢失。

**域分组**：`_render_data_model()` 按表名前缀分组（m3contract→主数据，m3newcontract→申请单，m3rdbc→条款/公式）。新增厂商时在 `_DOMAIN_MAP` 里加前缀映射。

## 维护规则

修改本 skill 时，如发现新的非显而易见行为或踩到新坑：

1. **更新本文件**的「已知限制」和「设计决策」章节
2. **如是诊断流程**，更新 `references/troubleshooting.md`
3. **修改 term-aliases.yaml 时**，同时检查 `material-importer/references/domain-tags.md` 是否需要同步（如涉及共享术语）
4. **修改 business-ontology.yaml 时**，它是共享文件（`$LANLNK_BASE/knowledge/`），其他 skill 也依赖

**判断标准**：如果一个行为或坑"下次的我"读到代码不一定能立刻理解为什么这么做，就应该记录。
