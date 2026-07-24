---
name: site-health-operations
version: 0.1.0
status: planned
scope: lnkwebsite
---

# Site Health Operations

> **状态**：v0.1 contract skeleton。**不包含可执行 workflow**。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.9

## Purpose

定期生成 lnkwebsite 站点健康基线报告（4 个 systemd service 状态 + 关键 endpoint 响应时间 + DB 连接 + 磁盘/内存/swap）。**仅生成报告，不自动修复、不自动重启、不改任何配置**。

## Trigger Condition

- 决定恢复 uptime 监控（P0-2 待业务方决策）
- 发生首次被动发现故障
- 月度健康基线审计

当前 status：`planned`，无 uptime 监控，无月度基线审计。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| check_scope | enum | 可选 | `quick` / `full`（默认 quick） |
| baseline_date | date | 可选 | 对比基线 |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| health-baseline-report.json | `$HEALTH_OUTPUT_BASE/baseline/<date>.json` | service 状态 + endpoint 响应 + 资源占用 |

**report 字段示例**：

```json
{
  "check_date": "2026-07-24",
  "services": {
    "lnkwebsite-backend": {"status": "active", "uptime_hours": 9, "main_pid": 2050626},
    "lnkwebsite-frontend": {"status": "active", "uptime_hours": 12, "main_pid": 2279198},
    "lnkwebsite-admin": {"status": "active", "uptime_hours": 8, "main_pid": 2250388},
    "lnkwebsite-h5": {"status": "active", "uptime_hours": 19, "main_pid": 2050629}
  },
  "endpoints": {
    "homepage": {"http_code": 200, "response_time_ms": 125},
    "api_health": {"http_code": 200, "body": "{\"status\":\"ok\"}"},
    "sitemap_xml": {"http_code": 200, "url_count": 53}
  },
  "resources": {
    "disk_used_percent": 27,
    "memory_used_percent": 60,
    "swap_used_percent": 49
  },
  "drifts_detected": [],
  "auto_actions_taken": []
}
```

## Allowed MCP Tools

| 工具 | 权限 |
|---|---|
| `curl`（公开端点） | read only |
| `systemctl status` | read only |
| `docker ps` / `docker exec ... psql` | read only |
| `df` / `free` / `top -bn1` | read only |

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
planned → ready：业务方决定恢复监控 + 明确运维 owner
ready → pilot：baseline report 跑通 1 次
pilot → validated：3 次 baseline report + 与外部监控数据一致
validated → Phase 5：在 skill-portfolio.md 显式记录（但 site-health 通常不沉淀为 LangChat capability，而是作为运维元数据来源）
```

## LangChat Productization Mapping

- 候选 capability_id：**N/A**（site-health 通常不沉淀为 LangChat 数字员工能力）
- 替代价值：作为 LangChat 平台运维元数据来源（如 LangChat 自己的 AuditEventModel 可以参考本 skill 的 baseline 结构）
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 业务方书面认可其作为运维 SoT
