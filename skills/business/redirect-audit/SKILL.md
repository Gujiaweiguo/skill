---
name: redirect-audit
version: 0.2.0
status: ready
scope: lnkwebsite
description: |-
  对比 lnkwebsite redirects 表、docs/seo/redirect-map.md 文档、实际 nginx 配置与线上 curl 状态四方数据源，识别 drift（表/文档/nginx/线上不一致）。不自动创建、修改、启用或禁用任何 redirect，仅生成 drift report 供人工核查。触发场景：redirect 漂移检查、301 审计、redirect 表与 nginx 一致性校验。
compatibility: |-
  Requires Python 3.10+ and uv. Runtime scripts use only stdlib (subprocess, json, re).
  Output artifacts use REDIRECT_OUTPUT_BASE (default /tmp/redirect-audit).
---

# Redirect Audit

> **状态**：v0.2 — 可执行 workflow 就绪，**status=ready**（技术基建完成，已知 drift gzshopex.com 待审计）。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.8

## Purpose

对比 lnkwebsite redirects 表、`docs/seo/redirect-map.md` 文档、实际 nginx 配置 + 线上 curl 状态，识别 drift。**不自动创建/修改/启用/禁用任何 redirect**。

## Trigger Condition

- 新增 redirect
- 季度 SEO 审核
- `docs/seo/redirect-map.md` 与实际配置 drift

当前已知 drift：`gzshopex.com` 重定向到 `www.lanlnk.com`（应到 `lanlnk.cn`，归属未确认，见 `docs/qa/seo-checks.md`）。

## 配置

```bash
export REDIRECT_OUTPUT_BASE="${REDIRECT_OUTPUT_BASE:-/tmp/redirect-audit}"

cd /opt/code/skill/skills/business/redirect-audit
uv sync --group dev
```

- `REDIRECT_OUTPUT_BASE` 未设置时使用 `/tmp/redirect-audit`。
- 生产模式需要 lnkwebsite MCP server 可用（`redirect_list` / `redirect_get`）。
- 无外部依赖（仅使用 Python stdlib）。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| audit_scope | enum | 可选 | `db-only` / `nginx-only` / `online-only` / `cross-check`（默认 cross-check） |
| records | list[RedirectRecord] | 是 | 来自 DB / 文档 / curl 的 redirect 数据 |
| check_online | bool | 可选 | 是否实时检查 URL（默认 false，使用 records 中的 online_status_code） |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| redirect-drift-report.json | `$REDIRECT_OUTPUT_BASE/audit/<date>.json` | DB vs 文档 vs nginx vs 线上 curl 全链路对比 |

**report 字段示例**：

```json
{
  "audit_date": "2026-08-01",
  "audit_scope": "cross-check",
  "total_checked": 5,
  "total_drifts": 3,
  "drifts": [
    {
      "source_url": "gzshopex.com",
      "drift_type": "ownership-confirmation-pending",
      "severity": "critical",
      "description": "Redirect for gzshopex.com has pending ownership confirmation...",
      "db_status": "missing",
      "doc_status": "pending-ownership-confirmation",
      "nginx_status": "302-to-www.lanlnk.com",
      "online_status_code": 302
    }
  ],
  "summary": {
    "total_records": 5,
    "total_drifts": 3,
    "severity_critical": 1,
    "severity_warning": 2
  }
}
```

## Workflow

### 1. Collect

**输入**：lnkwebsite MCP `redirect_list`、`docs/seo/redirect-map.md`、线上 curl。

**动作**：从 DB 获取 redirect 列表，从文档解析 redirect 状态，（可选）curl 检查线上 HTTP 状态。

**输出**：`list[RedirectRecord]`（source_url + db_status + doc_status + nginx_status + online_status_code）。

**交接条件**：至少 1 条记录；每条记录 source_url 非空。

### 2. Cross-check

**输入**：Collect 阶段的 records + audit_scope。

**动作**：根据 audit_scope 识别 drift：

- `cross-check`（默认）：对比 DB / 文档 / nginx / 线上四方数据源
- `db-only`：仅检查 DB 一致性
- `nginx-only`：仅检查 nginx 配置
- `online-only`：实时 curl 比对预期状态

**Drift 类型**：

| drift_type | severity | 说明 |
|---|---|---|
| ownership-confirmation-pending | critical | 归属未确认 |
| doc-db-inconsistency | warning | 文档与 DB 不一致 |
| stale-doc-entry | warning | 文档未更新 |
| db-missing-but-online | critical | DB 缺失但线上存在 |
| disabled-but-online | critical | DB 已禁用但线上仍跳转 |
| offline-but-active | critical | DB 标记活跃但线上不可达 |
| unexpected-target | critical | 跳转目标不符合预期 |

**输出**：`list[DriftFinding]`。

### 3. Report

**输入**：Cross-check 阶段的 findings + records。

**动作**：生成结构化 drift report JSON。

```bash
uv run python -m scripts.audit_runner \
  --fixture fixtures/synthetic-fixture.json \
  --output "$REDIRECT_OUTPUT_BASE/audit/$(date +%F).json"
```

**输出**：`redirect-drift-report.json`（含 audit_date、drifts、summary）。

**交接条件**：report 文件已写入；每条 drift 包含 source_url、drift_type、severity、description。

### 失败模式

| 情况 | 处理 |
|---|---|
| MCP 连接失败 | 不生成 report；检查 MCP server 状态后重试 |
| curl 超时 | 记录 online_status_code=0；在 report 中标注 unreachable |
| 文档不存在 | doc_status 全部标记为 missing；继续审计 |
| 无 redirect 记录 | report 中 total_checked=0；不产生 drift |

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
planned → ready：可执行 workflow 就绪 + 至少 1 个已知 drift 待审计
ready → pilot：drift report 在生产环境跑通 1 次
pilot → validated：3 次 drift report + ≥ 1 个真实 drift 识别并跟踪修复
validated → Phase 5：在 skill-portfolio.md 显式记录
```

## Ready Condition Checklist

- [x] 可执行 workflow（`scripts/audit_runner.py`）：cross-check / db-only / nginx-only / online-only
- [x] 已知 drift：`gzshopex.com` 302 → www.lanlnk.com（应为 lanlnk.cn，归属未确认）
- [x] 测试覆盖：106 tests passing（含 validation + synthetic runner + audit runner + CLI）
- [x] CLI 可运行：`uv run python -m scripts.audit_runner --fixture ... --output ...`
- [x] Drift report 结构化输出：JSON 含 severity / drift_type / description / summary
- [ ] SEO owner 书面确认（portfolio 下一轮 review 时确认）

## Maintenance

- drift 分类规则变更必须同步 `_SEVERITY_MAP` 和 `_classify_drift` 函数
- 新增 audit_scope 必须更新 `VALID_AUDIT_SCOPES` 和对应测试
- 生产环境 URL 检查需注入自定义 `OnlineCheckerProtocol` 实现

## LangChat Productization Mapping

- 候选 capability_id：`redirect-drift-audit-v1`
- 映射目标：LangChat Capability Gateway adapter
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 与 seo-audit skill 边界明确
