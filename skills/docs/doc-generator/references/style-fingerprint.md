# style-fingerprint.json Schema

This document defines the data contract for `style-fingerprint.json`, one of the three inputs to `render_manual.py`. It captures five orthogonal dimensions of how a reference manual reads and renders. The fingerprint does NOT change what the manual says (content comes from `analysis.json` + `manifest.json`); it only changes how that content is laid out (template branches, table density, FAQ inclusion).

The five dimensions are intentionally minimal. They cover the highest-leverage stylistic choices in technical manual rendering. Per-dimension `sources` provenance records whether each value came from a reference document, a config override, or the built-in default, enabling transparency and debugging.

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `chapter_depth` | int (1-3) | MUST | 章节嵌套深度上限。控制 `操作手册.md` 中 H3/H4 的使用密度。 |
| `step_density` | enum | MUST | 步骤密度：`"low"` / `"medium"` / `"high"`。控制每个模块展示多少操作步骤。 |
| `screenshot_frequency` | enum | MUST | 截图频率：`"low"` / `"medium"` / `"high"`。控制 `screenshot-plan.json` 中截图动作的插入密度。 |
| `table_preference` | enum | MUST | 表格偏好：`"none"` / `"minimal"` / `"heavy"`。控制元素表格与参数表格的输出量。 |
| `faq_style` | enum | MUST | FAQ 风格：`"none"` / `"short"` / `"detailed"`。控制 FAQ 章节是否存在及答案深度。 |
| `sources` | object | MUST | 各维度取值来源：`{chapter_depth: ..., step_density: ..., ...}`，每个值是 `"reference"` / `"config"` / `"default"` 之一。 |

## 维度详解

### 1. `chapter_depth` (int 1-3)

| 取值 | 控制行为 |
|------|---------|
| `1` | 仅用 H1/H2。所有内容平铺在章节内，不使用 H3 子模块。适合极简单应用（3 个以下模块）。 |
| `2` | H1/H2/H3。每个模块一个 H3，模块内步骤平铺。**最常见取值**。 |
| `3` | H1/H2/H3/H4。每个模块 H3 + 子章节 H4（页面入口、操作步骤、界面元素说明）。对齐 `manual-template.md` 默认结构。 |

**从参考资料提取的启发式规则**：

| 参考资料特征 | 推断取值 |
|-------------|---------|
| 参考手册中只有 H1/H2，无 H3 | `1` |
| 出现 H3，但无 H4 | `2` |
| 出现 H4 或更深嵌套 | `3` |

具体算法：扫描参考资料所有 Markdown 标题行，统计最大嵌套深度 `max_depth = max(heading_level for each heading)`，clamp 到 `[1, 3]` 区间。

**默认值（无参考资料时）**：`2`

### 2. `step_density` (enum)

| 取值 | 控制行为 |
|------|---------|
| `"low"` | 每模块仅展示 1 个主流程的 2-3 个关键步骤。次要流程降级为元素表格。 |
| `"medium"` | 每模块展示主流程的全部步骤（典型 3-7 步）。**最常见取值**。 |
| `"high"` | 每模块展示全部 flow 的全部步骤。手册更长但更完整。 |

**从参考资料提取的启发式规则**：

计算参考手册中"步骤数 / 流程数"的均值（即每个流程平均包含多少步骤）：

| 平均步骤数 | 推断取值 |
|-----------|---------|
| `< 3` | `"low"` |
| `3` - `7` | `"medium"` |
| `> 7` | `"high"` |

具体算法：用"以'步骤'或数字列表开头的段落"作为流程步骤识别标志，按章节聚合后求平均。

**默认值（无参考资料时）**：`"medium"`

### 3. `screenshot_frequency` (enum)

| 取值 | 控制行为 |
|------|---------|
| `"low"` | 仅页面加载后与关键流程结束时截图。典型每模块 2-3 张。 |
| `"medium"` | 页面加载 + 每个流程的关键节点截图。典型每模块 4-6 张。**最常见取值**。 |
| `"high"` | 每个步骤都截图，包括 hover、scroll 等中间状态。典型每模块 8+ 张。 |

**从参考资料提取的启发式规则**：

计算参考手册中"图片数 / 文本段落数"的比值（image-to-paragraph ratio）：

| 比值 | 推断取值 |
|------|---------|
| `< 0.2`（约每 5 段 1 图）| `"low"` |
| `0.2` - `0.6`（约每 2-5 段 1 图）| `"medium"` |
| `> 0.6`（几乎每段都配图）| `"high"` |

具体算法：用正则 `!\[.*\]\(.*\)` 统计图片数量；用空行分隔的文本块统计段落数；两者相除。

**默认值（无参考资料时）**：`"medium"`

### 4. `table_preference` (enum)

| 取值 | 控制行为 |
|------|---------|
| `"none"` | 不输出元素表格，仅用散文描述界面元素。 |
| `"minimal"` | 仅在元素 ≥ 3 个时输出表格。表格列数 ≤ 3 列（元素/类型/用途）。**最常见取值**。 |
| `"heavy"` | 每个模块都输出元素表格，并扩展列（元素/类型/用途/默认值/必填）。 |

