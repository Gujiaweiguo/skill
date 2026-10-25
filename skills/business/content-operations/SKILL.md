---
name: content-operations
version: "1.1.0"
status: validated
scope: lnkwebsite
description: |-
  蓝联创新网站内容运营 Skill。将有证据支撑的选题按 Research、Generation、Validation、Draft Import
  四个阶段转成 lnkwebsite CMS 草稿，保留研究包、Pattern Draft、审阅记录、Article JSON、校验报告和导入回执。
  对已发布内容（article/case/product）提供 Maintenance 修订能力：改前快照 → diff 审阅 → 人审 → 应用，
  Skill 只建 pending-review 修订单，永不 approve/reject/apply。
  触发场景："生成官网文章草稿"、"校验 Article JSON"、"把已审批文章导入 CMS 草稿"、
  "修订已发布文章"、"给已发布内容建维护修订单"、"为 lnkwebsite 做内容运营"。
  仅处理 lnkwebsite 现有栏目，不负责公开发布、栏目扩展、排期自动化或批量导入。
compatibility: |-
  Requires Python 3.10+ and uv. Runtime scripts depend on the ``markdown`` library (auto-installed by ``uv sync``).
  Runtime artifacts use CONTENT_OUTPUT_BASE (default /opt/code/docs/lanlnk/lnkwebsite/content).
  Draft Import requires OpenCode MCP Streamable HTTP transport to the lnkwebsite MCP server.
  Maintenance requires MCP tools ``maintenance_revision_create`` / ``maintenance_revision_get``
  with token scope ``content.maintenance.draft`` + ``content.maintenance.read``.
---

# Content Operations

## Validation History (pilot → validated)

Promotion Rule: pilot → validated 需 3 次端到端跑通 + 人审通过。

| # | 日期 | 选题 | Pattern | Article ID | 人审 |
|---|------|------|---------|-----------|------|
| 1 | 2026-07-31 | 什么是 MCP（Model Context Protocol） | term-entry (ai-trends) | 24 | ✅ approved |
| 2 | 2026-08-01 | AI Agent vs Automation | industry-insight (ai-trends) | 25 | ✅ approved |
| 3 | 2026-08-01 | What is Function Calling | term-entry (ai-trends) | 26 | ✅ approved |

Promotion date: 2026-08-01. All 4 phases (Research → Generation → Validation → Draft Import) completed end-to-end for each pilot. 29 unit tests green at v1.0.0; 58 after the v1.1.0 Maintenance handler (29 pre-existing tests untouched).

## 目标与边界

把可追溯研究证据转换为可审阅、可验证、可审计的 lnkwebsite CMS 草稿。此 Skill 只创建草稿；公开发布属于独立的人工作业，不在本 Skill 的命令、脚本或凭据范围内。

适用：单篇官网 Article 的研究、起草、审阅、确定性校验和草稿导入。

不适用：修改 lnkwebsite 代码或 taxonomy、创建新栏目、批量迁移、定时任务、公开发布、修改 MCP/API 权限或保存凭据。

## 配置

```bash
export CONTENT_OUTPUT_BASE="${CONTENT_OUTPUT_BASE:-/opt/code/docs/lanlnk/lnkwebsite/content}"

cd /opt/code/skill/skills/business/content-operations
uv sync --group dev
```

- `CONTENT_OUTPUT_BASE` 未设置时使用 `/opt/code/docs/lanlnk/lnkwebsite/content`。
- 固定目录和文件契约见 `references/runtime-artifacts-v1.md`。
- Article 字段、栏目和错误契约见 `references/article-payload-v1.md`。

### MCP server 配置

OpenCode 必须配置一个 Streamable HTTP MCP server，连接 `http://127.0.0.1:5580/mcp`，并通过 `Authorization: Bearer <MCP token>` 请求头认证。Bearer token 由 OpenCode 的 MCP 配置管理，不传给 Skill 脚本，也不得写入模板、回执、日志或仓库文件。

Draft Import 由 agent 直接调用该 MCP server 的 `article_create`；Skill 脚本不实现 MCP 协议，也不发起 HTTP 请求。

## 阶段

### 1. Research

**输入**：选题、受众、选定 content pattern、可引用的一手或可靠二手来源。

**动作**：使用 `templates/v1/research-pack.md` 记录主张、证据、来源位置、证据强度、缺口和禁止外推项。遵守 `/opt/code/skill/references/docspec/`，不得把推断写成事实。

**输出**：`$CONTENT_OUTPUT_BASE/research-packs/<content-id>.md`。

**交接条件**：每个核心主张有来源；缺口已明确标注；已选定 content pattern。未满足时不得进入 Generation。

### 2. Generation

**输入**：通过交接条件的 Research Pack、选定 content pattern、品牌与事实约束。

