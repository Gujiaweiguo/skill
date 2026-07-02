---
name: doc-generator
description: |-
  Web 应用操作手册生成器 Skill。基于 运行时探测 + 源码 hint + Playwright 协作 + 纯函数渲染 方案，
  为 Vue3/React/Next/Nuxt 等 SPA 应用自动生成图文并茂的操作手册，同时输出 LangChain RAG 友好的
  chunks.jsonl 与 llms.txt。调用内置 playwright skill 完成截图自动化，单页失败不阻塞整体流程。
  触发场景："为这个 Web 应用生成操作手册"、"生成 mysqlbot 的用户手册"、"自动截图并出操作文档"、
  "做一份 RAG 友好的应用手册"、"给这个 Vue 项目出操作手册"、"分析源码 + 截图 → 操作手册"。
  当用户提供一个运行中的 SPA 应用（含源码）并要求生成操作文档时，触发此 skill。
compatibility: >
  Requires Python 3.10+ and uv.
  Requires `$USERGUIDE_BASE` env var (default `/opt/code/docs/lanlnk/UserGuide/`).
  Requires the builtin `playwright` skill (loaded mid-execution for screenshots).
  Requires the target app's dev server to be running (e.g., `npm run dev` on port 5173/3000/8080).

  Quick start:
  ```bash
  export USERGUIDE_BASE=/opt/code/docs/lanlnk/UserGuide
  cd skills/docs/doc-generator
  uv sync
  ```

  Degrades gracefully: produces manual with screenshot placeholders when playwright unavailable
  or dev server down.
---

# Doc Generator - Web 应用操作手册生成器

为运行中的 SPA 应用（Vue3 / React / Next / Nuxt 等）自动产出图文操作手册，同步生成 LangChain RAG 友好的 `chunks.jsonl` 与 `llms.txt`。agent 负责发现、规划、协作与编排，确定性渲染交给 `scripts/render_manual.py`。

## Architecture

```text
运行中的 SPA + 源码（用户提供路径）
        ↓
P0: 环境检测（框架/dev server/playwright skill 可用性/$USERGUIDE_BASE/软件名）
        ↓
P1: 应用结构发现（运行时探测 + 源码 hint）→ analysis.json
        ↓
P2: 截图规划（locator 用 text/role/placeholder，禁用 CSS）→ screenshot-plan.json
        ↓
P2.5: 登录凭据（首次询问 → .auth.json 持久化；--no-auth 可跳过）
        ↓
P3: 截图执行（加载 skill(name="playwright")，逐 action 执行）→ imgs/ + manifest.json
        ↓
P4: 渲染（render_manual.py 纯函数）→ 操作手册.md + chunks.jsonl + llms.txt
        ↓
P5: 交互确认（TOC + 成功率 + 迭代）
```

## Core Principles

1. **运行时优先**：以 Playwright 探测应用真实状态为主，源码只作 hint 补全隐藏路由、权限受限页、modal 流程。不写 AST parser。
2. **文本/角色定位器**：所有 locator 只用 `text` / `role` / `placeholder` / `label` 策略；CSS 选择器与 XPath 禁止。跨重构稳定。
3. **优雅降级**：playwright skill 不可用、dev server down、单页 timeout 都不阻塞整体流程；P4 始终产出（缺失图位用占位符）。
4. **输入输出分离**：`$USERGUIDE_BASE/_input/{name}/` 存输入，`$USERGUIDE_BASE/{name}/` 存输出。首次运行自动建目录。
5. **双 RAG 输出**：同一份 `analysis.json + manifest.json` 驱动 Markdown 与 `chunks.jsonl`，结构对齐 `manual-template.md` 章节。
6. **纯函数渲染**：`render_manual.py` 无浏览器、无网络、无 LLM。所有智能前移到 P1-P3，schema 约束行为契约。

---

## P0: 环境检测与准备

### Goal

在执行任何 side effect 前完成环境就绪检查，建立输入输出目录骨架，确定软件名。

### Inputs

- 用户提供的源码项目路径（如 `/opt/code/mysqlbot`）
- 环境变量 `$USERGUIDE_BASE`
- 可选 CLI flags：`--port`、`--no-auth`、`--auth-user`、`--auth-pass`、`--full`

### Outputs

- `$USERGUIDE_BASE/_input/{name}/references/`（首次创建）
- `$USERGUIDE_BASE/_input/{name}/config.yaml`（若用户预置则读，不主动写）
- `$USERGUIDE_BASE/{name}/`（输出目录，首次创建空目录）
- P0 检测报告（终端输出，含 framework_hint、dev_server_url、软件名、模式）

### Procedure

1. **解析 `$USERGUIDE_BASE`**：未设置时使用默认 `/opt/code/docs/lanlnk/UserGuide/`，并告知用户默认路径。
2. **校验 `$USERGUIDE_BASE` 可写**：尝试创建目录与临时文件；失败为 blocking error，终止并打印 "请检查 $USERGUIDE_BASE 权限：{path}"。
3. **发现软件名**（4 级优先级，找到即停）：
   1. 读源码根 `package.json` 的 `name` 字段；存在 `@scope/` 前缀时剥离。
   2. 取源码目录名；若目录名为 `src` / `app` / `code` / `project` 等通用名则跳过本级。
   3. 解析用户调用文本中的显式名称（如 "为 mysqlbot 生成手册" 中的 `mysqlbot`）。
   4. 交互式询问用户。
   规范化为目录安全 kebab-case：小写、非字母数字替换为 `-`、去除首尾 `-`。
