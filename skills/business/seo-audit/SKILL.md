---
name: seo-audit
version: 0.2.0
status: planned
scope: lnkwebsite
description: |-
  定期审计 lnkwebsite 的 SEO 健康度，覆盖 sitemap 完整性、canonical 一致性、structured data 校验、meta 唯一性、Open Graph 完整性与 robots.txt 配置六个维度，生成可审计的 drift report。不自动修复任何 drift，所有修正由人工执行。触发场景：SEO 审计、sitemap 检查、canonical 一致性、structured data 校验、meta 重复检测。审计结果可定期对比基线，追踪 SEO 健康度趋势变化。
compatibility: |-
  Requires Python 3.10+ and uv. Runtime scripts use only stdlib (re, json, subprocess, urllib).
  Output artifacts use SEO_OUTPUT_BASE (default /tmp/seo-audit).
---

# SEO Audit

> **状态**：v0.2 — 可执行 workflow 就绪，**status=planned**（GSC 数据 < 2 周 + SEO owner 未明确）。
> **Promotion Gate**：GSC 数据 ≥ 2 周 + 明确 SEO owner → ready。
> **生命周期登记**：见 `lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md` §2.5

## Purpose

定期审计 lnkwebsite 的 SEO 健康度（sitemap 完整性 + canonical 一致性 + structured data 校验 + meta 唯一性 + Open Graph + robots.txt），生成可审计的 drift report。**不自动修复任何 drift**。

## Trigger Condition

- GSC 有连续 2 周数据
- 出现 SEO drift（canonical 错误 / 重复 title / sitemap 缺失 / structured data 失效）
- 季度 SEO 审核

当前状态：GSC 验证已完成（2026-07-24），但数据 < 2 周。

## 配置

```bash
export SEO_OUTPUT_BASE="${SEO_OUTPUT_BASE:-/tmp/seo-audit}"

cd /opt/code/skill/skills/business/seo-audit
uv sync --group dev
```

- `SEO_OUTPUT_BASE` 未设置时使用 `/tmp/seo-audit`。
- 生产模式需要 `lanlnk.cn` 可访问（curl 检查页面 HTML）。
- 无外部依赖（仅使用 Python stdlib）。

## Inputs

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| audit_scope | enum | 可选 | `full` / `sitemap-only` / `canonical-only` / `schema-only`（默认 full） |
| baseline_date | date | 可选 | 对比基线 |
| pages | list[PageRecord] | 是 | 来自 fetch 或 fixture 的页面数据 |
| sitemap_url | str | 可选 | sitemap.xml URL |
| robots_url | str | 可选 | robots.txt URL |
| known_urls | list[str] | 可选 | 应在 sitemap 中出现的 URL 列表 |

## Outputs and Required Artifacts

| Artifact | 路径约定 | 内容 |
|---|---|---|
| seo-drift-report.json | `$SEO_OUTPUT_BASE/audit/<date>.json` | sitemap 完整性 + canonical 一致性 + schema 校验 + meta 唯一性 + OG + robots |

**report 字段示例**：

```json
{
  "audit_date": "2026-08-01",
  "audit_scope": "full",
  "site": "lanlnk.cn",
  "total_pages_checked": 7,
  "sitemap": {
    "url": "https://lanlnk.cn/sitemap.xml",
    "total_urls": 5,
    "reachable": true,
    "errors": []
  },
  "canonical": {
    "inconsistencies": []
  },
  "structured_data": {
    "validated_pages": ["https://lanlnk.cn/", "..."],
    "errors": []
  },
  "meta": {
    "duplicate_titles": [],
    "duplicate_descriptions": []
  },
  "robots": {
    "url": "https://lanlnk.cn/robots.txt",
    "reachable": true,
    "sitemap_refs": ["https://lanlnk.cn/sitemap.xml"]
  },
  "total_findings": 12,
  "findings": [
    {
      "page_url": "https://lanlnk.cn/broken",
      "issue_type": "missing_title",
      "severity": "critical",
      "description": "Page https://lanlnk.cn/broken has no <title> tag",
      "dimension": "meta"
    }
  ],
  "summary": {
    "total_pages": 7,
    "total_findings": 12,
    "severity_critical": 5,
    "severity_warning": 7,
    "dimension_meta": 8,
    "dimension_canonical": 1,
    "dimension_structured_data": 1,
    "dimension_og": 2
  }
}
```

## Workflow

### 1. Fetch

**输入**：站点 URL 列表 + sitemap.xml URL + robots.txt URL。

**动作**：通过 curl 或注入的 fetcher 抓取页面 HTML，解析 sitemap.xml 和 robots.txt。

**输出**：`list[PageRecord]`（含 title, description, canonical, h1_tags, og_*, json_ld_blocks, meta_robots）+ `SitemapData` + `RobotsData`。

**交接条件**：至少 1 个 PageRecord；每条记录 url 非空。

