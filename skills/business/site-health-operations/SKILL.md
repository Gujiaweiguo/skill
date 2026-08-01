---
name: site-health-operations
version: 0.2.0
status: ready
scope: lnkwebsite
description: |-
  定期生成 lnkwebsite 站点健康基线报告，覆盖 HTTP 端点状态/响应时间、SSL 证书到期、redirect chain、4 个 systemd service 状态、磁盘/内存/swap 使用五个维度。仅生成报告，不自动修复、不自动重启、不改任何配置。触发场景：站点健康检查、服务状态基线、endpoint 响应时间监控、SSL 证书到期预警。报告可定期对比基线，追踪站点健康趋势，辅助容量规划与故障预警。所有指标输出结构化 JSON 便于趋势追踪与告警对接。
compatibility: |-
  Requires Python 3.10+ and uv. Runtime scripts use only stdlib (subprocess, json, ssl, socket).
  Output artifacts use HEALTH_OUTPUT_BASE (default /tmp/site-health).
---

# Site Health Operations

> **状态**：v0.2 — **status=ready**（运维 owner = opc，一人公司）。技术基建完成，可执行 workflow 就绪。uptime 监控部署为 pilot 验证内容，不影响 ready。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.9

## Purpose

定期生成 lnkwebsite 站点健康基线报告（HTTP 端点状态/响应时间 + SSL 证书到期 + redirect chain + 4 个 systemd service 状态 + 磁盘/内存/swap）。**仅生成报告，不自动修复、不自动重启、不改任何配置**。

## Trigger Condition

- 月度健康基线审计
- SSL 证书到期检查（季度）
- 发生首次被动发现故障
- 决定恢复 uptime 监控（P0-2 待业务方决策）

当前 status：`ready`，运维 owner = opc（一人公司）。uptime 监控部署为 pilot 验证内容。

## 配置

```bash
export HEALTH_OUTPUT_BASE="${HEALTH_OUTPUT_BASE:-/tmp/site-health}"

cd /opt/code/skill/skills/business/site-health-operations
uv sync --group dev
```

- `HEALTH_OUTPUT_BASE` 未设置时使用 `/tmp/site-health`。
- 生产模式需要目标站点可访问 + `systemctl` 可执行。
- 无外部依赖（仅使用 Python stdlib: subprocess, ssl, socket, json）。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| check_scope | enum | 可选 | `quick` / `full`（默认 full） |
| thresholds | json | 可选 | 告警阈值配置（默认读取 `config/thresholds.json`） |
| sites | list[str] | 可选 | 检查站点列表（默认 4 个 lanlnk.cn 子域） |
| services | list[str] | 可选 | systemd 服务名列表（默认 4 个 lnkwebsite 服务） |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| health-baseline-report.json | `$HEALTH_OUTPUT_BASE/baseline/<date>.json` | endpoints + SSL + services + resources + findings |

**report 字段示例**：

```json
{
  "check_date": "2026-08-01",
  "check_scope": "full",
  "endpoints": [
    {
      "url": "https://lanlnk.cn",
      "http_code": 200,
      "response_time_ms": 125.0,
      "final_url": "https://lanlnk.cn",
      "redirect_chain": [],
      "ssl_enabled": true,
      "reachable": true
    }
  ],
  "ssl_certs": [
    {
      "domain": "lanlnk.cn",
      "issuer": {"commonName": "Let's Encrypt R3"},
      "not_after": "Sep 23 00:00:00 2026 GMT",
      "days_remaining": 53
    }
  ],
  "services": [
    {
      "name": "lnkwebsite-backend",
      "status": "active",
      "main_pid": 2050626,
      "uptime_hours": 9.0
    }
  ],
  "resources": {
    "disk_used_percent": 27.0,
    "memory_used_percent": 60.0,
    "swap_used_percent": 49.0
  },
  "findings": [
    {
      "check": "ssl_expiry",
      "target": "lanlnk.cn",
      "severity": "warning",
      "message": "SSL certificate for lanlnk.cn expires in 20 days",
      "current_value": "20 days",
      "threshold": "≤30 days"
    }
  ],
  "summary": {
    "total_endpoints": 4,
    "total_ssl_certs": 4,
    "total_services": 4,
    "total_findings": 1,
    "severity_warning": 1
  }
}
```