**从参考资料提取的启发式规则**：

计算参考手册中"表格数 / 章节数"的比值：

| 比值 | 推断取值 |
|------|---------|
| `0`（无表格）| `"none"` |
| `< 1.0`（约每章 < 1 表）| `"minimal"` |
| `≥ 1.0`（约每章 ≥ 1 表）| `"heavy"` |

具体算法：用 Markdown 表格语法（`|---|` 分隔行）统计表格数；用 H2/H3 数量统计章节数。

**默认值（无参考资料时）**：`"minimal"`

### 5. `faq_style` (enum)

| 取值 | 控制行为 |
|------|---------|
| `"none"` | 不输出"常见问题"章节。 |
| `"short"` | 输出 FAQ 章节，每条答案 1-2 句。**最常见取值**。 |
| `"detailed"` | 输出 FAQ 章节，每条答案含排查思路、相关链接、示例。 |

**从参考资料提取的启发式规则**：

| 参考资料特征 | 推断取值 |
|-------------|---------|
| 无 FAQ 章节 | `"none"` |
| 有 FAQ 章节，每条答案 < 100 字 | `"short"` |
| 有 FAQ 章节，每条答案 ≥ 100 字 | `"detailed"` |

具体算法：检测"常见问题"、"FAQ"、"疑难解答"等关键词定位 FAQ 章节；若存在则统计平均答案字数。

**默认值（无参考资料时）**：`"short"`

## sources 字段

`sources` 记录每个维度的取值来源，是调试与透明度的关键。每个维度独立记录。

| 维度 | sources 取值 | 含义 |
|------|-------------|------|
| 任一 | `"reference"` | 从参考资料提取得到（多份参考时取置信度最高的） |
| 任一 | `"config"` | 由 `_input/{name}/config.yaml` 显式覆盖 |
| 任一 | `"default"` | 无参考资料、无 config 覆盖时的内置默认值 |

## 默认指纹（无参考资料时）

```json
{
  "chapter_depth": 2,
  "step_density": "medium",
  "screenshot_frequency": "medium",
  "table_preference": "minimal",
  "faq_style": "short",
  "sources": {
    "chapter_depth": "default",
    "step_density": "default",
    "screenshot_frequency": "default",
    "table_preference": "default",
    "faq_style": "default"
  }
}
```

## 完整示例（参考资料 + config 覆盖）

假设场景：

- 参考资料是一份深度嵌套、表格密集的友商手册，提取得到：`chapter_depth=3`、`step_density="medium"`、`screenshot_frequency="low"`、`table_preference="heavy"`、`faq_style="detailed"`。
- `config.yaml` 显式覆盖 `screenshot_density: "high"`，意图让本应用手册图片更密集。
- 其余维度未被 config 覆盖。

合并后的 `style-fingerprint.json`：

```json
{
  "chapter_depth": 3,
  "step_density": "medium",
  "screenshot_frequency": "high",
  "table_preference": "heavy",
  "faq_style": "detailed",
  "sources": {
    "chapter_depth": "reference",
    "step_density": "reference",
    "screenshot_frequency": "config",
    "table_preference": "reference",
    "faq_style": "reference"
  }
}
```

## 合并优先级

`style-fingerprint.json` 是合并产物，按以下优先级（高 → 低）生成：

1. **config 覆盖最高**：`_input/{name}/config.yaml` 显式提供的维度 MUST 覆盖其他来源，`sources.{dimension} = "config"`。
2. **参考资料次之**：多份参考资料时取众数或置信度最高的提取值，`sources.{dimension} = "reference"`。
3. **默认值兜底**：既无 config 也无参考资料时使用默认值，`sources.{dimension} = "default"`。

**config.yaml 覆盖字段映射**：当前 MVP 仅支持一个 config 字段覆盖一个指纹维度：

| config.yaml 字段 | 覆盖的指纹维度 |
|------------------|---------------|
| `screenshot_density` | `screenshot_frequency` |

其他 config 字段（`auth.hint`、`ignore_modules`、`branding.primary_color`）不覆盖指纹维度，详见 `config-yaml-schema.md`。

## 校验规则

1. **5 维度齐全**：`chapter_depth` / `step_density` / `screenshot_frequency` / `table_preference` / `faq_style` 全部存在。
2. **取值合法**：`chapter_depth` MUST 在 `[1, 3]` 区间；其余 enum 字段 MUST 取允许值之一。
3. **sources 字段齐全**：每个维度在 `sources` 中都有对应条目，取值 MUST 是 `"reference"` / `"config"` / `"default"` 之一。
4. **config 来源一致性**：`sources.{dim} === "config"` 时，对应维度值 MUST 等于 `config.yaml` 中提供的值（renderer 不强制校验，但生成时保证）。
5. **default 来源一致性**：`sources.{dim} === "default"` 时，对应维度值 MUST 等于上文"默认指纹"中的取值。

## 待确认

- 是否需要为 config.yaml 暴露更多指纹维度的覆盖字段（如 `chapter_depth_override`）？MVP 仅暴露 `screenshot_density`，对应 Q3 决策；新增覆盖字段先在本文件登记。
