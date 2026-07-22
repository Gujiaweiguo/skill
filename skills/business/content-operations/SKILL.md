---
name: content-operations
version: "1.0.0"
description: |-
  蓝联创新网站内容运营 Skill。将有证据支撑的选题按 Research、Generation、Validation、Draft Import
  四个阶段转成 lnkwebsite CMS 草稿，保留研究包、Pattern Draft、审阅记录、Article JSON、校验报告和导入回执。
  触发场景："生成官网文章草稿"、"校验 Article JSON"、"把已审批文章导入 CMS 草稿"、
  "为 lnkwebsite 做内容运营"。仅处理 lnkwebsite 现有栏目，不负责公开发布、栏目扩展、排期自动化或批量导入。
compatibility: |-
  Requires Python 3.10+ and uv. Runtime scripts use only the Python standard library.
  Runtime artifacts use CONTENT_OUTPUT_BASE (default /opt/code/docs/lanlnk/lnkwebsite/content).
  Draft Import requires CONTENT_CMS_DRAFT_ENDPOINT and CONTENT_CMS_TOKEN in the environment.
---

# Content Operations

## 目标与边界

把可追溯研究证据转换为可审阅、可验证、可审计的 lnkwebsite CMS 草稿。此 Skill 只创建草稿；公开发布属于独立的人工作业，不在本 Skill 的命令、脚本或凭据范围内。

适用：单篇官网 Article 的研究、起草、审阅、确定性校验和草稿导入。

不适用：修改 lnkwebsite 代码或 taxonomy、创建新栏目、批量迁移、定时任务、公开发布、修改 MCP/API 权限或保存凭据。

## 配置

```bash
export CONTENT_OUTPUT_BASE="${CONTENT_OUTPUT_BASE:-/opt/code/docs/lanlnk/lnkwebsite/content}"
export CONTENT_CMS_DRAFT_ENDPOINT="https://configured-internal-endpoint.example/article-create"
export CONTENT_CMS_TOKEN="<injected-at-runtime>"

cd /opt/code/skill/skills/business/content-operations
uv sync --group dev
```

- `CONTENT_OUTPUT_BASE` 未设置时使用 `/opt/code/docs/lanlnk/lnkwebsite/content`。
- endpoint 可以记录在部署配置中；token 只能通过环境注入，不得写入模板、回执、日志或仓库文件。
- 固定目录和文件契约见 `references/runtime-artifacts-v1.md`。
- Article 字段、栏目和错误契约见 `references/article-payload-v1.md`。

## 阶段

### 1. Research

**输入**：选题、受众、选定 content pattern、可引用的一手或可靠二手来源。

**动作**：使用 `templates/v1/research-pack.md` 记录主张、证据、来源位置、证据强度、缺口和禁止外推项。遵守 `/opt/code/skill/references/docspec/`，不得把推断写成事实。

**输出**：`$CONTENT_OUTPUT_BASE/research-packs/<content-id>.md`。

**交接条件**：每个核心主张有来源；缺口已明确标注；已选定 content pattern。未满足时不得进入 Generation。

### 2. Generation

**输入**：通过交接条件的 Research Pack、选定 content pattern、品牌与事实约束。

**动作**：用 `templates/v1/pattern-draft.md` 生成 Markdown Pattern Draft。正文只能使用 Research Pack 支撑的事实，未决信息保留为待确认项。

**输出**：`$CONTENT_OUTPUT_BASE/drafts/<content-id>.md`。

**交接条件**：Research Pack 路径和 pattern 已写入 Draft；正文完整；事实、链接和品牌口径自检完成。随后生成 Article JSON，提交人工审阅。

### 3. Validation

**输入**：Pattern Draft、人工审阅记录、`$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/article.json`。

**动作**：审阅记录使用 `templates/v1/review-record.json`，且必须为 `decision=approved`、`slug_available=true`。运行确定性校验器：

```bash
uv run python -m scripts.validate_article \
  "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/article.json" \
  --report "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/validation-report.json"
```

**输出**：同一 `publish-jobs/<slug>/` 下的 Article JSON 和 `validation-report.json`。

**交接条件**：命令退出码为 0；报告 `valid=true`；报告 SHA-256 与 Article JSON 当前字节一致；审阅记录批准同一 source draft 和 payload digest。任一失败时不得发起 CMS 请求。

### 4. Draft Import

**输入**：已批准 source draft、匹配的 review record、Article JSON、有效 validation report、环境中的 endpoint/token。

**动作**：调用唯一的草稿导入命令：

```bash
uv run python -m scripts.import_draft \
  "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/article.json" \
  --source-draft "$CONTENT_OUTPUT_BASE/drafts/<content-id>.md" \
  --review-record "$CONTENT_OUTPUT_BASE/review/<content-id>.json" \
  --validation-report "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/validation-report.json" \
  --receipt "$CONTENT_OUTPUT_BASE/publish-jobs/<slug>/import-receipt.json"
```

**输出**：CMS 草稿和 `import-receipt.json`。回执记录 source draft、payload SHA-256、CMS article id、slug、category、status，不记录 token。

**完成条件**：CMS 响应明确为 `status=draft`，且回执已原子写入。非草稿响应会失败且不生成回执。

## 质量门禁

1. Research Pack 与 Pattern Draft 遵守 `/opt/code/skill/references/docspec/DocSpec-通用文档质量规范.md` 和 `文档验收清单.md`。
2. Article JSON 只含 v1 契约字段，必填 `title/body/slug/category`；`body` 为 HTML。
3. `category` 只能为 `ai-trends`、`industry-insights`、`case-studies`、`community`。
4. `status` 省略或为 `draft`；任何其他状态、发布意图字段或未知字段均阻塞。
5. 导入前重新校验 payload，并核对 validation report、review record 和 source draft。
6. endpoint 和 token 只从环境读取；任何运行时文件均不得包含 token。
7. 运行 `uv run pytest -q`，确认本地 HTTP test double 覆盖无请求失败路径、草稿响应检查和回执安全。

## 失败模式

| 情况 | 处理 |
|---|---|
| 研究证据不足 | 停在 Research，列出缺口，不生成确定性主张 |
| Draft 未批准或 slug 未确认可用 | 停在 Validation，不调用 CMS |
| Article JSON 无效或 digest 漂移 | 重跑 validator，重新审阅变更后的 payload |
| endpoint/token 未配置 | 阻塞并提示缺失的环境变量，不打印 token |
| CMS 请求失败或返回非草稿 | 不写回执；保留输入和校验报告供重试 |
| 回执路径不在 `publish-jobs/` | 阻塞，改用固定 runtime taxonomy |

## 维护规则

- v1 契约变更必须同步 `scripts/contracts.py`、`templates/v1/`、`references/*-v1.md` 和测试；破坏兼容性的变更新建 v2，不覆盖 v1。
- lnkwebsite taxonomy 变更只能由 lnkwebsite 自身的变更流程决定；本 Skill 只在该变更落地后同步白名单。
- 仅影响本 Skill 的排障经验写入 `references/troubleshooting.md`；跨文档质量规则提升到 `/opt/code/skill/references/docspec/`。

## References

- `references/runtime-artifacts-v1.md`：运行时目录、交接条件和留存契约。
- `references/article-payload-v1.md`：Article JSON、校验报告、CMS 响应和回执契约。
- `references/troubleshooting.md`：digest、slug、CMS 响应和凭据排障。