**动作**：用 `templates/v1/pattern-draft.md` 生成 Markdown Pattern Draft。模板包含 term-entry 和 industry-insight 两种模式的节结构大纲。正文只能使用 Research Pack 支撑的事实，未决信息保留为待确认项。

**输出**：`$CONTENT_OUTPUT_BASE/drafts/<content-id>.md`。

**交接条件**：Research Pack 路径和 pattern 已写入 Draft；正文完整；事实、链接和品牌口径自检完成。随后将 Markdown 转为 HTML 并生成 Article JSON，提交人工审阅。

**Markdown → HTML 转换**：

```bash
uv run python -m scripts.markdown_to_html \
  "$CONTENT_OUTPUT_BASE/drafts/<content-id>.md" \
  --output "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/body.html"
```

然后将 `body.html` 的内容填入 `templates/v1/article.json` 的 `body` 字段，补全 `title`、`slug`、`category`、`summary` 等字段，产出 Article JSON。

### 3. Validation

**输入**：Pattern Draft、人工审阅记录、`$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/article.json`。

**动作**：审阅记录使用 `templates/v1/review-record.json`，且必须为 `decision=approved`、`slug_available=true`。运行确定性校验器：

```bash
uv run python -m scripts.validate_article \
  "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/article.json" \
  --report "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/validation-report.json"
```

**输出**：同一 `publish-jobs/<slug>/` 下的 Article JSON 和 `validation-report.json`。

**交接条件**：命令退出码为 0；报告 `valid=true`；报告 SHA-256 与 Article JSON 当前字节一致；审阅记录批准同一 source draft 和 payload digest。任一失败时不得调用 MCP `article_create`。

### 4. Draft Import

**输入**：已批准 source draft、匹配的 review record、Article JSON、有效 validation report，以及可用的 lnkwebsite MCP 连接。

**Step 1（Validation）**：在 MCP 调用前运行确定性校验：

```bash
uv run python -m scripts.validate_article \
  "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/article.json" \
  --report "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/validation-report.json"
```

**Step 2（MCP call）**：agent 从已校验的 Article JSON 读取 `title`、`body`、`slug`、`category`、`summary`、`source_name`、`commentary`，直接调用 MCP `article_create(title, body, slug, category, summary, source_name, commentary)`。不传 `status`；该工具始终创建 `status=draft`。记录 MCP 返回的 article ID。

**Step 3（Receipt）**：使用 MCP 返回值写入确定性回执：

```bash
uv run python -m scripts.write_receipt \
  "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/article.json" \
  --cms-article-id <id-from-mcp> \
  --cms-status draft \
  --source-draft "$CONTENT_OUTPUT_BASE/drafts/<content-id>.md" \
  --review-record "$CONTENT_OUTPUT_BASE/review/<content-id>.json" \
  --validation-report "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/validation-report.json" \
  --receipt "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/import-receipt.json"
```

**输出**：MCP 创建的 CMS 草稿和 `import-receipt.json`。回执记录 source draft、payload SHA-256、CMS article id、slug、category、status，不记录 MCP token。

**完成条件**：MCP `article_create` 返回 article ID，返回状态为 `draft`，且回执已原子写入。

## Maintenance（已发布内容修订，R-CMS-03）

针对已发布的 article/case/product 建立可追溯修订。**安全边界：Skill 建单（pending-review）不审单不应用**——approve/reject/apply 是人工 publisher 在 admin UI 的动作，Skill 与其脚本永不执行（OD-CMS03-TRANSPORT）；token scope `content.maintenance.draft` + `content.maintenance.read`。

产物目录：`$CONTENT_OUTPUT_BASE/maintenance/<entity-type>/<entity-id>/<工作名>/`（MCP 建单前用 `<entity-id>-proposed` 工作名，回执内记录真实 revision id）。

**Step 1（构建）**：保存当前快照 `current.json`（只读获取后落盘）与期望 `desired.json`，构建 payload 与人读 diff：

```bash
uv run python -m scripts.maintenance_payload \
  --entity-type article --entity-id 24 \
  --current "$MAINT/<id>-proposed/current.json" \
  --desired "$MAINT/<id>-proposed/desired.json" \
  --rationale "<修订理由>" \
  --output-dir "$MAINT/<id>-proposed"
```

输出 `proposed.json`（`proposed_fields` 仅含差异；服务端禁改字段 `{id,status,published_at,created_at,updated_at}` 一律不得进入，客户端预检阻塞）+ `diff-review.md`（改前 vs proposed，人审材料）。`base_digest` 为 current 快照字节 SHA-256。

**Step 2（校验）**：exit 码门禁 + SHA-256 校验报告：

