# doc-generator Troubleshooting

本文件记录 doc-generator 的**非显然行为**与**踩坑修复**——读代码不会立刻理解"为什么这么做"的那些。
与 `limitations.md`（v1 已知限制 + v2 路线图）配合阅读：本文件是**怎么从问题里爬出来**，limitations.md 是**这些问题为什么暂时不修**。

> 复杂度分级：本 skill 属 AGENTS.md tier 表的 **Complex**（多模块包），troubleshooting.md 必填。

---

## 1. P1-P3 是 agent 驱动的，P4 才是代码

**症状**：试图把 P1（应用结构发现）、P2（截图规划）、P3（截图执行）写成代码自动跑——失败。

**根因**：本 skill 的"智能"全部在 P1-P3，由 agent 读 SKILL.md 现场决策（哪些路由要进、locator 用什么文本、登录如何处理）。`scripts/render_manual.py`（P4 渲染）**是纯函数**——无浏览器、无网络、无 LLM 调用。

**正确分工**：
| 阶段 | 由谁执行 | 是否代码 |
|---|---|---|
| P0 环境检测 | agent + 少量探测代码 | 半自动 |
| P1 应用结构发现 | agent（用 playwright skill 探测） | 非代码 |
| P2 截图规划 | agent 写 `screenshot-plan.json` | 非代码 |
| P2.5 登录凭据 | agent + `.auth.json` | 半自动 |
| P3 截图执行 | agent 调 playwright skill 逐 action 跑 | 非代码 |
| **P4 渲染** | **`render_manual.py`**（纯函数） | **代码** |

**契约**：P4 的输入 schema 见 `references/analysis-schema.md` + `references/screenshot-plan-schema.md` + `references/style-fingerprint.md`。schema 是行为契约，schema 合规的输入 → 一定出合规输出。

详见 AGENTS.md §「Doc-Generator: Runtime-First SPA Manual Generator」。

---

## 2. Playwright skill 在 P0 才加载，不在 skill 启动时

**症状**：在 SKILL.md 入口处就 `skill(name="playwright")`——失败或拖慢启动。

**根因**：playwright 是 MCP skill，加载有开销。doc-generator 在 **P0 第 6 步** 才尝试加载（轻量加载，不执行浏览器操作），且：
- 加载失败时 **不终止**，标记 `degraded_mode: "playwright_unavailable"`
- 后续 P2.5 / P3 全部跳过
- P4 走占位符（图位显示 "playwright 不可用"）

**正确顺序**（SKILL.md §P0 Procedure 第 6 步）：
```python
# P0 step 6
try:
    skill(name="playwright")  # 轻量加载
except SkillLoadError:
    degraded_mode = "playwright_unavailable"
    # 继续不终止
```

P1 第 1 步才真正"保持上下文"加载 playwright 用于探测。

---

## 3. 优雅降级（graceful degradation）的边界

**症状**：playwright 不可用 / dev server down / 单页 timeout 时，不知道流程该怎么走。

**根因**：本 skill 设计原则之一就是"P4 始终产出"——任何 P1-P3 失败都不阻塞渲染，用占位符兜底。

**降级矩阵**：

| 失败 | 阻塞 P4? | 处理 |
|---|---|---|
| `$USERGUIDE_BASE` 不可写 | **是** | 终止（无法输出） |
| 源码无 `package.json` | 否 | framework_hint=unknown，软件名走 2/3/4 级 |
| Dev server 探测失败 | **是** | 终止（无 dev server 整个 skill 没意义） |
| Playwright skill 加载失败 | 否 | degraded_mode，跳过 P2.5/P3，P4 占位符 |
| 单路由导航 timeout | 否 | 标记 `accessible: false`，其它路由继续 |
| 单张截图 timeout | 否 | manifest 标 `failed`，P4 用占位图 |
| `config.yaml` YAML 语法错 | **是** | 终止（语法错说明用户写错了） |
| `config.yaml` 未知字段 | 否 | warning 继续 |

详见 SKILL.md 各阶段的「Failure Modes」表。

---

## 4. iframe 微前端不被发现也不截图

**症状**：手册只出现壳应用菜单，qiankun/wujie/micro-app 等子应用页面缺失。

**根因**：P1 运行时探测只看外层壳路由；P3 默认不切 iframe 上下文。跨 iframe 的路由发现、locator 解析、上下文切换是独立工程，MVP 不做。

**临时方案**：对微前端子应用**单独运行** doc-generator（当成独立 SPA），生成独立手册。

详见 `limitations.md` §1。

---

## 5. WebSocket / 实时 UI 截图可能不完整

**症状**：截图捕获到 loading 转圈、部分加载的中间态。

**根因**：Playwright `waitFor` 基于明确条件，无法判断 WebSocket 推送的"完成"。

