# GitHub Docs Adapter

## 认证

使用已配置的 `gh` CLI 或 SSH key。

验证：
```bash
gh auth status  # 确认登录状态
```

## 仓库

- **仓库**：`Gujiaweiguo/langchat-docs`
- **URL**：`git@github.com:Gujiaweiguo/langchat-docs.git`
- **可见性**：Public

## 流程

```bash
# 1. Clone 或 pull 最新
REPO_DIR="${GITHUB_DOCS_REPO:-/tmp/langchat-docs}"
if [ -d "$REPO_DIR/.git" ]; then
    cd "$REPO_DIR" && git pull
else
    git clone git@github.com:Gujiaweiguo/langchat-docs.git "$REPO_DIR"
fi

# 2. 写入文档
# 路径约定：docs/<category>/<slug>.md
# Front matter:
#   ---
#   title: <英文标题>
#   slug: <slug>
#   original_url: https://lanlnk.cn/insights/<category>/<slug>/
#   published_at: <date>
#   ---

# 3. 提交推送
cd "$REPO_DIR"
git add docs/
git commit -m "docs: add <slug>"
git push origin main
```

## 文件格式

```markdown
---
title: What is RAG (Retrieval-Augmented Generation)
slug: what-is-rag
original_url: https://lanlnk.cn/insights/ai-trends/what-is-rag/
published_at: 2026-07-22
---

[中文原文内容或英文翻译版本]
```

## 全自动

GitHub adapter 全自动执行，无需人工确认。原因：
- 内容已通过官网发布的人审环节
- GitHub 公开仓库的内容可以随时修改/回滚
- git 有完整的版本历史

## 错误处理

| 错误 | 处理 |
|------|------|
| git push 失败 | 先 pull --rebase 再 push |
| 权限错误 | 检查 SSH key 或 gh auth |
| 文件已存在 | 覆盖更新，git 会记录变更 |