4. **检测 framework_hint**：读 `package.json.dependencies`，按关键字匹配（`vue` → vue3、`react` → react、`next` → next、`nuxt` → nuxt）；识别失败标记 `unknown`。仅诊断用，不影响后续行为。
5. **发现 dev server URL**：按优先级探测 base URL。
   - `--port <N>` 显式指定时直接拼 `http://localhost:{N}`。
   - 否则探测 5173 / 3000 / 8080 三个常见端口（HTTP HEAD 请求）。
   - 否则读 `vite.config.js` / `next.config.js` / `nuxt.config.ts` 中的 `server.port` / `port` 字段。
   - 全部失败为 blocking error，终止并提示：`"请启动 dev server（如 npm run dev）后重试，或用 --port <N> 指定端口"`。
6. **检查 playwright skill 可用性**：尝试加载 `skill(name="playwright")`（轻量加载，不执行任何浏览器操作）。失败时标记 `degraded_mode: "playwright_unavailable"`，不终止；后续 P2.5 / P3 跳过，P4 走占位符。
7. **检测 `$USERGUIDE_BASE/_input/{name}/`**：
   - 不存在：创建 `_input/{name}/references/`，打印路径告知用户可投放参考材料。
   - 已存在且 `references/` 内有文件：视为"用户预置"，沿用，不询问。
8. **读取 `config.yaml`**（若存在）：按 `references/config-yaml-schema.md` 校验 YAML 语法与字段；非法字段 warning 但不终止；YAML 语法错误终止。
9. **增量模式检测**：若 `$USERGUIDE_BASE/{name}/analysis.json` 存在且未传 `--full`，询问用户 "全量重生成 / 增量更新"；`--full` 跳过询问强制全量。
10. **打印 P0 报告**：列出 framework_hint、dev_server_url、软件名、模式（full / incremental / degraded），等待 P1 启动。

### Failure Modes

| 失败类型 | 阻塞? | 处理 |
|---------|-------|------|
| `$USERGUIDE_BASE` 不可写 | 阻塞 | 终止，打印权限排查指引 |
| 源码目录无 `package.json` | 非阻塞 | framework_hint=unknown，软件名走 2/3/4 级 |
| Dev server 探测失败 | 阻塞 | 终止，提示 `npm run dev` 或 `--port` |
| Playwright skill 加载失败 | 非阻塞 | 标记 degraded_mode，跳过 P2.5/P3，P4 走占位符 |
| `config.yaml` YAML 语法错 / 未知字段 | 阻塞 / 非阻塞 | 语法错终止；未知字段 warning 继续 |

### References

- `references/config-yaml-schema.md`：config.yaml 字段、合并优先级、校验规则。

---

## P1: 应用结构发现

### Goal

通过运行时探测 + 源码 hint，输出描述应用全貌的 `analysis.json`，作为 P2-P4 的唯一数据源。

### Inputs

- P0 报告（dev_server_url、framework_hint、software_name、degraded_mode、mode）
- 源码项目路径（用于 router 配置、menu 定义、page components 读取）
- `$USERGUIDE_BASE/{name}/analysis.json`（增量模式下作为 diff 基准）
- `_input/{name}/config.yaml.ignore_modules`

### Outputs

- `$USERGUIDE_BASE/{name}/analysis.json`（schema 见 `references/analysis-schema.md`）
- 增量模式下附带 `analysis.json.diff`（含 `added` / `removed` / `changed` / `unchanged` 四个数组）

### Procedure