```bash
uv run python -m scripts.validate_maintenance \
  "$MAINT/<id>-proposed/proposed.json" \
  --report "$MAINT/<id>-proposed/validation-report.json"
```

**Step 3（建单回执）**：agent 调 MCP `maintenance_revision_create(entity_type, entity_id, rationale, proposed_fields)`（服务端按其快照算 base_digest 并返回 `id/base_digest/proposed_fields/filtered_fields/status`），随后按返回值落回执：

```bash
uv run python -m scripts.maintenance_receipt \
  "$MAINT/<id>-proposed/proposed.json" \
  --revision-id <id-from-mcp> \
  --cms-status <status-from-mcp> \
  --base-digest <base_digest-from-mcp> \
  --filtered-fields '<filtered_fields-from-mcp JSON>' \
  --receipt "$MAINT/<id>-proposed/create-receipt.json"
```

回执仅在 `status=pending-review` 且返回 `base_digest` 与本地 payload `base_digest` 回显一致时写入；任一不符即拒收（exit 1，不落回执）。

**Step 4（post-apply 验证）**：人工在 admin UI approve → apply 之后（Skill 外部动作），agent 调 MCP `maintenance_revision_get` 并把返回落盘为 `revision-get.json`，再验证：

```bash
uv run python -m scripts.maintenance_post_apply \
  --revision "$MAINT/<id>-proposed/revision-get.json" \
  --receipt "$MAINT/<id>-proposed/create-receipt.json" \
  --output "$MAINT/<id>-proposed/post-apply-verification.json"
```

仅当 `status=applied` 且 `post_snapshot_id` 非空、且回执指向同一 revision 时落验证产物。

**完成条件**：校验报告、diff 审阅、回执、post-apply 验证四件产物齐，且全程未发生 Skill 侧 approve/reject/apply。

## 质量门禁

1. Research Pack 与 Pattern Draft 遵守 `/opt/code/skill/references/docspec/DocSpec-通用文档质量规范.md` 和 `文档验收清单.md`。
2. Article JSON 只含 v1 契约字段，必填 `title/body/slug/category`；`body` 为 HTML。
3. `category` 只能为 `ai-trends`、`industry-insights`、`case-studies`、`community`。
4. `status` 省略或为 `draft`；任何其他状态、发布意图字段或未知字段均阻塞。
5. MCP 调用前重新校验 payload；写回执时再次核对 validation report、review record 和 source draft。
6. MCP token 只由 OpenCode MCP 配置管理；任何运行时文件均不得包含 token。
7. Maintenance payload 的 `proposed_fields` 不得含服务端禁改字段；MCP create 结果非 `pending-review` 或 `base_digest` 回显不一致时不得写回执；post-apply 非 `applied` 或 `post_snapshot_id` 为空时不得写验证产物。
8. 运行 `uv run pytest -q`，确认 receipt CLI 覆盖成功、非草稿状态和无效 artifact 路径；maintenance 用例覆盖校验器全分支与拒收路径。

## 失败模式

| 情况 | 处理 |
|---|---|
| 研究证据不足 | 停在 Research，列出缺口，不生成确定性主张 |
| Draft 未批准或 slug 未确认可用 | 停在 Validation，不调用 CMS |
| Article JSON 无效或 digest 漂移 | 重跑 validator，重新审阅变更后的 payload |
| MCP 连接或认证失败 | 不写回执；检查 OpenCode MCP server URL、backend 状态和 Bearer token 配置后重试 |
| MCP 未返回 article ID | 不写回执；保留输入和校验报告并排查 MCP 调用结果 |
| 回执路径不在 `publish-jobs/` | 阻塞，改用固定 runtime taxonomy |
| current/desired 无差异或只动了禁改字段 | 构建即失败（exit 1），不出 proposed.json |
| maintenance create 返回非 pending-review 或 base_digest 不一致 | 不写回执；排查快照来源后重建（快照可能已过期） |
| post-apply 时 revision 非 applied 或无 post_snapshot_id | 不写验证产物；等待人工 apply 完成后重新 get 验证 |

## 维护规则

- v1 契约变更必须同步 `scripts/contracts.py`、`templates/v1/`、`references/*-v1.md` 和测试；破坏兼容性的变更新建 v2，不覆盖 v1。
- lnkwebsite taxonomy 变更只能由 lnkwebsite 自身的变更流程决定；本 Skill 只在该变更落地后同步白名单。
- 仅影响本 Skill 的排障经验写入 `references/troubleshooting.md`；跨文档质量规则提升到 `/opt/code/skill/references/docspec/`。

## References

- `references/runtime-artifacts-v1.md`：运行时目录、交接条件和留存契约。
- `references/article-payload-v1.md`：Article JSON、校验报告、MCP tool 和回执契约。
- `references/troubleshooting.md`：digest、slug 和 MCP 连接排障。
