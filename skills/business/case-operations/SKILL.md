---
name: case-operations
version: 0.2.0
status: ready
scope: lnkwebsite
description: |-
  把客户授权的案例素材转换为可审计、可验证的 lnkwebsite CMS case draft，仅创建 draft 不公开发布。复用 content-operations 的 case_payload / validate_case 校验逻辑（含 client_authorized fail-closed 与禁词检查）。触发场景：录入案例、案例草稿入库、客户案例上 CMS。与 content-operations 共享 case 处理 helper，未来可能提取为独立目录或保持共享。
compatibility: |-
  Requires Python 3.10+ and uv. Runtime scripts depend on the content-operations
  shared parser (loaded at runtime, no install needed). Case screening uses
  urllib (stdlib). Draft Import requires OpenCode MCP Streamable HTTP transport
  to the lnkwebsite MCP server at http://127.0.0.1:5580/mcp.
---

# Case Operations

> **状态**：v0.2 — **status=ready**（业务方书面同意 = opc 确认，一人公司）。pilot 基准案例：粤海天河城（screening Top 1）。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.2

## Purpose

把客户授权的案例素材转换为可审计、可验证的 lnkwebsite CMS case draft。此 skill 只创建 draft；公开发布属于独立的人工作业，不在本 skill 的命令、脚本或凭据范围内。

**与 content-operations skill 的关系**：content-operations 在 commit `c178e54`（2026-07-23）已加入 `scripts/case_payload.py` 与 `scripts/validate_case.py`，提供 case payload 校验逻辑（含 client_authorized fail-closed + 禁词检查）。本 skill 把 case 处理显式抽出为独立 contract；未来可能从 content-operations 提取为独立 skill 目录，或保持 helper 共享。

## Trigger Condition

- 客户书面授权的案例素材入库
- status 从 `ready` → `pilot` 的前置条件：pilot 基准案例 research-pack 完成 + 双签授权证据在档
- pilot 基准案例：粤海天河城（screening Top 1）

## 配置

```bash
export CASE_OUTPUT_BASE="${CASE_OUTPUT_BASE:-/opt/code/docs/lanlnk/lnkwebsite/content/cases}"

cd /opt/code/skill/skills/business/case-operations
uv sync --group dev
```

- `CASE_OUTPUT_BASE` 未设置时使用 `/opt/code/docs/lanlnk/lnkwebsite/content/cases`。
- 固定目录和文件契约见 `references/runtime-artifacts-v1.md`。
- Case 字段、禁词和错误契约见 `references/payload-v1.md`。

### MCP server 配置

OpenCode 必须配置一个 Streamable HTTP MCP server，连接 `http://127.0.0.1:5580/mcp`，并通过 `Authorization: Bearer <MCP token>` 请求头认证。Bearer token 由 OpenCode 的 MCP 配置管理，不传给 Skill 脚本，也不得写入模板、回执、日志或仓库文件。

Draft Import 由 agent 直接调用该 MCP server 的 `case_create`；Skill 脚本不实现 MCP 协议，也不发起 HTTP 请求。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| case-research-pack | markdown | ✅ | 含客户名、行业、problem/solution/outcome、testimonial、授权证据 |
| client_authorized | boolean | ✅ | MUST be `true`，否则 fail-closed |
| industry | enum | ✅ | 合法 CaseIndustry 取值 |
| client_name | string | ✅ | 客户显示名 |
| testimonial | string | 可选 | 客户口述/书面评价 |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| case-research-pack.md | `$CASE_OUTPUT_BASE/research-packs/<case-id>.md` | 证据来源 + 客户授权 |
| case-payload.json | `$CASE_OUTPUT_BASE/publish-jobs/<slug>/case-payload.json` | case 字段 + client_authorized |
| validation-report.json | `$CASE_OUTPUT_BASE/publish-jobs/<slug>/validation-report.json` | 禁词 + 字段完整性 + 授权检查 |
| import-receipt.json | `$CASE_OUTPUT_BASE/publish-jobs/<slug>/import-receipt.json` | MCP case_create 回执 |

## Workflow

### 1. Screen（可选：案例筛选）

**输入**：网站案例 API `https://lanlnk.cn/api/cases`。

**动作**：获取已发布案例，按字段完整度（80%）+ 行业优先级（20%）打分排序。

```bash
uv run python -m scripts.case_workflow screen \
  --output /tmp/case-screening-report.json
```

**输出**：`screening-report.json`（含打分排序 + Top 3 候选）。

**交接条件**：至少 1 个 published case；Top 候选有完整字段。

### 2. Validate（案例校验）

**输入**：Case payload JSON（含 `client_authorized: true`）。

**动作**：运行确定性校验器——字段完整性、授权 fail-closed、禁词检查、绝对化用语拦截、publish/delete 意图拦截。

```bash
uv run python -m scripts.case_workflow validate \
  fixtures/synthetic-fixture.json \
  --report /tmp/case-ops-run/validation-report.json
```

**交接条件**：报告 `valid=true`；无 error。

### 3. Generate（Artifact 生成）

**输入**：通过校验的 fixture payload。

**动作**：使用 synthetic runner 生成 4 个必需 artifact（research-pack / payload / validation-report / import-receipt），通过 mock MCP 创建 draft。

```bash
uv run python -m scripts.case_workflow generate \
  fixtures/synthetic-fixture.json \
  --output-dir /tmp/case-ops-run
```

**输出**：4 个 artifact 文件全部就位。

**交接条件**：4 个文件存在且非空；mock MCP 仅调用 `case_create`；无 forbidden calls。

### 4. Import（CMS Draft 创建）

**输入**：已校验的 case payload + 可用的 lnkwebsite MCP 连接。