1. **加载 playwright skill**：调用 `skill(name="playwright")` 并保持上下文。P0 已标记 degraded_mode 时跳过本步与运行时探测，仅靠源码 hint。
2. **运行时探测根路由**：导航到 `dev_server_url`，等待 `body` 渲染完成。若被重定向到 `/login` 等鉴权页，标记 `auth_required: true`。
3. **提取导航结构**：依次扫描 `nav` / `aside` / `header` 内的菜单项、侧边栏链接、顶部 bar 链接，记录每项的文本与 href / route path → 候选路由列表（`discovered_via: "menu"` / `"sidebar"`）。
4. **探测 router state**：读取 Vue Router 全局实例（`window.__VUE_APP__` / app.config.globalProperties.$router）或 React Router（`window.__REACT_ROUTER__` 等暴露点）的注册路由表。未在可见菜单中的路由加入候选列表，`discovered_via: "router_state"`。
5. **源码 hint 读取**：扫描源码 `src/router/` 下的配置文件、page components 目录、menu definitions。找出运行时未探测到的路由（权限受限、modal 触发、动态注册），加入候选列表，`discovered_via: "source_hint"`，`accessible: false`，`requires_role` 按源码 meta 填写。
6. **逐路由探测元素**：对每条 `accessible: true` 路由，导航并等待渲染，提取 buttons（可见文本或 `aria-label`）、inputs（`placeholder` 或关联 label）、tables（列标题）、dropdowns / links / modals 标识。按 `references/analysis-schema.md` 的 Element 对象字段填充 `routes[].elements[]`。
7. **推断用户流程**：对每个路由，按元素组合（"新建按钮 + 表单 modal + 保存按钮 + 列表"等模式）识别 CRUD / 查询 / 导出等典型流程，写入 `routes[].flows[]`。每个 step 引用 `elements[].element_id`，不重复写文本。
8. **识别登录流程**：若第 2 步探测到重定向，或源码定义 `/login` 路由带表单，填充 `analysis.auth`（`login_route` / `form_fields` / `post_login_route` / `post_login_assertion`）。无鉴权时 `auth: null`。
9. **应用 `ignore_modules`**：从 `routes[]` 中剔除 `title` 精确匹配 `config.yaml.ignore_modules` 任一字符串的路由。被剔除路由不进入下游阶段。
10. **填充元数据**：`app_name` = 规范化软件名；`version` 从 `package.json.version` 读，缺失为 `"unknown"`；`framework_hint` 来自 P0；`dev_server_url` 来自 P0；`generated_at` 为当前 UTC ISO 8601。
11. **增量 diff 计算**（仅 incremental 模式）：与上次 `analysis.json.routes` 对比。`added` = 新增 path；`removed` = 上次有本次无；`changed` = path 相同但 elements 数量或 flow 签名不同；`unchanged` = 其余。写入 `analysis.json.diff`。
12. **schema 校验**：按 `references/analysis-schema.md` 的校验规则（顶层字段完整、ID 格式与唯一性、step 引用合法性、element 字段匹配 type、auth 形状、`discovered_via` 取值）自检。失败立即终止并打印错误。
13. **写出 `analysis.json`**（增量模式仅写 added + changed 部分，unchanged 路由原样保留）。

### Failure Modes

| 失败类型 | 阻塞? | 处理 |
|---------|-------|------|
| playwright skill 不可用（P0 已标记） | 非阻塞 | 仅靠源码 hint，元素 / flow 字段可能稀疏，记录到 `_debug_notes` |
| 某路由导航 timeout | 非阻塞 | 标记 `accessible: false`，`requires_role` 或备注 |
| Router state 全局实例未暴露 | 非阻塞 | 仅靠菜单 + 源码 hint，缺失路由记入 `_debug_notes` |
| Schema 校验失败 | 阻塞 | 终止，打印缺失字段或非法取值 |

### References

- `references/analysis-schema.md`：analysis.json 顶层字段、Route / Element / Flow / Auth 对象、校验规则。
- `references/config-yaml-schema.md`：`ignore_modules` 匹配规则。

---

## P2: 截图规划

### Goal

把 `analysis.json` 翻译为 `screenshot-plan.json`，即一组 playwright 可机械执行的 task / action 序列。locator 严格使用文本/角色策略。

### Inputs

- `$USERGUIDE_BASE/{name}/analysis.json`
- `$USERGUIDE_BASE/{name}/analysis.json.diff`（增量模式下用于限定需要重新规划的路由）
- `$USERGUIDE_BASE/_input/{name}/config.yaml`（`screenshot_density` 影响截图频率）

### Outputs

- `$USERGUIDE_BASE/{name}/screenshot-plan.json`（schema 见 `references/screenshot-plan-schema.md`）

### Procedure

1. **遍历 accessible routes**：对 `analysis.routes[]` 中每条 `accessible: true` 路由生成一个 page task；`accessible: false` 路由不进入 plan。
2. **生成 auth_task**（仅 `analysis.auth` 非 null 时）：作为 `tasks[0]`，固定 `id: "task_000"`、`page_title: "登录"`。actions 序列：navigate → fill 用户名 → fill 密码 → click 提交 → assert 登录断言。fill 的 value 用占位符 `"<from .auth.json>"`。
3. **构建 page task actions**：对每个 accessible route：
   1. `navigate` 到 `dev_server_url + route.path`
   2. `wait` 主内容元素（用 route 首个元素 text 或 aria-label 定位）
   3. `screenshot` 页面初始态（`name` 用 route.title + "初始页"）
   4. 对 `route.flows[]` 的首个 flow：按 step 顺序输出对应 click / fill / select action，并在关键节点（modal 打开、提交完成）插入 `screenshot` action
   5. 多 flow 场景受 `style-fingerprint.step_density` 调节：`low` 仅展开主 flow，`medium` 展开主 flow 全步骤，`high` 展开全部 flow
