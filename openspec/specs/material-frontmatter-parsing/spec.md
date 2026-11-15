# material-frontmatter-parsing Specification

## Purpose
定义素材 markdown 文件 YAML frontmatter 的解析契约：`---` 分隔符仅在独立成行时作为边界，值内出现的 `---` 不影响解析；解析失败时的错误类别保持稳定，供素材校验闸门与下游消费方依赖。

## Requirements

### Requirement: 独立成行分隔符识别
素材 frontmatter 解析 SHALL 仅将「独立成行的 `---`」识别为 frontmatter 边界 delimiter：开 delimiter 为**文件字节起点处的首行**（即文件第一行就是 `---` 行，其前不得有任何前置空白行或 BOM）；闭 delimiter 为其后第一个独立成行的 `---` 行。YAML 值内部的 `---`（非独立成行）MUST NOT 被当作边界。

#### Scenario: 未加引号标量值内含三连字符
- **WHEN** 素材文件 frontmatter 某个 YAML 未加引号标量值（如 `source: 成本---成本管理典型问题库.xlsx`）包含 `---` 子串
- **THEN** 解析成功返回完整键值对，该值保持原文（现状为静默截断为 `成本` 且不报错，本变更修复为保全原文），不产生任何解析错误

#### Scenario: 加引号标量值内含三连字符
- **WHEN** 素材文件 frontmatter 某个 YAML 加引号标量值（如 `source: "成本---成本管理典型问题库.xlsx"`）包含 `---` 子串
- **THEN** 解析成功返回完整键值对，该值保持原文（现状为「YAML 解析错误: while scanning a quoted scalar」，本变更修复为解析成功）

#### Scenario: 闭 delimiter 行允许行尾空白与 CRLF
- **WHEN** 闭 delimiter 行为 `---` 后跟行尾空白或以 CRLF 结尾
- **THEN** 该行仍被识别为闭 delimiter，解析成功

### Requirement: 错误类别保持
frontmatter 解析失败时 SHALL 沿用现有错误类别：缺少 YAML frontmatter（文件不以 `---` 行开头）、frontmatter 未闭合（无闭 delimiter）、YAML 解析错误（闭块内容非合法 YAML）、frontmatter 不是合法的键值对（解析结果非 mapping）。除两类既定例外（delimiter 识别收紧、值内 `---` 修复）外，MUST NOT 改变对合法与非法文件的判定结果；例外详情见下方场景。

#### Scenario: 值内含三连字符的标量修复（既定例外 1）
- **WHEN** frontmatter 标量值内含 `---`：未加引号标量、加引号标量
- **THEN** 均解析成功且值保全原文（未加引号由「静默截断无报错」修正、加引号由「YAML 解析错误」修正，均为有意的行为修正）

#### Scenario: 四横线开头文件的归类调整（既定例外 2）
- **WHEN** 文件以 `----`（4 横线及以上）行开头
- **THEN** 归类为「缺少 YAML frontmatter」（现状为「YAML 解析错误」；两种口径下该文件均非法，仅错误类别归并到更准确的一类）

#### Scenario: 缺少开分隔符
- **WHEN** 文件首行不是独立的 `---` 行（含前置空白行、BOM、`----` 等更长横线行开头的情况）
- **THEN** 返回错误类别「缺少 YAML frontmatter」，不尝试解析正文（`----` 情形为既定例外 2 的归类调整）

#### Scenario: frontmatter 块未闭合
- **WHEN** 文件以 `---` 行开头但其后不存在独立成行的闭 delimiter
- **THEN** 返回错误类别「frontmatter 未闭合」

#### Scenario: 非法 YAML 与非 mapping
- **WHEN** 闭块内内容 YAML 语法非法，或合法 YAML 但顶层不是 mapping
- **THEN** 分别返回「YAML 解析错误」与「frontmatter 不是合法的键值对」

#### Scenario: CRLF 文件
- **WHEN** 素材文件整体使用 CRLF 换行且 frontmatter 结构正确
- **THEN** 解析行为与 LF 文件一致（现状基线已实测确认：2026-11-15 临时 fixture 实跑 CRLF frontmatter 解析成功，新实现须保持该现状）