## Workflow

### 1. Endpoint Check

**输入**：站点 URL 列表 + `config/thresholds.json` 中每站点配置。

**动作**：通过 `curl` 检查每个 URL 的 HTTP 状态码、响应时间、redirect chain。

**输出**：`list[EndpointResult]`（url, http_code, response_time_ms, redirect_chain, reachable）。

**告警规则**：

| 检查项 | severity | 触发条件 |
|---|---|---|
| endpoint_reachable | critical | 站点不可达 |
| http_status | critical (5xx) / warning (4xx) | 状态码 ≠ expected_http_code |
| response_time | warning | response_time_ms > max_response_time_ms |
| redirect_target | warning | redirect 目标 ≠ expected_redirect |
| https_enabled | warning | 非 HTTPS |

### 2. SSL Certificate Check

**输入**：站点域名列表 + SSL 阈值配置。

**动作**：通过 Python `ssl` 模块检查证书有效期。

**输出**：`list[SSLResult]`（domain, issuer, not_after, days_remaining）。

**告警规则**：

| 检查项 | severity | 触发条件 |
|---|---|---|
| ssl_expiry | critical | days_remaining ≤ critical_days_remaining (默认 7) |
| ssl_expiry | warning | days_remaining ≤ warn_days_remaining (默认 30) |
| ssl_certificate | critical | SSL 检查失败（无法连接/无证书） |

### 3. Service Check

**输入**：systemd 服务名列表 + 预期状态配置。

**动作**：通过 `systemctl show` 获取服务 ActiveState、MainPID、启动时间。

**输出**：`list[ServiceResult]`（name, status, main_pid, uptime_hours）。

**告警规则**：

| 检查项 | severity | 触发条件 |
|---|---|---|
| service_status | critical | status = failed / inactive |
| service_status | warning | status ≠ expected_status（非 failed/inactive） |

### 4. Resource Check

**输入**：资源阈值配置。

**动作**：通过 `df` 和 `/proc/meminfo` 获取磁盘/内存/swap 使用率。

**输出**：`ResourceResult`（disk_used_percent, memory_used_percent, swap_used_percent）。

**告警规则**：

| 检查项 | severity | 触发条件 |
|---|---|---|
| resource_disk | critical / warning | disk ≥ critical (90%) / warn (80%) |
| resource_memory | critical / warning | memory ≥ critical (90%) / warn (75%) |
| resource_swap | critical / warning | swap ≥ critical (80%) / warn (60%) |

### 5. Report

**输入**：以上 4 阶段的所有结果 + findings。

**动作**：生成结构化 JSON 健康基线报告。

```bash
# Fixture 模式（synthetic test）
uv run python -m scripts.health_check \
  --fixture fixtures/synthetic-fixture.json \
  --thresholds config/thresholds.json \
  --output "$HEALTH_OUTPUT_BASE/baseline/$(date +%F).json"

# Live 模式（真实检查）
uv run python -m scripts.health_check \
  --thresholds config/thresholds.json \
  --live \
  --output "$HEALTH_OUTPUT_BASE/baseline/$(date +%F).json"
```

**输出**：`health-baseline-report.json`（含 endpoints, ssl_certs, services, resources, findings, summary）。

**交接条件**：report 文件已写入；每条 finding 包含 check, target, severity, message。

### 失败模式

| 情况 | 处理 |
|---|---|
| curl 超时 | 标记 unreachable=true，记录 error，继续其他检查 |
| SSL 连接失败 | 标记 error，severity=critical finding |
| systemctl 不可用 | 记录 error，severity=warning finding |
| /proc/meminfo 不可读 | 资源检查字段置 0，不产生 finding |
| 无 finding | 正常情况，report 中 total_findings=0 |

