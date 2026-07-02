# Known Limitations & v2 Roadmap

This document lists the known limitations of doc-generator v1 and outlines rough directions for v2. The MVP deliberately scopes down to deliver a stable contract for the most common case (Chinese-only SPA with username/password auth and a running dev server). Anything outside that envelope is documented here so users can plan workarounds and so contributors know where the next round of investment should go.

Limitations are facts about v1's behavior, not bugs. Roadmap items are speculative directions, not commitments.

## 已知限制

### 1. iframe 嵌入的微前端不被发现也不被截图

**表现**：当目标应用通过 `<iframe src="...">` 嵌入子应用（如 qiankun、wujie、micro-app 等微前端框架）时，P1 的运行时探测只看到外层壳应用的路由；P3 的 Playwright executor 默认不切换 iframe 上下文。

**用户感知**：手册中只出现壳应用的菜单项；微前端内的页面缺失或仅以"外部链接"形式列出，无截图、无元素说明。

**临时方案**：对微前端子应用单独运行 doc-generator（把它当成独立 SPA 处理），生成独立手册。

**根本原因**：跨 iframe 的路由发现、locator 解析、上下文切换是独立工程，且微前端框架的 iframe 沙箱策略各异。

### 2. 多语言手册（中/英）不支持

**表现**：MVP 仅生成中文手册。即使目标应用 UI 是英文（如 React + Ant Design 默认英文），生成的手册中文骨架会把英文 UI 文案夹在中文段落中，可读性下降但不影响功能。

**用户感知**：手册骨架强制中文（章节标题"功能模块详解"、"操作步骤"等）；元素文本与截图描述以应用实际语言为准（可能是英文）。

**临时方案**：用户可手动 post-process `操作手册.md`，但 `chunks.jsonl` 的 metadata 不受影响。

**根本原因**：对齐仓库约定（中文为主）与决策 D5（MVP 仅中文）。

### 3. 不支持 per-app 自定义 Jinja2 模板

**表现**：所有应用共用同一份 `references/manual-template.md`。用户无法通过 `_input/{name}/templates/manual.j2` 提供自己的 Jinja2 模板。

**用户感知**：手册版式风格统一，无法针对特定应用做差异化（如增加自定义封面页、版权页、变更日志等）。

**临时方案**：手动 edit 生成的 `操作手册.md`；或在 `render_manual.py` 输出后再跑一次外部脚本。

**根本原因**：决策 Q2 明确推迟到 v2，先稳定内置模板与 schema。

### 4. 不支持 CLI 子命令（如 `--regenerate <module>`）

**表现**：MVP 没有针对单个模块重新生成的 CLI 子命令。增量更新的唯一入口是默认的"比对 `analysis.json` diff"流程。

**用户感知**：若想只重生成"用户管理"模块，需手动删除该模块的旧截图与 manifest 段落，再触发增量流程。流程不直观。

**临时方案**：删除整个 `$USERGUIDE_BASE/{name}/` 目录后跑全量；或编辑 `analysis.json.diff` 手动标记目标模块为 `changed`。

**根本原因**：决策 Q4 决定，MVP 增量模式已覆盖大部分场景。

### 5. 不支持多模态 RAG 的图像 captioning

**表现**：`chunks.jsonl.metadata.screenshots` 仅存截图相对路径，不生成截图的文本描述（如"一个红色的删除按钮位于表格右侧"）。用户的 RAG 是纯文本向量库，无法回答"那个红色按钮在哪"类纯视觉查询。

**用户感知**：纯文本检索（"怎么新建用户"）正常；纯视觉检索失效。

**临时方案**：用户的下游 RAG 系统自行集成多模态 embedding（CLIP 等），按 `metadata.screenshots` 路径取图建立独立的图像索引。

**根本原因**：决策 D10 明确，多模态 captioning 是另一套架构，MVP 不做。

### 6. 不自动处理 OAuth/SSO 登录流程

**表现**：MVP 仅自动处理"用户名 + 密码"标准表单登录（即 `analysis.json.auth.form_fields` 描述的形态）。OAuth 跳转、SSO 重定向、企业微信/钉钉扫码等场景不会被 P2.5 自动生成 auth_task。

**用户感知**：受 OAuth 保护的应用在 P3 截图阶段全部标记为 `inaccessible`，手册中相应模块显示"需手动登录后截图"占位符。

**临时方案**：使用 `--no-auth` flag 跳过受保护模块，只生成公开模块手册；或用户手动登录后用 dev-browser / playwright skill 单独截图。

