---
name: content-distribution
version: "0.1.0"
status: ready
scope: lnkwebsite
description: |-
  将官网已发布文章适配并分发到外部渠道（掘金、GitHub Docs、知乎），建立 SEO 外链网络。
  输入：content-operations 产出的已发布 article（article_id 或 URL）。
  输出：各渠道分发结果清单。
  触发场景："分发到三平台"、"发外链"、"掘金草稿"、"同步 GitHub docs"。
  边界：不做选题、研究、写作（content-operations 负责）；不做官网发布（content-operations 负责）。
  HITL：掘金创建草稿后需人工点发布；知乎导出 HTML 供人工粘贴；GitHub 全自动。
---

# Content Distribution

## 设计理念

```
Agent（编排）
  │
  ├─ content-operations → 官网（原创源）
  │
  └─ content-distribution → 外部渠道（外链网络）
       ├─ juejin adapter（中文高权重外链）
       ├─ github adapter（技术文档同步）
       └─ zhihu adapter（导出待粘贴）
```

每个渠道是一个独立 adapter，自动化程度如实反映：

| 渠道 | 自动化 | 方式 |
|------|--------|------|
| 掘金 | 草稿自动，发布手动 | API 创建草稿 → 通知人工发布 |
| GitHub Docs | 全自动 | git commit + push |
| 知乎 | 内容导出 | 生成适配 HTML → 人工粘贴 |

## 输入契约

```
输入：article_id（官网已发布的文章 ID）
     或 article URL（如 /insights/ai-trends/what-is-rag/）

获取方式：
  curl ${API_BASE}/articles/${slug}  # 从 CMS API 拉取
```

## 工作流

### Phase 1: 读取源文章

```bash
# 从 CMS API 获取已发布文章
curl -s "${API_BASE}/articles/${slug}" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
# 输出: title, summary, body, category, slug, published_at
"
```

### Phase 2: 渠道适配

每个 adapter 负责自己的内容转换：

- **掘金**：口语化改写、加代码示例、文末加原文链接
- **GitHub**：英文标题 + Markdown 原文 + front matter
- **知乎**：HTML 格式、适配知乎编辑器

### Phase 3: 分发执行

按渠道调用对应 adapter，收集结果。

### Phase 4: 输出分发清单

```
分发结果：
  官网：https://lanlnk.cn/insights/ai-trends/xxx/  ✅
  掘金：https://juejin.cn/editor/drafts/xxx          📝 待发布
  GitHub：https://github.com/Gujiaweiguo/langchat-docs/commit/xxx  ✅
  知乎：/tmp/dist/zhihu-xxx.html                      📋 待粘贴
```

## Adapter 规范

每个 adapter 位于 `adapters/<channel>/`，包含：

- `ADAPTER.md` — 渠道特定的 API 调用方式、认证、限制
- 脚本（如需要）放在 `scripts/` 下

### 掘金 Adapter

**认证**：`JUEJIN_SESSION_ID` 环境变量（用户 cookie）

**流程**：
1. 适配内容（掘金风格）
2. `article_draft/create` → 创建草稿（返回 draft_id）
3. `article_draft/update` → 写入 mark_content
4. 返回草稿 URL，等待人工发布

**已知限制**：
- publish API 被 WAF 拦截，只能创建草稿
- cookie 有时效，过期需重新获取
- 详见 `adapters/juejin/ADAPTER.md`

### GitHub Docs Adapter

**认证**：SSH key（已配置）或 `gh` CLI

**仓库**：`Gujiaweiguo/langchat-docs`（公开）

**流程**：
1. 转换为英文标题 + Markdown
2. 写入仓库对应目录
3. `git add && git commit && git push`

**路径约定**：`docs/<category>/<slug>.md`

### 知乎 Adapter

**状态**：导出待粘贴（无 API）

**流程**：
1. 生成适配知乎编辑器的 HTML
2. 写入 `/tmp/dist/zhihu-<slug>.html`
3. 输出提示：请手动复制到知乎

## 配置

```bash
# 掘金
export JUEJIN_SESSION_ID="<cookie>"

# GitHub
# 使用已配置的 gh CLI / SSH key

# CMS API（读取源文章）
export CMS_API_BASE="${CMS_API_BASE:-http://127.0.0.1:5580/api}"

# GitHub docs 仓库路径
export GITHUB_DOCS_REPO="${GITHUB_DOCS_REPO:-/tmp/langchat-docs}"
```

## HITL 治理

遵循 LangChat Build · Ship · Operate 理念：

```
DRAFT（草稿/导出）
  ↓ 人工审批
PUBLISHED（已发布）
```

- 掘金：草稿自动创建 → 人审 → 发布
- GitHub：自动推送（公开仓库，内容已过官网人审）
- 知乎：导出 → 人工粘贴发布

## 使用示例

```
用户："把 what-is-rag 分发到三个平台"

Agent:
  1. 读取官网文章（API）
  2. juejin adapter → 创建草稿 → 返回草稿 URL
  3. github adapter → git push → 返回 commit URL
  4. zhihu adapter → 导出 HTML → 返回文件路径
  5. 输出分发清单
```