4. **生成 locator**：每个需定位元素的 action 携带 `locator` 对象，`strategy` 取 `text` / `role` / `placeholder` / `label` 之一。元素首选策略见 `analysis-schema.md` 的 type 主用字段表。**禁止生成 `strategy: "css"` 或 `"xpath"`**。
5. **填充 action 元数据**：`screenshot` action 必须含 `name`（短描述，用于文件名）与 `description`（长描述，用于手册图示文字）。`wait` 必须含 `timeout_ms`（5000-30000）。`assert` 必须含 `expected_state` 中文短句。
6. **action type 白名单**：只允许 `navigate` / `wait` / `screenshot` / `fill` / `click` / `hover` / `scroll` / `select` / `assert` 九种。其他类型立即报错 `"Unsupported action type: {type}"`。
7. **受 screenshot_frequency 调节截图密度**：
   - `low`：仅页面初始 + flow 结束共 2-3 张
   - `medium`：页面初始 + 每个关键节点 4-6 张
   - `high`：每个 step + hover/scroll 中间态 8+ 张
8. **增量模式限定范围**：仅对 `diff.added` 与 `diff.changed` 中的路由生成新 task；`diff.unchanged` 路由复用上次 `manifest.json` 与 `imgs/`，不进入新 plan。
9. **schema 校验**：按 `references/screenshot-plan-schema.md` 校验规则（顶层字段、Task ID 唯一与格式、auth_task 一致性、Action type 取值、Locator 策略、字段完整性、凭据占位符约束）自检。
10. **写出 `screenshot-plan.json`**。

### Failure Modes

| 失败类型 | 阻塞? | 处理 |
|---------|-------|------|
| 发现 CSS / XPath locator | 阻塞 | 立即修正为 text/role 策略 |
| 未知 action type | 阻塞 | 终止并打印 `"Unsupported action type: {type}"` |
| Schema 校验失败 | 阻塞 | 终止并打印缺失字段 |
| 凭据占位符 locator 不是 placeholder/label | 阻塞 | 修正 locator 策略 |

### References

- `references/screenshot-plan-schema.md`：Task / Action / Locator 结构、9 种 action type 字段、校验规则。
- `references/style-fingerprint.md`：`screenshot_frequency` 维度取值如何影响截图密度。

---

## P2.5: 登录凭据

### Goal

获取并持久化 demo 账号凭据，供 P3 在 authenticated context 中执行截图。

### Inputs

- `$USERGUIDE_BASE/{name}/analysis.json.auth`（null 时跳过本阶段）
- `$USERGUIDE_BASE/_input/{name}/.auth.json`（若已存在则复用）
- CLI flags：`--no-auth` / `--auth-user` / `--auth-pass`
- `config.yaml.auth.hint`（可选提示文本）

### Outputs

- `$USERGUIDE_BASE/_input/{name}/.auth.json`（mode 0600，含 `username` 与 `password` 字段）

### Procedure

1. **跳过条件**：
   - `analysis.auth === null` → 跳过本阶段
   - `--no-auth` flag 存在 → 跳过本阶段，并将 `analysis.routes[]` 中 `requires_auth: true` 的路由全部标记 `accessible: false`，备注 "未提供凭据"
   - P0 标记 `degraded_mode: "playwright_unavailable"` → 跳过本阶段（无截图需要凭据）
2. **复用现有凭据**：`.auth.json` 已存在 → 读取并继续，不提示用户。
3. **首次获取凭据**（`.auth.json` 不存在）：
   - 优先级 1：`--auth-user` + `--auth-pass` flag 同时存在 → 直接使用
   - 优先级 2：交互式询问用户。若 `config.yaml.auth.hint` 存在，连同提示文本一起打印（如 "管理员账号在 .env 的 DEMO_USER/DEMO_PASS"）
4. **写入 `.auth.json`**：JSON 格式 `{"username": "...", "password": "..."}`，权限 mode 0600。路径 `$USERGUIDE_BASE/_input/{name}/.auth.json`。
5. **告知 gitignore**：首次写入时打印提示：`"请确保 $USERGUIDE_BASE/_input/**/.auth.json 已加入 .gitignore"`。

### Failure Modes

| 失败类型 | 阻塞? | 处理 |
|---------|-------|------|
| `--no-auth` 但所有路由都需要 auth | 非阻塞 | plan 为空，P3 无 task，P4 仅渲染模块章节标题 |
| 用户拒绝提供凭据 | 阻塞 | 询问是否改用 `--no-auth`，否则终止 |
| `.auth.json` 写入失败（权限） | 阻塞 | 终止并提示目录权限 |

### References

- `references/screenshot-plan-schema.md`：凭据占位符 `"<from .auth.json>"` 在 fill action 中的使用约束。
- `references/config-yaml-schema.md`：`auth.hint` 字段的安全约束（MUST 是"指引去哪找"，不含明文密码）。

---

## P3: 截图执行

### Goal

加载 builtin playwright skill，按 `screenshot-plan.json` 顺序执行所有 action，产出 `imgs/` 与 `manifest.json`。单页失败不阻塞其他页。

### Inputs

- `$USERGUIDE_BASE/{name}/screenshot-plan.json`
- `$USERGUIDE_BASE/_input/{name}/.auth.json`（auth 场景）

### Outputs

- `$USERGUIDE_BASE/{name}/imgs/*.png`
- `$USERGUIDE_BASE/{name}/manifest.json`（schema 见本阶段下方与 `references/limitations.md`）

### Procedure