**根本原因**：OAuth 流程需要跳转第三方域名、处理回调，自动化复杂度高且跨 provider 差异大。

### 7. 依赖 WebSocket 的 UI 可能无法稳定截图

**表现**：当目标应用使用 WebSocket 推送数据（实时图表、协作表格、消息通知等），P3 的 `wait` action 可能永远等不到"稳定状态"，导致截图捕获到加载中或部分加载的中间态。

**用户感知**：截图内容不完整或显示 loading 转圈。

**临时方案**：用户可在 `screenshot-plan.json` 中手动调大 `wait.timeout_ms`，或在 `config.yaml` 中通过 `ignore_modules` 排除 WebSocket 重度模块。

**根本原因**：Playwright 的 `waitFor` 基于明确条件，无法判断 WebSocket 推送的"完成"；需要应用侧主动暴露 `data-ready` 属性或类似信号。

## v2 路线图

下列方向是 rough ideas，不承诺实现。每条对齐上面一个或多个限制。

### v2-1：iframe 与微前端支持

- 在 P1 阶段识别 `<iframe>` 标签并递归发现子应用路由
- P2 plan 生成时为 iframe 任务添加 `frame_locator` 字段
- 与 qiankun/wujie/micro-app 等主流微前端框架的集成示例
- 风险：iframe 跨域安全策略限制 DOM 访问

### v2-2：多语言手册

- 模板骨架抽取为 i18n 资源包，支持 zh-CN / en-US
- `analysis.json` 增加 `detected_locale` 字段，自动选择模板语言
- 用户在 config.yaml 中通过 `locale: "en-US"` 显式覆盖
- 风险：双语 RAG 召回的一致性

### v2-3：per-app 自定义 Jinja2 模板

- `_input/{name}/templates/manual.j2` 存在时优先加载，缺失时回退内置模板
- 提供"模板继承"机制：用户模板 `{% extends "builtin/manual.j2" %}` 仅覆盖部分 block
- 配套 lint 工具校验用户模板必须输出哪些 H2 章节（对齐 spec 的 Triple Output 一致性）
- 风险：用户模板可能破坏 chunk 边界对齐，需要额外约束

### v2-4：CLI 子命令体系

- `doc-generator render {name}`: 只跑 P4 渲染，复用已有 analysis + manifest
- `doc-generator regenerate {name} --module "用户管理"`: 仅对指定模块重跑 P2-P4
- `doc-generator diff {name}`: 显示当前 analysis.json 与上次的 diff，不写文件
- `doc-generator clean {name} --keep analysis`: 删除输出目录但保留 analysis.json
- 风险：子命令增多带来 CLI 复杂度，需要严格保持向后兼容

### v2-5：可选的多模态 captioning 阶段（P3.5）

- 在 P3 完成截图后、P4 开始前，可选启用 P3.5 阶段调用 VLM 为每张截图生成中文描述
- 描述文本写入 `chunks.jsonl` 对应 chunk 的 `page_content`，与原文合并
- 用户通过 `--caption` flag 启用，需要自备 VLM API key
- 风险：VLM 描述质量参差；用户可能误以为描述是应用文案

### v2-6：OAuth/SSO 自动化

- 在 `analysis.json.auth` 中扩展 `auth_type` 字段（`password` / `oauth_authorization_code` / `saml` 等）
- P2 plan 生成时为 OAuth 流程产出跳板任务（预填 client_id、redirect_uri）
- 与主流 IdP（Auth0、Keycloak、Azure AD）的参考实现
- 风险：跨 provider 的回调 URL 处理差异大

### v2-7：应用侧"就绪信号"协议

- 文档化一个轻量协议：应用暴露 `window.__DOCGEN_READY__` 全局变量或 `data-docgen-ready` 属性，标记当前页面可截图
- P3 `wait` action 增加新策略 `"signal"`，等待该信号翻转
- 与 WebSocket/实时 UI 配合，避免截图捕获中间态
- 风险：需要用户主动接入协议，对老应用不友好

## 校验规则

本文件是文档，无校验逻辑。但 v1 → v2 升级时需复查：

1. 每条 v2 路线图条目 MUST 对应至少一条 v1 限制，避免凭空新增。
2. 任一 v2 条目落地为正式 spec 前，MUST 先在此文件登记并标注版本目标。
3. 用户报告的限制若不在本文件清单中，MUST 先补充到此文件再讨论是否升级到 spec。
