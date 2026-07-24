---
name: geo-operations
version: 0.1.0
status: planned
scope: lnkwebsite
---

# GEO Operations

> **状态**：v0.1 contract skeleton。**不包含可执行 workflow**。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.4

## Purpose

读取 lnkwebsite geo MCP，对比 GEO profile 与 llms.txt 实际内容，识别 drift（profile 字段缺失 / llms.txt 内容陈旧 / capability 描述与 capability 页不一致）。**不自动修改任何 GEO 内容**。

## Trigger Condition

- 百度 PC 站验证完成（百度站长平台点【验证】通过）
- 需要维护 GEO profile
- llms.txt 内容陈旧（capability 页新增/修改后未同步）

当前状态：百度站长平台验证待用户操作（见 `lnkwebsite/docs/qa/seo-checks.md` 百度章节）。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| geo_profile_id | string | 可选 | 指定 profile；不指定则全量扫描 |
| baseline_date | date | 可选 | 对比的基线日期 |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| geo-drift-report.json | `$GEO_OUTPUT_BASE/drift/<date>.json` | profile 一致性 + llms.txt 时效性 + capability 一致性 |

## Allowed MCP Tools

| MCP 模块 | 工具 | 权限 |
|---|---|---|
| `geo` | 全部 read 工具 | read only |

## Forbidden Actions

- ❌ 自动修改 `llms.txt`
- ❌ 自动发布 GEO 内容
- ❌ 自动提交搜索引擎
- ❌ 自动改 GEO profile
- ❌ 自动调用 GSC / 百度站长 API（需用户手动）

## Human Review Gate

- 编辑审阅 drift report
- 编辑人工决定是否更新 GEO 内容
- 任何 GEO 内容变更 MUST 通过 OpenSpec change

## Validation Criteria（pilot → validated）

- 百度验证完成（用户在百度后台点【验证】通过）
- drift report 跑通 1 次
- 编辑认可报告价值（识别 ≥ 1 个真实 drift 或确认无 drift）

## Promotion Rule

```
planned → ready：百度验证完成 + 明确 GEO 维护任务
ready → pilot：drift report 跑通 1 次
pilot → validated：3 次 drift report + 至少识别 1 个真实 drift 并修复
validated → Phase 5：在 skill-portfolio.md 显式记录
```

## LangChat Productization Mapping

- 候选 capability_id：`geo-discoverability-audit-v1`
- 映射目标：LangChat Capability Gateway adapter
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 与 seo-audit skill 边界明确
