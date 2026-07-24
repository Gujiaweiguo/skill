---
name: case-operations
version: 0.1.0
status: ready
scope: lnkwebsite
---

# Case Operations

> **状态**：v0.1 contract skeleton，**status=ready**（pilot 基准待选定）。**不包含可执行 workflow**。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.2

## Purpose

把客户授权的案例素材转换为可审计、可验证的 lnkwebsite CMS case draft。此 skill 只创建 draft；公开发布属于独立的人工作业，不在本 skill 的命令、脚本或凭据范围内。

**与 content-operations skill 的关系**：content-operations 在 commit `c178e54`（2026-07-23）已加入 `scripts/case_payload.py` 与 `scripts/validate_case.py`，提供 case payload 校验逻辑（含 client_authorized fail-closed + 禁词检查）。本 skill 把 case 处理显式抽出为独立 contract；未来可能从 content-operations 提取为独立 skill 目录，或保持 helper 共享。

## Trigger Condition

- 客户书面授权的案例素材入库
- status 从 `planned` → `ready` 的前置条件：选定 1 个明确客户授权的案例作为 pilot 基准

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
| case-payload.json | `$CASE_OUTPUT_BASE/publish-jobs/<slug>/case.json` | case 字段 + client_authorized |
| validation-report.json | `$CASE_OUTPUT_BASE/publish-jobs/<slug>/validation-report.json` | 禁词 + 字段完整性 + 授权检查 |
| import-receipt.json | `$CASE_OUTPUT_BASE/publish-jobs/<slug>/import-receipt.json` | MCP case_create 回执 |

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
planned → ready：选定 pilot 基准案例 + 业务方书面同意
ready → pilot：pilot 基准案例的 research-pack 完成 + 双签授权证据在档
pilot → validated：1 次端到端跑通 + artifact 完整 + 人审通过
validated → Phase 5：在 skill-portfolio.md 显式记录 + 进入 LangChat 映射讨论
```

## LangChat Productization Mapping

- 候选 capability_id：`case-evidence-management-v1`
- 映射目标：LangChat Capability Gateway adapter（参考 `phase5-mapping-plan.md` §3）
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 证据矩阵对应行更新
