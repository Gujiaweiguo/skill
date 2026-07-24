---
name: seo-audit
version: 0.1.0
status: planned
scope: lnkwebsite
---

# SEO Audit

> **状态**：v0.1 contract skeleton。**不包含可执行 workflow**。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.5

## Purpose

定期审计 lnkwebsite 的 SEO 健康度（sitemap 完整性 + canonical 一致性 + structured data 校验 + meta 唯一性），生成可审计的 drift report。**不自动修复任何 drift**。

## Trigger Condition

- GSC 有连续 2 周数据
- 出现 SEO drift（canonical 错误 / 重复 title / sitemap 缺失 / structured data 失效）
- 季度 SEO 审核

当前状态：GSC 验证已完成（2026-07-24），但数据 < 2 周。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| audit_scope | enum | 可选 | `full` / `sitemap-only` / `canonical-only` / `schema-only`（默认 full） |
| baseline_date | date | 可选 | 对比基线 |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| seo-drift-report.json | `$SEO_OUTPUT_BASE/audit/<date>.json` | sitemap 完整性 + canonical 一致性 + schema 校验 + meta 唯一性 |

**report 字段示例**：

```json
{
  "audit_date": "2026-07-24",
  "sitemap": {
    "total_urls": 53,
    "missing_urls": [],
    "broken_urls": []
  },
  "canonical": {
    "inconsistencies": []
  },
  "structured_data": {
    "validated_pages": ["homepage", "capability-pages"],
    "errors": []
  },
  "meta": {
    "duplicate_titles": [],
    "duplicate_descriptions": []
  }
}
```

## Allowed MCP Tools

| MCP 模块 | 工具 | 权限 |
|---|---|---|
| 公开 URL | `curl` | read only |
| `redirects` | `redirect_list` / `redirect_get` | read only |

**不调用 GSC API / 百度站长 API**（需用户手动查 GSC 后台）。

## Forbidden Actions

- ❌ 自动改 nginx
- ❌ 自动提交搜索引擎
- ❌ 自动改 sitemap / robots.txt / canonical
- ❌ 自动改 meta tags / structured data
- ❌ 自动改 SEOHead.astro 组件
- ❌ 调用 GSC / 百度站长 API（凭据不进 skill）

## Human Review Gate

- SEO owner 审阅 drift report
- 人工修复 drift（如发现 canonical 错误 → 人工改 SEOHead.astro）
- skill 不替 owner 决定优先级

## Validation Criteria（pilot → validated）

- GSC 数据 ≥ 2 周
- drift report 跑通 3 次
- 至少识别 1 个真实 drift（如 gzshopex.com 重定向错误 / canonical 不一致 / sitemap 缺失 URL）

## Promotion Rule

```
planned → ready：GSC 数据 ≥ 2 周 + 明确 SEO owner
ready → pilot：drift report 跑通 1 次
pilot → validated：3 次 drift report + ≥ 1 个真实 drift 识别并修复
validated → Phase 5：在 skill-portfolio.md 显式记录
```

## LangChat Productization Mapping

- 候选 capability_id：`seo-health-audit-v1`
- 映射目标：LangChat Capability Gateway adapter
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 与 redirect-audit / geo-operations 边界明确