### 2. Audit

**输入**：PageRecord 列表 + audit_scope。

**动作**：根据 audit_scope 执行四维度审计：

| audit_scope | 检查维度 |
|---|---|
| `full`（默认） | sitemap + canonical + structured data + meta + OG + robots |
| `sitemap-only` | sitemap 完整性 |
| `canonical-only` | canonical 一致性 |
| `schema-only` | JSON-LD 校验 |

**Finding 类型**：

| issue_type | severity | dimension | 说明 |
|---|---|---|---|
| missing_title | critical | meta | 缺少 title 标签 |
| empty_title | critical | meta | title 为空 |
| title_too_long | warning | meta | title 超过 60 字符 |
| title_too_short | warning | meta | title 少于 10 字符 |
| duplicate_title | warning | meta | 多页使用相同 title |
| missing_description | critical | meta | 缺少 meta description |
| duplicate_description | warning | meta | 多页使用相同 description |
| description_too_long | warning | meta | description 超过 160 字符 |
| description_too_short | warning | meta | description 少于 50 字符 |
| missing_canonical | warning | canonical | 缺少 canonical 标签 |
| canonical_mismatch | critical | canonical | canonical 指向不同域名 |
| multiple_h1 | warning | meta | 多个 H1 标签 |
| missing_h1 | warning | meta | 缺少 H1 标签 |
| missing_json_ld | warning | structured_data | 缺少 JSON-LD 结构化数据 |
| invalid_json_ld | critical | structured_data | JSON-LD 格式无效 |
| missing_og_title | warning | og | 缺少 og:title |
| missing_og_description | warning | og | 缺少 og:description |
| missing_og_image | warning | og | 缺少 og:image |
| sitemap_unreachable | critical | sitemap | sitemap.xml 不可达 |
| sitemap_empty | critical | sitemap | sitemap.xml 无 URL |
| sitemap_missing_url | warning | sitemap | sitemap 缺少已知 URL |
| robots_unreachable | warning | robots | robots.txt 不可达 |
| robots_no_sitemap_ref | info | robots | robots.txt 未引用 sitemap |
| blocked_by_robots | critical | robots | 页面被 robots.txt 禁止 |

**输出**：`list[SEOFinding]`。

### 3. Report

**输入**：Audit 阶段的 findings + PageRecords + SitemapData + RobotsData。

**动作**：生成结构化 drift report JSON。

```bash
uv run python -m scripts.seo_audit_runner \
  --fixture fixtures/synthetic-fixture.json \
  --output "$SEO_OUTPUT_BASE/audit/$(date +%F).json"
```

**输出**：`seo-drift-report.json`（含 audit_date, findings, summary）。

**交接条件**：report 文件已写入；每条 finding 包含 page_url、issue_type、severity、description、dimension。

### 失败模式

| 情况 | 处理 |
|---|---|
| 页面不可达 | status_code=0；finding 标注 missing_* |
| sitemap.xml 不可达 | sitemap.reachable=false；finding 标注 sitemap_unreachable |
| robots.txt 不可达 | robots.reachable=false；finding 标注 robots_unreachable |
| HTML 解析异常 | 空 PageRecord；finding 标注 missing_title |
| JSON-LD 解码失败 | finding 标注 invalid_json_ld |
| 无页面记录 | report 中 total_pages_checked=0；不产生 finding |

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

## Ready Condition Checklist

- [x] 可执行 workflow（`scripts/seo_audit_runner.py`）：full / sitemap-only / canonical-only / schema-only
- [x] HTML 解析引擎：title, description, canonical, H1, OG tags, JSON-LD, meta robots
- [x] Sitemap.xml 解析与完整性检查
- [x] Robots.txt 解析与配置检查
- [x] JSON-LD 结构化数据校验（含 @graph / array 格式）
- [x] 测试覆盖：121 tests passing（含 validation + synthetic runner + SEO audit runner + CLI）
- [x] CLI 可运行：`uv run python -m scripts.seo_audit_runner --fixture ... --output ...`
- [x] Drift report 结构化输出：JSON 含 severity / issue_type / description / dimension / summary
- [ ] GSC 数据 ≥ 2 周（当前 < 2 周）
- [ ] 明确 SEO owner

## Maintenance

- Finding 分类规则变更必须同步 `_SEVERITY_MAP` 和对应审计方法
- 新增 audit_scope 必须更新 `VALID_AUDIT_SCOPES` 和对应测试
- 新增 HTML meta 标签解析需更新 `parse_html` 正则和对应测试
- 生产环境页面抓取需注入自定义 `FetcherProtocol` 实现

## LangChat Productization Mapping

- 候选 capability_id：`seo-health-audit-v1`
- 映射目标：LangChat Capability Gateway adapter
- 沉淀前置：本 skill MUST 处于 `validated` 状态 + 与 redirect-audit / geo-operations 边界明确
