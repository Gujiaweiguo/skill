---
name: comment-moderation
version: 0.1.0
status: planned
scope: lnkwebsite
---

# Comment Moderation

> **状态**：v0.1 contract skeleton。**不包含可执行 workflow**。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.6

## Purpose

读取 lnkwebsite comments 表中 `status=pending` 的评论，做风险标记与审核建议，生成 triage report。**不执行任何 approve / reject / delete 动作**。所有审核决定由审核员人工做出。

## Trigger Condition

- 有真实评论审核量（≥ 10 条待审）
- 当前 status：`planned`，无真实评论量

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| status_filter | enum | 可选 | 默认 `pending` |
| article_id_filter | int | 可选 | 限定某文章 |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| comment-triage-report.json | `$COMMENT_OUTPUT_BASE/triage/<date>.json` | 风险标记 + 审核建议 + **不执行任何动作** |

**report 字段示例**：

```json
{
  "comment_id": 5,
  "risk_level": "low",
  "risk_flags": [],
  "moderation_suggestion": "approve",
  "auto_actions_taken": [],
  "human_review_required": true
}
```

## Allowed MCP Tools

| MCP 模块 | 工具 | 权限 |
|---|---|---|
| `comments` | `comment_list` / `comment_get` | read only |

**禁止任何 write 操作**（`comment_approve` / `comment_reject` / `comment_delete`）。

## Forbidden Actions

- ❌ 自动 approve / reject / delete 评论
- ❌ 自动回复评论者
- ❌ 自动 ban 用户
- ❌ 自动改评论 status
- ❌ 把评论者个人信息写入 triage report 之外

## Human Review Gate

- 审核员逐条审阅
- 审核员人工决定（approve / reject / delete）
- skill 仅提供建议，不替审核员做决定

## Validation Criteria（pilot → validated）

- 真实评论 ≥ 10 条
- 风险标记准确率 ≥ 80%
- 审核员认可（建议合理 + 不漏标高风险）

## Promotion Rule

```
planned → ready：真实评论 ≥ 10 条 + 审核员书面任命
ready → pilot：triage report 跑通 1 次
pilot → validated：10 条评论跑过 + 准确率 ≥ 80%
validated → Phase 5：在 skill-portfolio.md 显式记录
```

## LangChat Productization Mapping

- 候选 capability_id：`comment-moderation-advisory-v1`
- 映射目标：LangChat Capability Gateway adapter
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 合规审查（评论者个人信息处理）