1. **加载 playwright skill**：在 P3 入口调用 `skill(name="playwright")`。P0 已确认可用，但本步再次确认；若意外失败，写 `manifest.json = {"executor_error": "...", "tasks": []}`，跳到 P4 degraded 路径。
2. **遍历 tasks**：按 `screenshot-plan.json.tasks[]` 顺序处理。
3. **执行 auth_task**（如存在）：作为首个 task 执行，建立 authenticated context（cookies + localStorage）。后续 task 在同一 context 中执行，避免重复登录。
4. **逐 action 分发**：对每个 task 的 `actions[]` 顺序执行，按 type 分发到 playwright skill 的对应 API：
   - `navigate` → `page.goto(url)`
   - `wait` → `page.wait_for(locator, timeout_ms)`
   - `screenshot` → `page.screenshot(path=...)`
   - `fill` → `page.fill(locator, value)`；value 为 `"<from .auth.json>"` 时从 `.auth.json` 读真实值
   - `click` → `page.click(locator)`
   - `hover` → `page.hover(locator)`
   - `scroll` → `page.evaluate` 或 `mouse.wheel`
   - `select` → `page.select_option(locator, label=value)`
   - `assert` → 验证 `expected_state`；executor 实现"可见 + 文本匹配"两种常见情况，复杂断言降级为"可见即通过"
5. **locator fallback chain**：若主 locator 失败（timeout），按 `text → role → placeholder → label` 顺序尝试备选策略。每次尝试记入 manifest 的 `resolved_locator`。
6. **截图命名**：`{module_slug}_{step_index}_{description_slug}.png`。`module_slug` 为 route.title 的 kebab-case（中文在 Unicode 文件系统原样保留，ASCII-only 文件系统用拼音 slug）；`step_index` 为 screenshot action 在 task 中的位置；`description_slug` 为 action `name` 的 slug 化。命名冲突追加 `_2` 后缀。
7. **per-action 失败处理**：action timeout / selector not found / navigation error 时，标记该 action `status: "failed"`，同 task 剩余 action 标记 `status: "skipped"`，继续下一 task。**不终止 P3 整体**。
8. **写 manifest.json**：顶层含 `app_name` / `generated_at` / `executor_error` (null 或错误字符串) / `tasks[]`。每个 task 含 `id` / `page_title` / `actions[]`；每个 action 含 `action_id` / `type` / `status` (`success` / `failed` / `skipped`) / `elapsed_ms` / `output_path` (截图成功时) / `primary_locator` / `resolved_locator` (fallback 后) / `error`。完整 schema 见 `references/screenshot-plan-schema.md`。
9. **empty state 警告**：截图前若检测到列表 0 行、表单未填、数据未加载，在 manifest 对应 action 加 `warning: "empty_state"` 字段，P5 提示用户 seed 后增量重跑。

### Failure Modes

| 失败类型 | 阻塞? | 处理 |
|---------|-------|------|
| playwright skill 加载失败 | 非阻塞（P4 走 degraded） | 写 `manifest.json.executor_error`，所有 task `status: "failed"` |
| 单 action timeout | 非阻塞 | 标记 failed，skip 同 task 剩余，下一 task 继续 |
| 单 action selector 不存在 | 非阻塞 | 尝试 fallback chain；全部失败后标记 failed |
| navigate 失败（404 / 网络错） | 非阻塞 | manifest 含 `error: "navigation_failed"` 与 `url` 字段 |
| assert 失败 | 非阻塞 | 视同 action failed，影响后续 skip 链 |

### References

- `references/screenshot-plan-schema.md`：action type 与 locator 策略对应 playwright API 的语义说明。
- `references/limitations.md`：WebSocket 依赖 UI、iframe 微前端等已知截图限制场景。

---

## P4: 渲染输出

### Goal

调用 `scripts/render_manual.py` 纯函数渲染器，从 `analysis.json + manifest.json + style-fingerprint.json` 一次性产出三份输出文件。

### Inputs

- `$USERGUIDE_BASE/{name}/analysis.json`
- `$USERGUIDE_BASE/{name}/manifest.json`
- `$USERGUIDE_BASE/{name}/style-fingerprint.json`（本阶段先生成）
- `$USERGUIDE_BASE/_input/{name}/references/*`（参考资料，用于指纹提取）
- `$USERGUIDE_BASE/_input/{name}/config.yaml`（可选覆盖）

### Outputs

**交付版**（给人看，含截图，主目录）：

- `$USERGUIDE_BASE/{name}/操作手册.md`
- `$USERGUIDE_BASE/{name}/chunks.jsonl`（预切块，供高质量 RAG 用）
- `$USERGUIDE_BASE/{name}/llms.txt`

**知识库版**（给 RAG，去图片引用，子目录）：

- `$USERGUIDE_BASE/{name}/知识库版/操作手册.md`

> **为什么分目录**：交付版含 `![](imgs/xxx.png)` 截图引用，对 RAG 是路径噪音；知识库版去掉图片引用只保留文字（含 `> 图示：xxx` 描述），RAG 系统只索引 `知识库版/` 子目录。

### Procedure