## Alert Thresholds

阈值配置文件：`config/thresholds.json`

```json
{
  "endpoints": {
    "lanlnk.cn": {
      "expected_https": true,
      "expected_redirect": "https://lanlnk.cn",
      "max_response_time_ms": 3000,
      "expected_http_code": 200
    }
  },
  "ssl": {
    "warn_days_remaining": 30,
    "critical_days_remaining": 7
  },
  "resources": {
    "disk_warn_percent": 80,
    "disk_critical_percent": 90,
    "memory_warn_percent": 75,
    "memory_critical_percent": 90,
    "swap_warn_percent": 60,
    "swap_critical_percent": 80
  },
  "services": {
    "lnkwebsite-backend": {"expected_status": "active"}
  }
}
```

## Allowed MCP Tools

| 工具 | 权限 |
|---|---|
| `curl`（公开端点） | read only |
| `ssl.create_default_context`（SSL 证书检查） | read only |
| `systemctl show`（服务状态） | read only |
| `df` / `/proc/meminfo` | read only |

## Forbidden Actions

- ❌ 自动重启服务（`systemctl restart`）
- ❌ 自动改 nginx vhost
- ❌ 自动改 systemd unit
- ❌ 自动改 cron
- ❌ 自动改 iptables
- ❌ 自动改 DB schema 或数据
- ❌ 自动发送告警（需要先有 P0-1 通知通道）

## Human Review Gate

- 运维审阅 baseline report
- 运维人工决定是否干预（如 swap 持续 > 80% → 决定升级内存）
- skill 不替运维做任何决定

## Validation Criteria（pilot → validated）

- 1 次月度基线审计跑通
- 与 P0-2 uptime 监控决策对齐（如选择 SaaS 监控，本 skill 作为内部 baseline 互补）
- 至少识别 1 个真实 drift（如 swap 持续增长趋势）

## Promotion Rule

```
planned → ready：✅ 已完成（运维 owner = opc，一人公司）
ready → pilot：baseline report 跑通 1 次
pilot → validated：3 次 baseline report + 与外部监控数据一致 + uptime 监控部署
validated → Phase 5：在 skill-portfolio.md 显式记录（但 site-health 通常不沉淀为 LangChat capability，而是作为运维元数据来源）
```

## Ready Condition Checklist

- [x] 可执行 workflow（`scripts/health_check.py`）：endpoint / SSL / service / resource 四维度
- [x] 告警阈值配置（`config/thresholds.json`）：每站点可配置 HTTP 码/响应时间/redirect
- [x] 测试覆盖：120 tests passing（含 validation + synthetic runner + health check + CLI）
- [x] CLI 可运行：`uv run python -m scripts.health_check --fixture ... --output ...`
- [x] 结构化输出：JSON 含 endpoints / ssl_certs / services / resources / findings / summary
- [x] 业务方决定恢复 uptime 监控策略（P0-2 决策）— owner = opc 确认
- [x] 明确运维 owner（书面确认）— opc（一人公司）

**当前 status：`ready`** — 技术基建已完成，运维 owner = opc（一人公司）。uptime 监控部署为 pilot 验证内容，不影响 ready。

## Maintenance

- 新增站点：更新 `config/thresholds.json` 的 `endpoints` 节
- 阈值变更：直接编辑 `config/thresholds.json` 对应字段
- 新增检查维度：在 `HealthChecker.run()` 添加新 check_* 参数 + 对应 evaluate 函数
- 生产环境使用：注入自定义 checker（`OnlineCheckerProtocol` / `SSLCheckerProtocol` / `ServiceCheckerProtocol` / `ResourceCheckerProtocol`）

## LangChat Productization Mapping

- 候选 capability_id：**N/A**（site-health 通常不沉淀为 LangChat 数字员工能力）
- 替代价值：作为 LangChat 平台运维元数据来源（如 LangChat 自己的 AuditEventModel 可以参考本 skill 的 baseline 结构）
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 业务方书面认可其作为运维 SoT
