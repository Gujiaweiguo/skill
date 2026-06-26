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
- **匹配率 ~17%**：瓶颈是**术语覆盖率**（ontology 482 术语），不是匹配策略。两阶段匹配提升精确度但不提升召回率。继续扩 ontology 术语是唯一提升路径。
- **business-ontology.yaml 运行时依赖**：doc_map 从 `$LANLNK_BASE/knowledge/business-ontology.yaml` 加载。文件缺失时退化为纯 term-aliases 匹配（匹配率回到 ~12%）。
- **噪音过滤可能误判**：`_is_noise_text` 过滤编号、元数据、表格残留、图片路径、JSON 块、句子型文本。极端情况下可能误杀合法标题。
- **word-master .venv 依赖**：word_export 调用 word-master 时依赖其目录下的 `.venv`。如果 word-master 目录未 `uv sync`，会报 `ModuleNotFoundError: docx`。

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

## 维护规则

修改本 skill 时，如发现新的非显而易见行为或踩到新坑：

1. **更新本文件**的「已知限制」和「设计决策」章节
2. **如是诊断流程**，更新 `references/troubleshooting.md`
3. **修改 term-aliases.yaml 时**，同时检查 `material-importer/references/domain-tags.md` 是否需要同步（如涉及共享术语）
4. **修改 business-ontology.yaml 时**，它是共享文件（`$LANLNK_BASE/knowledge/`），其他 skill 也依赖

**判断标准**：如果一个行为或坑"下次的我"读到代码不一定能立刻理解为什么这么做，就应该记录。
