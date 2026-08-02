# juejin-publish

Publish Markdown articles to 掘金 (juejin.cn) using the content creation API.

## When to Use

- Publishing technical articles to 掘金 for SEO backlink building
- Cross-posting content from lanlnk.cn insights to 掘金
- Any request to "发掘金" / "publish to juejin"

## Prerequisites

- **Cookie**: The user's 掘金 `sessionid` cookie stored in `JUEJIN_SESSION_ID` env var.
- Verify cookie before publishing:
  ```bash
  curl -s 'https://api.juejin.cn/user_api/v1/user/get' \
    -H "Cookie: sessionid=$JUEJIN_SESSION_ID" \
    -H 'User-Agent: Mozilla/5.0'
  ```
  Success: `err_no: 0` with user data.

## Workflow

### Step 1: Prepare Article

1. Source content from lanlnk.cn articles or write new content.
2. Adapt tone for 掘金: more conversational, add code examples, use Markdown.
3. Ensure 文末 has原文链接: `> 原文链接：https://lanlnk.cn/insights/...`
4. Determine category and tags (see maps below).

### Step 2: Create Draft (ALWAYS draft first)

```bash
curl -s -X POST 'https://api.juejin.cn/content_api/v1/article/publish' \
  -H "Cookie: sessionid=$JUEJIN_SESSION_ID" \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "<title>",
    "content": "<markdown content>",
    "category_id": "<category_id>",
    "tag_ids": ["<tag_id>", ...],
    "brief": "<summary>",
    "edit_type": 10,
    "theme_type": 1,
    "draft": 1
  }'
```

- `"draft": 1` creates a draft.
- `"draft": 0` publishes immediately.
- `edit_type: 10` = Markdown mode.

### Step 3: Publish

1. Show user the draft URL: `https://juejin.cn/editor/drafts/<article_id>`
2. After user confirms, publish with `"draft": 0`.

## Category Map

| Category | ID |
|----------|-----|
| 人工智能 | 6809637773955495949 |
| 后端 | 6809637767543259144 |
| 前端 | 6809637769959178254 |
| 开发工具 | 6809637771511071 |
| 阅读 | 6809637767445133325 |
| 其他 | 6809637772904953870 |

## Tag Discovery

```bash
curl -s -X POST 'https://api.juejin.cn/tag_api/v1/query_tag_list' \
  -H "Cookie: sessionid=$JUEJIN_SESSION_ID" \
  -H 'Content-Type: application/json' \
  -d '{"key_word": "AI"}'
```

Common tags for AI content:
- AI: `6icy9i`
- 人工智能: `6o97p3`
- 大模型: `73wy6m`
- RAG: `753qxx`

## Conventions

- **ALWAYS create as draft first**, show user, then publish after confirmation.
- Never publish without showing the user the final content.
- Insert `> 原文链接：https://lanlnk.cn/...` at the end of every cross-posted article.
- Rate limit: wait 2 seconds between API calls.
- Cookie expiry: if API returns auth error, ask user for new sessionid.

## Error Handling

| Error | Action |
|-------|--------|
| Auth error (401) | Cookie expired — ask user for new sessionid |
| Content too long (413) | Split or trim |
| Network timeout | Retry once with 10s timeout |

## Notes

- 掘金 recommends 800+ characters.
- Articles with code blocks and structured headings get better engagement.
- Best posting time: weekday evenings 19:00-22:00 CST.