**临时方案**（按代价排序）：
1. `screenshot-plan.json` 里手动调大 `wait.timeout_ms`
2. `config.yaml` 用 `ignore_modules` 排除 WebSocket 重度模块
3. 应用侧主动暴露 `data-ready` 属性或 `window.__DOCGEN_READY__` 全局变量（v2 协议，目前需用户接入）

详见 `limitations.md` §7 + §v2-7。

---

## 6. `.auth.json` 必须 gitignore

**症状**：`.auth.json` 含明文密码，被提交到 git——**严重安全风险**。

**根因**：P2.5 首次运行时询问凭据后写入 `$USERGUIDE_BASE/_input/{name}/.auth.json`（mode 0600），二次运行复用。

**正确配置**：

如果 `$USERGUIDE_BASE` 在某个仓库内（不推荐——推荐放仓库外），在该仓库根 `.gitignore` 加：
```gitignore
$USERGUIDE_BASE/_input/**/.auth.json
```

或更稳妥的写法（避免 `$` 在 gitignore 中的歧义）：
```gitignore
_input/**/.auth.json
```

**CI 场景**：用 `--auth-user` + `--auth-pass` 直接传，不写文件。

详见 SKILL.md §「凭据安全」。

---

## 7. 软件名发现的 4 级优先级

**症状**：软件名不对，导致输出目录错乱、复用旧 analysis.json 失败。

**根因**：P0 第 3 步有 4 级优先级，找到即停：
1. 源码根 `package.json:name`（剥 `@scope/` 前缀）
2. 源码目录名（但 `src` / `app` / `code` / `project` 等通用名跳过本级）
3. 用户调用文本中的显式名称（"为 mysqlbot 生成手册" → `mysqlbot`）
4. 交互式询问

**规范化**：全部转 kebab-case（小写、非字母数字替换为 `-`、去首尾 `-`）。

**踩坑**：`@scope/mysql-bot` 应得 `mysql-bot`，不是 `scope-mysql-bot`。

---

## 8. 增量 vs 全量模式的判断

**症状**：跑了一次后第二次重新截图所有页面，浪费时间。

**根因**：P0 第 9 步根据 `$USERGUIDE_BASE/{name}/analysis.json` 是否存在判断：
- 存在 + 未传 `--full`：询问"全量 / 增量"
- 传 `--full`：跳过询问强制全量
- 不存在：直接全量

**增量模式行为**：P1 产出 `analysis.json.diff`（added / removed / changed / unchanged），P2-P3 只重做 added + changed。

**强制全量的场景**：
- 升级 doc-generator 版本后 schema 变了
- 之前 P3 失败导致 manifest 缺图
- 应用大改后路由全变

---

## 9. 参考资料格式支持矩阵

**症状**：往 `_input/{name}/references/` 丢了个 `.numbers` 文件，被跳过。

**根因**：参考资料支持格式是有限集合：

| 格式 | 处理方式 |
|---|---|
| `.md` / `.txt` / `.html` | 直读 |
| `.docx` / `.pptx` | markitdown |
| `.pdf` | pypdf |
| URL（`urls.txt`） | webfetch |
| 其他 | **跳过 + warning** |

** unsupported 文件类型**（已知会被跳过）：`.numbers`、`.key`、`.pages`、`.xlsx`（除非用 markitdown 转）、视频/音频。

---

## 10. 跨 skill 路径依赖

- 调 `playwright` skill（builtin）—— P0 第 6 步轻量加载，P1 第 1 步保持上下文加载
- 不调 word-master / ppt-master——本 skill 输出是 Markdown + JSONL，不需要 Office 排版
- 输出可被 LangChain ingestion 直接消费（chunks.jsonl 格式见 `references/chunks-jsonl-schema.md`）

---

## 与其它文档的关系

| 文件 | 作用 | 何时读 |
|---|---|---|
| 本文件 | 踩坑 + 非显然行为 | 第一次跑、出错时、改 SKILL.md 时 |
| `limitations.md` | v1 已知限制 + v2 路线图 | 决定要不要等 v2、规划 workaround 时 |
| `analysis-schema.md` | P1 输出 schema | 写 P1 探测代码、改 analysis.json 结构时 |
| `screenshot-plan-schema.md` | P2 输出 schema | 写 P2 规划、改 screenshot-plan 结构时 |
| `style-fingerprint.md` | 风格参考 schema | 传入参考手册影响输出风格时 |
| `chunks-jsonl-schema.md` | RAG 输出 schema | 下游 RAG 集成时 |
| `llms-txt-format.md` | llms.txt 规范 | llmstxt.org 集成时 |
| `config-yaml-schema.md` | per-app 配置 | 写 `_input/{name}/config.yaml` 时 |
| `manual-template.md` | P4 内置 Jinja2 模板 | 改输出格式时（v2 才支持 per-app 覆盖） |
