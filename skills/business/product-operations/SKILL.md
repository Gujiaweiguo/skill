---
name: product-operations
version: 0.1.0
status: planned
scope: lnkwebsite
---

# Product Operations

> **状态**：v0.1 contract skeleton。**不包含可执行 workflow**。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.7

## Purpose

把产品 PRD / capability 文档转换为 lnkwebsite CMS product draft。**只创建 draft**，公开发布属于独立人工作业。

**与 content-operations skill 的关系**：content-operations 在 commit `c178e54`（2026-07-23）已加入 `scripts/product_payload.py` 与 `scripts/validate_product.py`，提供 product payload 校验逻辑（含 brand-guardrail + AI Vision MVP 检查）。本 skill 把 product 处理显式抽出为独立 contract；未来可能从 content-operations 提取或保持 helper 共享。

## Trigger Condition

- 有产品 PRD 到 capability 内容的高频迭代（月度 ≥ 2 次）
- 新增 capability 页（如新增 LangChat AI XX 能力）

当前 status：`planned`，无高频迭代需求。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| product-research-pack | markdown | ✅ | 含 PRD 来源、能力定义、MVP vs Roadmap 区分 |
| product_type | enum | ✅ | 合法 ProductType 取值 |
| slug | string | ✅ | URL-friendly（如 `ai-customer-service`） |
| ai_vision_mvp_only | boolean | 可选 | slug 含 mallsense/vision 时强制 true |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| product-research-pack.md | `$PRODUCT_OUTPUT_BASE/research-packs/<slug>.md` | PRD 来源 + 能力定义 |
| product-payload.json | `$PRODUCT_OUTPUT_BASE/publish-jobs/<slug>/product.json` | product 字段 |
| validation-report.json | `$PRODUCT_OUTPUT_BASE/publish-jobs/<slug>/validation-report.json` | 禁词 + AI Vision MVP + 字段完整性 |
| import-receipt.json | `$PRODUCT_OUTPUT_BASE/publish-jobs/<slug>/import-receipt.json` | MCP product_create 回执 |

## Allowed MCP Tools

| MCP 模块 | 工具 | 权限 |
|---|---|---|
| `products` | `product_list` / `product_get` | read |
| `products` | `product_create` | write draft（强制 `status=draft`） |
| `products` | `product_update` | write draft（仅未发布 product） |

## Forbidden Actions

- ❌ `product_publish` / `product_unpublish`
- ❌ 直接 SQL 操作 products 表
- ❌ 修改公开 capability 页面（绕过 draft 流程）
- ❌ 修改 ProductType enum 取值集合
- ❌ 在 AI Vision capability 里声明非 MVP 能力（`精准客流` / `热区分析` 等 roadmap 项）
- ❌ 批量导入

## Human Review Gate

- **gate 1**：产品 owner 确认 PRD 来源准确
- **gate 2**：编辑审稿（内容质量 + 禁词 + AI Vision MVP 边界）
- 两道 gate 全部 approved 才允许 MCP `product_create`

## Validation Criteria（pilot → validated）

- 1 个 capability 页端到端跑通
- 字段完整性（slug / title / product_type / description 全非空）
- 禁词检查通过
- AI Vision MVP 校验通过（mallsense-ai 类 slug 只声明 `通道拥堵` / `火灾烟雾` / `地面脏污`）

## Promotion Rule

```
planned → ready：明确产品 owner + 至少 1 个 PRD 待转换
ready → pilot：1 个 capability 页端到端跑通
pilot → validated：3 次 product draft 创建 + 字段/禁词/MVP 全部通过
validated → Phase 5：在 skill-portfolio.md 显式记录
```

## LangChat Productization Mapping

- 候选 capability_id：`product-content-stewardship-v1`
- 映射目标：LangChat Capability Gateway adapter
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 与 case-operations 边界明确