**Step 1（Validation）**：在 MCP 调用前运行确定性校验（同 Phase 2）。

**Step 2（MCP call）**：agent 从已校验的 payload 读取字段，直接调用 MCP `case_create(payload)`。不传 `status`；该工具始终创建 `status=draft`。记录 MCP 返回的 case ID。

**Step 3（Receipt）**：使用 MCP 返回值写入回执：

```bash
uv run python -m scripts.case_workflow import \
  fixtures/synthetic-fixture.json \
  --mock \
  --receipt /tmp/case-ops-run/import-receipt.json
```

**输出**：MCP 创建的 CMS 草稿和 `import-receipt.json`。

**完成条件**：MCP `case_create` 返回 case ID，返回状态为 `draft`，且回执已写入。

### 失败模式

| 情况 | 处理 |
|---|---|
| 案例 API 不可达 | 不生成 screening report；检查网络后重试 |
| payload 无 `client_authorized: true` | fail-closed，拒绝处理 |
| 含禁词或绝对化用语 | 停在 Validate，列出具体 term 和 field |
| MCP 连接或认证失败 | 不写回执；检查 MCP server 状态和 Bearer token 配置后重试 |
| MCP 返回非 draft 状态 | 不写回执；保留输入和校验报告并排查 |
| artifact_dir 不在系统 temp 目录内 | fail-closed，拒绝写入 |

## Allowed MCP Tools

| MCP 模块 | 工具 | 权限 |
|---|---|---|
| `cases` | `case_list` / `case_get` | read |
| `cases` | `case_create` | write draft（强制 `status=draft`） |
| `cases` | `case_update` | write draft（仅未发布 case） |

## Forbidden Actions

- ❌ `case_publish` / `case_unpublish` — 任何发布动作
- ❌ 直接 SQL 操作 cases 表
- ❌ 处理无 `client_authorized=true` 的客户数据
- ❌ 修改已发布的 case（status=published）
- ❌ 修改 CaseIndustry enum 取值集合
- ❌ 批量导入

## Human Review Gate

- **gate 1**：业务方 + 法务双签确认客户授权
- **gate 2**：编辑审稿（内容质量 + 禁词）
- 两道 gate 全部 approved 才允许 MCP `case_create`

## Validation Criteria（pilot → validated）

- 1 个客户案例端到端跑通
- `client_authorized` fail-closed 验证（无授权时拒绝）
- 禁词检查（`解决方案` / `数字营销` / `新零售` / `新商业` / `新营销` / `新消费`）通过
- 字段完整性（slug / client_name / industry / problem / solution / outcome 全非空）
- 生成 4 个 artifact 全部就位

## Promotion Rule

```
planned → ready：✅ 已完成（业务方书面同意 = opc 确认，一人公司；pilot 基准 = 粤海天河城）
ready → pilot：pilot 基准案例的 research-pack 完成 + 双签授权证据在档
pilot → validated：1 次端到端跑通 + artifact 完整 + 人审通过
validated → Phase 5：在 skill-portfolio.md 显式记录 + 进入 LangChat 映射讨论
```

## Ready Condition Checklist

- [x] 可执行 workflow（`scripts/case_workflow.py`）：screen / validate / generate / import
- [x] 案例筛选脚本（`scripts/case_screening.py`）：从 API 获取 + 打分排序
- [x] Pilot 候选已选定：粤海天河城、广州城投、宝能商业（Top 3 from screening）
- [x] 测试覆盖：81 tests passing（含 validation + synthetic runner + screening + workflow CLI）
- [x] CLI 可运行：`uv run python -m scripts.case_workflow <command>`
- [x] Artifact 结构化输出：4 个 JSON/MD artifact 含 validation checks / draft status
- [x] 模板就位：`templates/v1/` 含 case-payload / research-pack / validation-report / import-receipt / review-record
- [x] References 文档：payload-v1.md / runtime-artifacts-v1.md / troubleshooting.md
- [x] 业务方书面同意（pilot 基准案例授权确认）— opc 确认（一人公司）；pilot 基准 = 粤海天河城

## Pilot Candidate Screening（pre-existing）

网站已发布 12 个案例，按字段完整度 + 行业优先级打分排序 Top 3：

| # | Client | Industry | Score | Notes |
|---|--------|----------|-------|-------|
| 1 | 粤海天河城 | shopping-center | 高 | 367 家店铺全渠道转型，字段完整 |
| 2 | 广州城投 | complex | 高 | 多项目统一会员体系，testimonial 有 |
| 3 | 宝能商业 | shopping-center | 高 | 六大购物中心的统一会员平台 |

> 以上案例已 **published**，本 skill 的工作是对新增授权案例创建 draft。已发布案例的 screening 仅作为 pilot 基准选择参考。

## Maintenance

- Case payload schema 变更必须同步 `scripts/validate.py`、`templates/v1/`、`references/payload-v1.md` 和测试。
- 禁词列表变更需同步 `content-operations/scripts/case_payload.py`（共享源）和本 skill 测试。
- 绝对化用语列表变更只需更新 `scripts/validate.py` 的 `ABSOLUTE_PHRASES` 和对应测试。
- 仅影响本 Skill 的排障经验写入 `references/troubleshooting.md`。

## LangChat Productization Mapping

- 候选 capability_id：`case-evidence-management-v1`
- 映射目标：LangChat Capability Gateway adapter（参考 `phase5-mapping-plan.md` §3）
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 证据矩阵对应行更新

## References

- `references/runtime-artifacts-v1.md`：运行时目录、交接条件和留存契约。
- `references/payload-v1.md`：Case payload、校验报告、MCP tool 和回执契约。
- `references/troubleshooting.md`：loader、fixture mode、MCP 连接排障。