1. **参考资料 ingest**（P4 前置子步骤）：扫描 `_input/{name}/references/`，按格式分发：
   - `.md` / `.txt` / `.html`：直接读文本
   - `.docx` / `.pptx`：调用 `markitdown`（复用 `material-importer` 的安装，不重复装）。若 markitdown 不可用，跳过该文件并 warning
   - `.pdf`：调用 `pypdf` 提取文本
   - `urls.txt`：每行一个 URL，逐行 `webfetch` 抓取
   - 其他扩展名：跳过并 warning `"Unsupported reference format: .{ext}, skipped"`
2. **提取 style fingerprint**：对上一步收集的所有参考文本，按 `references/style-fingerprint.md` 的启发式规则计算 5 维指纹（chapter_depth / step_density / screenshot_frequency / table_preference / faq_style）。
3. **应用 config 覆盖**：`config.yaml.screenshot_density` 覆盖 `screenshot_frequency`，`sources.screenshot_frequency = "config"`。其他维度保持 reference 来源。
4. **无参考资料的默认指纹**：`_input/{name}/references/` 为空或不存在时，使用 `references/style-fingerprint.md` 的默认值（`chapter_depth: 2` / `step_density: "medium"` / `screenshot_frequency: "medium"` / `table_preference: "minimal"` / `faq_style: "short"`），`sources` 全部为 `"default"`。
5. **写出 `style-fingerprint.json`** 到 `$USERGUIDE_BASE/{name}/style-fingerprint.json`，含 5 维取值与 `sources` provenance。
6. **调用 renderer**：
   ```bash
   cd skills/docs/doc-generator
   uv run python scripts/render_manual.py \
     --analysis $USERGUIDE_BASE/{name}/analysis.json \
     --manifest $USERGUIDE_BASE/{name}/manifest.json \
     --style-fingerprint $USERGUIDE_BASE/{name}/style-fingerprint.json \
     --output-dir $USERGUIDE_BASE/{name}/
   ```
7. **renderer 行为契约**（agent 不直接做，但要理解）：
   - 纯函数：仅读三个输入文件，仅写三个输出文件。无网络、无浏览器、无 LLM。
   - 模板：`references/manual-template.md` 定义的章节结构（一、快速开始 / 二、功能模块详解 / 三、常见问题 / 四、附录）。
   - 失败截图占位：`manifest.json` 标记 failed 的 action 对应位置渲染为 `> ⚠️ 截图失败：{reason}（步骤 {N}）`，不输出 `![](...)` 空链接。
   - chunks.jsonl 边界对齐 manual-template.md 章节：每模块至少 1 个 `page_load` + N 个 `step` + 1 个 `element_table`，全局 M 个 `faq`。
   - 一致性：模块数、元素文本、chunk ID 唯一性由 renderer 强制校验。
8. **原子输出**：renderer 使用 temp 文件 + rename + rollback。任一输出失败时已写的部分自动删除，exit code 非零。agent 检测 exit code，非零时进入失败处理。
9. **失败处理**：renderer 非零退出时，打印 stderr，告知用户哪一步失败；保留三个输入文件供用户排查；不删除 `imgs/`。
10. **生成知识库版**（renderer 成功后执行）：从交付版 `操作手册.md` 派生去图片引用的知识库版，供 RAG 系统索引。此步是 sed 后处理，不修改 renderer：

    ```bash
    mkdir -p $USERGUIDE_BASE/{name}/知识库版
    {
      echo "> **知识库版** — 已去除图片引用，适用于 RAG 系统上传。完整版（含截图）见上级目录同名文件。"
      echo ""
      sed '/^!\[/d' "$USERGUIDE_BASE/{name}/操作手册.md"
    } > "$USERGUIDE_BASE/{name}/知识库版/操作手册.md"
    ```

    规则：删除所有 `![xxx](yyy)` 开头的图片引用行；**保留** `> 图示：xxx` / `> ⚠️ 截图失败：xxx` 等文字描述（对 RAG 有语义价值）。此步失败为非阻塞（知识库版是派生产物，不影响主交付）。

### Failure Modes

| 失败类型 | 阻塞? | 处理 |
|---------|-------|------|
| 输入文件缺失（analysis/manifest/style-fingerprint） | 阻塞 | 终止并提示哪份缺失 |
| markitdown 不可用（处理 docx/pptx 参考） | 非阻塞 | warning 跳过该参考，继续其他参考 |
| webfetch 失败（处理 urls.txt） | 非阻塞 | warning 跳过该 URL，继续其他 |
| renderer exit 非零 | 阻塞 | 打印 stderr，保留输入文件 |
| Schema 校验失败（renderer 内部） | 阻塞 | renderer 已 rollback，agent 打印错误位置 |

### References

- `references/manual-template.md`：操作手册.md 的 Jinja2 模板、Context 变量、校验规则。
- `references/chunks-jsonl-schema.md`：chunks.jsonl 的 LangChain Document 结构、metadata 字段、chunk_id 构造规则。
- `references/llms-txt-format.md`：llms.txt 的 llmstxt.org 子集、4 个 H2 章节强制结构、anchor 生成规则。
- `references/style-fingerprint.md`：5 维指纹定义、启发式提取算法、合并优先级。

---

## P5: 交互确认与交付

