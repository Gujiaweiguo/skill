---
name: lead-operations
version: 0.1.0
status: planned
scope: lnkwebsite
---

# Lead Operations

> **状态**：v0.1 contract skeleton。**不包含可执行 workflow**。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.3

## Purpose

读取 lnkwebsite leads 表，对新线索做分类建议与跟进建议，生成可审计的 triage report。**不执行任何外发动作**（不邮件、不短信、不 IM、不自动改 status）。所有跟进由销售 owner 人工决定。

## Trigger Condition

- 业务方书面任命 lead 业务 owner
- 书面确定响应 SLA（建议：新线索 24h 内联系）
- 当前 status：`planned`，业务 owner 与 SLA 未确定前禁止进入 pilot

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| lead_id_range | list[int] | ✅ | 待 triage 的 lead ID 范围（**禁止包含 id 1「陈振发」和 id 2「ops-test」**）|
| triage_context | string | 可选 | 业务方提供的分类维度（行业 / 公司规模 / 需求类型） |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| lead-triage-report.json | `$LEAD_OUTPUT_BASE/triage/<date>-<lead-id-range>.json` | 分类建议 + 跟进建议 + 风险标记 + **不发外发消息** |

**report 字段示例**：

```json
{
  "lead_id": 3,
  "category_suggestion": "high-priority-commercial-real-estate",
  "follow_up_suggestion": "建议 24h 内电话联系，准备商业地产 AI 客服方案",
  "risk_flags": [],
  "auto_actions_taken": [],
  "human_review_required": true
}
```

## Allowed MCP Tools

| MCP 模块 | 工具 | 权限 |
|---|---|---|
| `leads` | `lead_list` / `lead_get` | read only |

**禁止任何 write 操作**（`lead_update` / `lead_status_change`）。

## Forbidden Actions

- ❌ 任何外发消息（邮件 / SMS / IM / webhook 通知）
- ❌ 自动改 lead status
- ❌ 自动分配销售
- ❌ 处理 lead id 1（陈振发，真实客户未处理）和 lead id 2（ops-test，测试数据）
- ❌ 把 lead 个人信息（phone / name）写入 triage report 之外的位置

## Human Review Gate

- 销售 owner 审阅 triage report
- 销售 owner 人工决定是否联系、何时联系、用什么话术
- skill 不替销售做任何决定

## Validation Criteria（pilot → validated）

- 业务 owner 书面任命
- SLA 文档化（24h / 48h 等）
- 5 条**新的**真实 lead（id > 2）跑过分类建议
- 销售 owner 认可 ≥ 80% 的分类建议合理

## Promotion Rule

```
planned → ready：业务 owner 任命 + SLA 文档化 + 至少 5 条新真实 lead 待 triage
ready → pilot：triage report 跑通 1 次 + 销售 owner 审阅认可
pilot → validated：5 条 lead 跑过 + 分类准确率 ≥ 80%
validated → Phase 5：在 skill-portfolio.md 显式记录 + 进入 LangChat 映射讨论
```

## LangChat Productization Mapping

- 候选 capability_id：`lead-triage-advisory-v1`
- 映射目标：LangChat Capability Gateway adapter
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 业务 owner 书面认可
- **特别说明**：lead-operations 的 LangChat 沉淀需要额外的合规审查（个人数据处理）
