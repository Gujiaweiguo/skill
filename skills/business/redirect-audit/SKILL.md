---
name: redirect-audit
version: 0.1.0
status: planned
scope: lnkwebsite
---

# Redirect Audit

> **状态**：v0.1 contract skeleton。**不包含可执行 workflow**。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.8

## Purpose

对比 lnkwebsite redirects 表、`docs/seo/redirect-map.md` 文档、实际 nginx 配置 + 线上 curl 状态，识别 drift。**不自动创建/修改/启用/禁用任何 redirect**。

## Trigger Condition

- 新增 redirect
- 季度 SEO 审核
- `docs/seo/redirect-map.md` 与实际配置 drift

当前已知 drift：`gzshopex.com` 重定向到 `www.lanlnk.com`（应到 `lanlnk.cn`，归属未确认，见 `docs/qa/seo-checks.md`）。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| audit_scope | enum | 可选 | `db-only` / `nginx-only` / `online-only` / `cross-check`（默认 cross-check） |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| redirect-drift-report.json | `$REDIRECT_OUTPUT_BASE/audit/<date>.json` | DB vs 文档 vs nginx vs 线上 curl 全链路对比 |

**report 字段示例**：

```json
{
  "audit_date": "2026-07-24",
  "total_redirects_in_db": 5,
  "total_redirects_in_doc": 20,
  "drifts": [
    {
      "source_url": "gzshopex.com",
      "db_status": "missing",
      "doc_status": "pending-ownership-confirmation",
      "nginx_status": "302-to-www.lanlnk.com",
      "online_curl": "302",
      "drift_type": "ownership-confirmation-pending"
    }
  ]
}
```

## Allowed MCP Tools

| MCP 模块 | 工具 | 权限 |
|---|---|---|
| `redirects` | `redirect_list` / `redirect_get` | read only |
| 公开 URL | `curl` | read only |

## Forbidden Actions

- ❌ 自动创建 redirect（`redirect_create`）
- ❌ 自动修改 redirect（`redirect_update`）
- ❌ 自动启用 / 禁用 redirect
- ❌ 自动改 nginx vhost
- ❌ 自动改 `docs/seo/redirect-map.md`

## Human Review Gate

- SEO owner + 运维审阅 drift report
- 人工修复（如确认归属后手工改 nginx / 改 DB / 改文档）
- skill 不替 owner 决定归属或优先级

## Validation Criteria（pilot → validated）

- 1 次季度审核跑通
- 至少识别 1 个真实 drift（如 gzshopex.com）
- drift report 与人工审计结果一致

## Promotion Rule

```
planned → ready：明确 SEO owner + 至少 1 个已知 drift 待审计
ready → pilot：drift report 跑通 1 次
pilot → validated：3 次 drift report + ≥ 1 个真实 drift 识别并跟踪修复
validated → Phase 5：在 skill-portfolio.md 显式记录
```

## LangChat Productization Mapping

- 候选 capability_id：`redirect-drift-audit-v1`
- 映射目标：LangChat Capability Gateway adapter
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 与 seo-audit skill 边界明确
