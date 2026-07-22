# Article Payload Contract v1

Contract version: `1.0.0`

## Fields

| Field | Required | Contract |
|---|---|---|
| `title` | yes | Non-empty string |
| `body` | yes | Non-empty HTML containing at least one element tag |
| `slug` | yes | Lowercase ASCII kebab-case: `^[a-z0-9]+(?:-[a-z0-9]+)*$` |
| `category` | yes | `ai-trends`, `industry-insights`, `case-studies`, or `community` |
| `summary` | no | Non-empty string when present |
| `source_name` | no | Non-empty string when present |
| `commentary` | no | Non-empty string when present |
| `status` | no | Only `draft`; defaults to `draft` for validation |

Unknown fields are rejected. Fields expressing publication intent, including `publish`, `published`, `publish_at`, `published_at`, `is_published`, and `publication_status`, are rejected explicitly before model validation.

## MCP tool

After deterministic validation succeeds, the agent calls MCP `article_create(title, body, slug, category, summary, source_name, commentary)` with the validated Article fields. Optional fields are omitted when absent. The validator-only `status` field is never passed to the tool. `article_create` always creates the Article with `status=draft` and returns its article ID and draft status.

The Skill scripts do not implement MCP transport. OpenCode connects to the lnkwebsite Streamable HTTP MCP server at `http://127.0.0.1:5580/mcp` with MCP Bearer authentication.

## Validation report

```json
{
  "contract_version": "1.0.0",
  "issues": [],
  "payload_sha256": "<64 lowercase hex characters>",
  "valid": true
}
```

Issues are sorted by field and code, and JSON keys are sorted. Revalidating identical bytes produces a byte-identical report.

## Import receipt

The receipt contains exactly `contract_version`, `source_draft`, `payload_sha256`, `cms_article_id`, `slug`, `category`, and `status`. It cannot contain the configured token.
