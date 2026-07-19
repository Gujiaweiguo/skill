# SKILL.md Frontmatter 规范

本文件定义 `/opt/code/skill/skills/<category>/<name>/SKILL.md` 的 YAML frontmatter 规范。
所有新增 / 修改 SKILL.md 必须遵守，由 `references/scripts/check_skill_ecosystem.sh` 自动验证。

## 必填字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | skill 名（kebab-case），必须与目录名一致，必须与 `.opencode/skills/<name>` 软链名一致 |
| `description` | string（≥ 200 字符推荐） | skill 触发描述，**必须用 `|-` literal block 风格**（见下文），OpenCode 用这段文本做触发词匹配 |

## 强烈建议字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `compatibility` | string | 运行时依赖、外部环境变量、Python/Node 版本要求。**必须用 `|-` literal block**，不要写单行（容易触发 `:` 解析错误，见下文陷阱） |

## 可选字段

| 字段 | 类型 | 适用场景 |
|---|---|---|
| `emoji` | string | 在 list 展示时显示图标（如 winshang-crawler 用 `🏗️`） |
| `requires.bins` | list of strings | 声明依赖的系统二进制（如 `[python3, uv]`） |
| `requires.env` | list of strings | 声明依赖的环境变量（如 `[WINSHANG_USERNAME]`） |
| `metadata` | dict | skill 元数据（如 OpenClaw 集成信息） |

## description 字段的强制风格：`|-` literal block

**所有 SKILL.md 的 description 必须用 `|-` literal block，不要用 inline 单行**。

**正确**：
```yaml
---
name: my-skill
description: |-
  简短一句话总结这个 skill 做什么。
  支持的子模式：
  - 模式 A：用于 X 场景
  - 模式 B：用于 Y 场景
  触发场景："关键词 1"、"关键词 2"、"关键词 3"。
  仅面向 X 决策，不负责 Y（那些交给 sibling-skill-name）。
---
```

**错误（不推荐）**：
```yaml
description: 简短描述。  # ← 太短，触发词覆盖不足，且后续难以扩展
```

### 为什么强制 `|-`

1. **触发词覆盖**：OpenCode 的 skill 路由靠 description 文本做语义匹配。多段描述（含"触发场景"段落）显著提升自动触发命中率。peer skill description 长度中位数约 400 字符，单行描述通常 < 200 字符 → 命中率显著下降。
2. **可扩展性**：后续添加新模式 / 新触发词时，加几行就行；单行描述需要重写整行。
3. **YAML 安全**：`|-` block 内任意字符（含 `:`、`#`、引号）都安全；inline 字符串遇 `:` 会被误解析为新 key。

## description 内容结构（推荐）

按下列顺序写，peer skill 都是这个结构（参考 bid-doc-master / company-intro-generator / product-prd-generator）：

1. **一句话总结**：什么 skill + 做什么 + 基于什么方案
2. **支持的模式**（如有多个）：列出每个模式的应用场景
3. **触发场景**：用户口语表达，5-10 个高频说法（带引号）
4. **边界声明**（可选）："仅面向 X，不负责 Y（那些交给 sibling-skill）"

## YAML 陷阱（务必避免）

### 陷阱 1：inline value 含 `:`（冒号+空格）

YAML 把 `key: value` 中的 `: ` 视为 key-value 分隔符。inline value 含 `: ` 会被误解析为嵌套 mapping。

**错误**：
```yaml
compatibility: Default docs root: /opt/code/docs. Default Baidu Sync target: /mnt/d/BaiduSyncdisk/docs.
```
↑ YAML 解析报 `mapping values are not allowed here`，因为第二个 `:` 触发嵌套 mapping。

**修复**：改用 `|-` literal block。

### 陷阱 2：`|-` block 内的段落忘记缩进

`|-` block 在第一个**未缩进**的非空行结束。如果描述末尾的段落忘记缩进，会被 YAML 当成新的 top-level key 处理。

**错误**：
```yaml
description: |-
  第一段。
  第二段。
第三段没缩进。       # ← |- block 在此结束；"第三段没缩进。" 被当成新 key（无 `:` 报错）
```

**修复**：所有段落、列表项、空行都要保持 `|-` block 起始的缩进（通常是 2 空格）。

### 陷阱 3：单数 vs 复数 references 目录

历史遗留：`word-master` 用 `reference/`（单数），其它所有 skill 用 `references/`（复数）。

**新 skill 必须用 `references/`（复数）**。`word-master` 的 `reference/` 是历史包袱，不要重命名（会破坏 5 个下游 skill 的路径引用），但也不要在新 skill 复制这个错误。

## 校验

每次改 SKILL.md 后，跑：

```bash
/opt/code/skill/references/scripts/check_skill_ecosystem.sh
```

脚本会自动检测：
- frontmatter 是否能被 yaml parser 解析（P1-6）
- description 长度是否 ≥ 200 字符（P2 warn）
- 复杂 skill 是否有 `references/troubleshooting.md`（P1-1）
- 复杂 skill SKILL.md 是否有 `## References` 索引（P1-5 warn）

CI / Git pre-push hook 用 `--ci` flag 获得非零退出码做门禁。
