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

The CMS request contains only the Article create fields. The validator-only `status` field is never sent. The endpoint must return a JSON object containing `id` and `status`; additional Article response fields are allowed, but `status` must equal `draft`.

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

## Endpoint configuration

- `CONTENT_CMS_DRAFT_ENDPOINT`: complete HTTP(S) URL for the configured internal draft-creation adapter.
- `CONTENT_CMS_TOKEN`: bearer token injected into the process environment.

Both variables are runtime configuration. Do not place token values in shell history, templates, receipts, reports, or version control.