### Goal

向用户展示生成结果全貌（目录、统计、风险），并提供迭代入口。

### Inputs

- `$USERGUIDE_BASE/{name}/` 下全部产出
- `$USERGUIDE_BASE/{name}/manifest.json`（统计来源）

### Outputs

- 终端交付摘要（无新文件）

### Procedure

1. **展示 TOC**：列出所有模块（按 `analysis.routes[]` 顺序），每条标注：
   - 模块标题与路由路径
   - 截图数（成功 / 失败 / 跳过）
   - accessible 状态（不可访问的模块标注 "需 X 权限"）
   - 是否被 `ignore_modules` 排除
2. **展示汇总统计**：
   ```text
   应用名称: mysqlbot (vue3, v1.4.2)
   发现路由: 12 条（accessible: 10, 受限: 2）
   截图结果: 成功 38 / 失败 6 / 跳过 3
   chunks: 共 56 条（page_load 10 + step 35 + element_table 10 + faq 1）
   模式: full | incremental | degraded
   ```
3. **展示最终交付路径**（绝对路径）：
   - 交付版（给人看）：
     - `$USERGUIDE_BASE/{name}/操作手册.md`
     - `$USERGUIDE_BASE/{name}/chunks.jsonl`
     - `$USERGUIDE_BASE/{name}/llms.txt`
     - `$USERGUIDE_BASE/{name}/imgs/`
   - 知识库版（给 RAG）：
     - `$USERGUIDE_BASE/{name}/知识库版/操作手册.md`
4. **提示风险与空状态**：列出 `manifest.json` 中所有 failed action 与 empty_state warning，建议用户：
   - failed 截图：检查元素是否存在或文案是否变更，修正后用增量模式重跑
   - empty_state：seed 演示数据后用增量模式重跑受影响模块
5. **提供迭代入口**：
   - 调整风格：用户编辑 `_input/{name}/config.yaml`（如 `screenshot_density: "high"`）或投放新参考材料后，仅重跑 P4（renderer 用现有 analysis + manifest）
   - 增量更新：源码变更后重跑触发增量模式，仅对新 / 变更路由重做 P1-P3
   - 强制全量：`--full` flag 重跑整个 pipeline
6. **degraded 模式特殊提示**：若 P0 / P3 标记 degraded，明确告知用户哪些模块因 playwright 不可用 / dev server down 用占位符替代，恢复后用 `--full` 重跑。

### Failure Modes

无阻塞失败。P5 是只读展示阶段，所有错误在前序阶段已处理。

### References

- `references/limitations.md`：v1 已知限制与 v2 路线图，向用户解释"为什么某些场景不被支持"。

---

## Cross-Skill Coordination

### 与 builtin playwright skill 的协作

| 时机 | 动作 |
|------|------|
| P0 | 探测性加载 `skill(name="playwright")` 验证可用性，失败时标记 degraded_mode |
| P1 | 复用已加载的 playwright skill 上下文，导航并提取 DOM 信息 |
| P3 入口 | 正式加载 `skill(name="playwright")`，开始截图会话 |
| P3 执行 | 按 `screenshot-plan.json.tasks[].actions[]` 顺序调用 playwright API |
| P3 结束 | 关闭浏览器 context，写 manifest.json |

**契约层**：`screenshot-plan.json` 是 doc-generator 与 playwright skill 之间唯一的接口。playwright skill 的 API 演进不影响 doc-generator，只要 plan schema 保持兼容。doc-generator 不直接调用 Playwright Python 库。

### 与 material-importer 的复用关系

P4 处理 `.docx` / `.pptx` 参考资料时调用 `markitdown`，**复用 `material-importer` skill 的依赖安装**，不重复安装：

- 检测路径 `$LANLNK_BASE/../../skills/business/material-importer/.venv/bin/markitdown` 或全局 PATH 上的 markitdown
- 若 material-importer 未 sync 或全局不可用：warning `"markitdown unavailable, skipped {N} docx/pptx references"`，跳过这些参考，继续处理 `.md` / `.txt` / `.pdf` / URL
- 不在 doc-generator 的 `.venv` 中重复安装 markitdown（避免依赖冲突）

### 不存在的协作

- 不调用 word-master / ppt-master（输出格式为 Markdown + JSONL + TXT，不生成 Office 文件）
- 不调用 bid-doc-master / company-intro-generator（业务领域不同）

---

## Configuration & Env Vars

### 环境变量

| 变量 | 默认值 | 作用 |
|------|--------|------|
| `$USERGUIDE_BASE` | `/opt/code/docs/lanlnk/UserGuide/` | 文档根目录。输入在 `_input/{name}/`，输出在 `{name}/` |

### CLI Flags

| Flag | 取值 | 作用 |
|------|------|------|
| `--port <N>` | 端口号 | 显式指定 dev server 端口，跳过自动探测 |
| `--no-auth` | 无值 | 跳过 P2.5，所有 auth 路由标记 inaccessible |
| `--auth-user <u>` | 字符串 | CI 场景非交互提供用户名（需配 `--auth-pass`） |
| `--auth-pass <p>` | 字符串 | CI 场景非交互提供密码 |
| `--full` | 无值 | 强制全量重生成，跳过增量询问 |

