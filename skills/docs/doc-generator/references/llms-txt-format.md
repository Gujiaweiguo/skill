# llms.txt Format Specification (Subset)

This document defines the data contract for `llms.txt`, one of the three outputs of P4 (Manual Rendering). It follows the stable subset of the [llmstxt.org](https://llmstxt.org) community specification: H1 project name, optional blockquote summary, H2 sections each followed by markdown links. The goal is to give LLM-powered tools (chat assistants, IDE integrations, doc aggregators) a compact overview of the manual plus deep links back to the full Markdown.

We use the stable subset only. Advanced llmstxt.org features (named links, optional sections marker, etc.) are intentionally excluded from MVP to keep the renderer trivial and the output predictable.

## 文件结构

| 行号 | 内容 | 必填 |
|------|------|------|
| Line 1 | `# {app_name} 操作手册`: 文件唯一的 H1 | MUST |
| Line 2 | 空行 | MUST |
| Line 3 | `> {one-sentence summary}`: blockquote 形式的一句话摘要 | OPTIONAL（推荐） |
| Line 4+ | 空行，然后 H2 章节块 | MUST |

### H2 章节块

每个 H2 章节块结构：

```
## {section_title}

{optional one-paragraph content}

- [link text](操作手册.md#{anchor})
- ...
```

| 元素 | 必填 | 说明 |
|------|------|------|
| `## {section_title}` | MUST | 中文标题，MUST 与 `操作手册.md` 中的对应章节匹配（去掉"一、""二、"等序号前缀）。 |
| 章节简介段落 | OPTIONAL | 一段中文描述本章节涵盖的内容。MUST NOT 超过 2-3 句。 |
| markdown 链接列表 | MUST | 至少 1 个 `[text](操作手册.md#anchor)` 链接。 |

### Anchor 锚点生成规则

链接锚点遵循 GitHub-flavored Markdown 规则，并保留中文字符：

| 规则 | 示例 |
|------|------|
| 全部转小写 | `用户管理` → `用户管理`（中文无大小写变化）|
| 空格替换为连字符 `-` | `实验性 功能` → `实验性-功能` |
| 标点（含中文标点）去除 | `常见问题（FAQ）` → `常见问题faq` |
| 字母数字（含汉字）保留 | `模块3：用户管理` → `模块3用户管理` |
| 连续连字符合并为单个 | `a -- b` → `a-b` |
| 前导/尾随连字符去除 | `-用户-` → `用户` |

**重要**：中文字符 MUST 保留，不进行拼音化或翻译。GitHub 在 anchor 中保留 CJK 字符，主流工具（VSCode preview、Chrome、Obsidian、LangChain MarkdownHeaderTextSplitter）均支持。

### 标题序号前缀处理

`操作手册.md` 的章节带序号前缀（如 `## 二、功能模块详解`、`### 模块三：用户管理`），但 `llms.txt` 的 H2 与 anchor 不含序号前缀。映射规则：

| 操作手册.md 原标题 | llms.txt H2 | anchor |
|--------------------|-------------|--------|
| `## 一、快速开始` | `## 快速开始` | `#快速开始` |
| `## 二、功能模块详解` | `## 主要功能模块` | （此章节本身在 llms.txt 列出子模块作为链接列表）|
| `### 模块三：用户管理` | （在"主要功能模块"章节内列出）| `#模块三用户管理` |
| `## 三、常见问题（FAQ）` | `## 常见问题` | `#常见问题faq` |
| `## 四、附录` | `## 附录` | `#附录` |

## 章节清单（doc-generator 强制结构）

`llms.txt` MUST 包含以下 4 个 H2 章节，按顺序排列：

### 1. `## 快速开始`

简短摘要 + 一个链接到 `操作手册.md#快速开始`。

```
## 快速开始

本手册介绍 {{ app_name }} 的核心功能与日常操作。

- [开始阅读](操作手册.md#快速开始)
```

### 2. `## 主要功能模块`

列出所有模块（每个 route 一个）。每个模块一个链接，链接文本是模块标题，锚点是 GitHub anchor 规则生成的（如 `模块三用户管理`）。

```
## 主要功能模块

{{ app_name }} 共包含以下功能模块：

- [用户管理](操作手册.md#模块1用户管理)
- [仪表盘](操作手册.md#模块2仪表盘)
- [订单管理](操作手册.md#模块3订单管理)
```

模块序号与 `操作手册.md` 中的 `### 模块N：` 序号严格对应（基于 `analysis.routes` 的顺序）。

### 3. `## 常见问题`

```
## 常见问题

整理高频问题与排查思路。

- [查看 FAQ](操作手册.md#常见问题faq)
```

当 `style-fingerprint.faq_style === "none"` 时，此章节 MUST 不输出（renderer 控制）。

### 4. `## 附录`

```
## 附录

快捷键说明、环境要求等补充信息。

- [查看附录](操作手册.md#附录)
```

## 完整示例

下列示例展示一个含 3 个模块的应用的 `llms.txt`。注意中文 anchor 的保留方式。

```text
# admin-portal 操作手册

> admin-portal 是面向运营团队的用户、权限与订单管理 Web 系统，本手册覆盖 v1.4.2 的全部功能模块。

## 快速开始

本手册介绍 admin-portal 的核心功能与日常操作。

- [开始阅读](操作手册.md#快速开始)

## 主要功能模块

admin-portal 共包含以下功能模块：

- [用户管理](操作手册.md#模块1用户管理)
- [仪表盘](操作手册.md#模块2仪表盘)
- [订单管理](操作手册.md#模块3订单管理)

## 常见问题

整理高频问题与排查思路。

- [查看 FAQ](操作手册.md#常见问题faq)

## 附录

快捷键说明、环境要求等补充信息。

- [查看附录](操作手册.md#附录)
```

## 校验规则

1. **唯一 H1**：文件 MUST 仅包含 1 个 `# ` 开头的行，且是第 1 行。
2. **H1 内容**：MUST 是 `{app_name} 操作手册`，与 `analysis.app_name` 一致。
3. **空行分隔**：H1 与 blockquote、blockquote 与第一个 H2、相邻 H2 章节之间 MUST 由空行分隔。
4. **blockquote 可选但位置固定**：若存在，MUST 紧跟 H1（中间仅 1 个空行）。
5. **H2 数量**：MUST 包含 4 个 H2：`快速开始` / `主要功能模块` / `常见问题` / `附录`（除非 `style-fingerprint.faq_style === "none"`，此时 FAQ 章节省略）。
6. **H2 顺序**：上述 4 章节顺序 MUST 保持。
7. **链接路径**：每个链接 MUST 指向 `操作手册.md#{anchor}`，不使用绝对路径或上层目录。
8. **anchor 合法性**：每个 anchor MUST 在 `操作手册.md` 中实际存在（renderer 用同一份 context 数据生成两者，结构上保证一致）。
9. **模块链接数量**：`## 主要功能模块` 下的链接数 MUST 等于 `analysis.routes` 长度。
10. **链接顺序**：模块链接顺序 MUST 与 `操作手册.md` 中 `### 模块N：` 顺序一致。

## 待确认

无。MVP 子集已覆盖 spec manual-rendering Requirement: LLMS-Text Format Compliance 的全部场景。高级 llmstxt.org 特性（named links、optional section marker 等）推迟。
