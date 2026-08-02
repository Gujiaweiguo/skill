# 掘金 Adapter

## 认证

使用 `JUEJIN_SESSION_ID` 环境变量（掘金 sessionid cookie）。

验证：
```bash
curl -s 'https://api.juejin.cn/user_api/v1/user/get' \
  -H "Cookie: sessionid=$JUEJIN_SESSION_ID" \
  -H 'User-Agent: Mozilla/5.0'
# err_no: 0 = 有效
```

## API 端点

| 操作 | 方法 | URL |
|------|------|-----|
| 创建草稿 | POST | `https://api.juejin.cn/content_api/v1/article_draft/create` |
| 更新草稿 | POST | `https://api.juejin.cn/content_api/v1/article_draft/update` |
| 删除草稿 | POST | `https://api.juejin.cn/content_api/v1/article_draft/delete` |
| 发布 | POST | `https://api.juejin.cn/content_api/v1/article/publish` |
| 搜索标签 | POST | `https://api.juejin.cn/tag_api/v1/query_tag_list` |

## 关键发现

### content vs mark_content

掘金 API 有两个内容字段：

- `content` — HTML 渲染内容（创建时返回 0 bytes，不可靠）
- `mark_content` — **Markdown 源内容（实际存储字段）**

**必须用 `mark_content` 存储内容。**

### 发布 API 被 WAF 拦截

`article/publish` 端点持续返回 `参数错误`，即使所有必填字段正确。
原因：掘金前端 WAF（`lf-waf-jschallenge`）需要浏览器执行 JS challenge 生成 token。

**结论：只能创建草稿，发布需人工点击。**

## 分类映射

| 分类 | ID |
|------|-----|
| 人工智能 | 6809637773955495949 |
| 后端 | 6809637767543259144 |
| 前端 | 6809637769959178254 |
| 开发工具 | 6809637771511071 |

## 标签映射

| 标签 | tag_id | 搜索关键词 |
|------|--------|-----------|
| 人工智能 | 6809640642101116936 | "人工智能" |
| LLM | 7257794499869573175 | "LLM" |
| AIGC | 7197380506562871333 | "AIGC" |
| NLP | 6809640930740535303 | "NLP" |
| ChatGPT | 7197380216015028281 | "ChatGPT" |

搜索新标签：
```bash
curl -s -X POST 'https://api.juejin.cn/tag_api/v1/query_tag_list' \
  -H "Cookie: sessionid=$JUEJIN_SESSION_ID" \
  -H 'Content-Type: application/json' \
  -d '{"key_word": "关键词"}'
```

## 完整流程

```python
import requests, os

sid = os.environ["JUEJIN_SESSION_ID"]

# 1. 创建草稿
resp = requests.post(
    'https://api.juejin.cn/content_api/v1/article_draft/create',
    headers={
        'Cookie': f'sessionid={sid}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0',
    },
    json={
        "category_id": "6809637773955495949",
        "tag_ids": ["6809640642101116936", "7257794499869573175"],
        "title": "文章标题",
        "content": "",
        "brief": "摘要",
        "edit_type": 10,
        "theme_type": 1,
        "cover_image": "",
        "column_ids": [],
        "link_url": "",
    },
)
draft_id = resp.json()['data']['id']

# 2. 更新内容（mark_content！）
resp2 = requests.post(
    'https://api.juejin.cn/content_api/v1/article_draft/update',
    headers={
        'Cookie': f'sessionid={sid}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0',
    },
    json={
        "id": draft_id,
        "category_id": "6809637773955495949",
        "tag_ids": ["6809640642101116936", "7257794499869573175"],
        "title": "文章标题",
        "mark_content": markdown_content,
        "brief": "摘要",
        "edit_type": 10,
        "theme_type": 1,
        "cover_image": "",
        "column_ids": [],
        "link_url": "",
    },
)

# 3. 返回草稿 URL
print(f"https://juejin.cn/editor/drafts/{draft_id}")
```

## 错误处理

| err_no | 含义 | 处理 |
|--------|------|------|
| 0 | 成功 | — |
| 2 | 参数错误 | 检查字段名和类型（tag_ids 必须是 string） |
| 401 | 未授权 | cookie 过期，需重新获取 |

## 内容适配规范

官网 → 掘金的改写原则：

1. **标题**：更吸引眼球，加"避坑"/"实战"/"指南"等词
2. **开头**：先说结论（"先说人话：..."），别铺垫
3. **代码**：加可运行的伪代码或示例
4. **表格**：保留，掘金支持 Markdown 表格
5. **文末**：加 `> 原文链接：https://lanlnk.cn/...`
6. **语气**：技术博客口语化，别像官网那样正式