### `_input/{name}/config.yaml`

完整字段、合并规则、校验规则见 `references/config-yaml-schema.md`。关键项：

- `auth.hint`：凭据位置的人类可读提示（不含明文密码）
- `ignore_modules`：按 route.title 精确匹配排除模块
- `screenshot_density`：覆盖 `style-fingerprint.screenshot_frequency`
- `branding.primary_color`：截图标注卡片主色（hex）

---

## Usage Examples

### 示例 1：基础调用

> 用户："为 /opt/code/mysqlbot 生成操作手册"

```text
Agent:
   [P0] framework_hint: vue3 | dev_server: http://localhost:5173
        软件名: mysqlbot (package.json) | 模式: full | playwright: 可用
        已创建 $USERGUIDE_BASE/_input/mysqlbot/references/

   [P1] 探测根路由，检测到登录重定向 → /login
        侧边栏 8 项 + router_state 2 项 + 源码 hint 1 项(/admin, requires_role: admin)
        写出 analysis.json (11 routes, 1 auth)

   [P2] 1 auth_task + 10 page tasks，共 47 actions (含 28 screenshot)
        全部 locator 用 text/role 策略，0 个 CSS

   [P2.5] 首次运行，询问用户 demo 账号 → 写入 .auth.json (mode 0600)
          提示将 _input/**/.auth.json 加入 .gitignore

   [P3] 加载 skill(name="playwright")，执行 auth_task + 10 page tasks
        成功 38 / 失败 6 / 跳过 3 → manifest.json + imgs/ (38 张)

   [P4] 无参考资料，用默认 fingerprint
        render_manual.py → 操作手册.md + chunks.jsonl (56 行) + llms.txt (38 行)

   [P5] TOC: 仪表盘(4 图) / 用户管理(6 图) / 订单管理(5 图) / ...
        统计: 路由 11 (10 accessible, 1 受限) | 截图 38 成功 / 6 失败 / 3 跳过 | chunks 56
        交付: $USERGUIDE_BASE/mysqlbot/{操作手册.md, chunks.jsonl, llms.txt, imgs/}
        6 张失败截图需排查（多为"导出"按钮文案变更），seed 数据后增量重跑。
```

### 示例 2：增量更新

> 用户："为 mysqlbot 重新生成手册"（`$USERGUIDE_BASE/mysqlbot/analysis.json` 已存在）

```text
Agent:
   [P0] 检测到既有 analysis.json → 询问全量/增量 → 用户选增量
   [P1] diff.added: ["/reports"] | diff.changed: ["/users"] (新增"导出"按钮)
        | diff.unchanged: 9 条
   [P2] 仅对 added + changed 生成新 task
   [P3] 仅执行 2 个新 task → 截图 7 张全部成功
   [P4] renderer 用新 analysis + 合并 manifest 渲染 → chunks 56→62 行
   [P5] TOC 标注 9 个模块"(复用上次截图)"，3 个模块"(本次新生成)"
```

### 示例 3：Dev server 未启动（阻塞）

> 用户："为 mysqlbot 生成手册"，dev server 未启动

```text
Agent:
   [P0] --port 未指定
        localhost:5173/3000/8080 全部 connection refused
        vite.config.js 读到 server.port=5173 (仍 refused)
        → 阻塞错误，终止

   提示用户:
   "无法连接 dev server。请检查:
    1. 是否已运行 npm run dev？常见端口 5173 / 3000 / 8080
    2. 自定义端口请用 --port <N> 指定
    3. vite.config.js 的 host 限制确认 0.0.0.0 或 localhost 可访问

    示例重试: cd /opt/code/mysqlbot && npm run dev &"
```

> 若 dev server 正常但 playwright skill 不可用（degraded 模式）：P0 标记 → P1 仅靠源码 hint → P2.5/P3 跳过 → manifest.executor_error 写入 → P4 渲染手册但所有图位为占位符 → P5 提示恢复 playwright 后用 `--full` 重跑。

---

## 关键约束速查

| 约束 | 来源 | 阻塞? |
|------|------|-------|
| 不写 AST parser，运行时优先 | design D1 | 设计原则 |
| locator 仅 text/role/placeholder/label | D2 + screenshot-plan-schema | 阻塞 |
| 不直接调 Playwright Python 库，走 builtin skill | D3 | 阻塞 |
| 三份输出从同一份 analysis + manifest 派生 | D4 | 阻塞 |
| 凭据只进 `.auth.json`，不进代码 / git | D5 | 阻塞 |
| 输入输出目录分离，首次自动建输入目录 | D6 | 阻塞 |
| `render_manual.py` 纯函数 | D7 | 阻塞 |
| `llms.txt` 遵循 llmstxt.org 子集 | D8 | 阻塞 |
| 5 维风格指纹，可被 config 覆盖 | D9 | 阻塞 |
| 不做多模态 captioning（MVP） | D10 | 设计原则 |
| 增量模式经 analysis.json diff | D11 | 设计原则 |

完整已知限制清单与 v2 路线图见 `references/limitations.md`。
