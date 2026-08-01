# Case Payload Contract v0.1

Contract version: `0.1.0`

## Fields

| Field | Required | Contract |
|---|---|---|
| `slug` | yes | Lowercase ASCII kebab-case: `^[a-z0-9]+(?:-[a-z0-9]+)*$` |
| `client_name` | yes | Non-empty string |
| `industry` | yes | Enum: `commercial-real-estate`, `office`, `shopping-center`, `property`, `park`, `community`, `complex` |
| `problem` | yes | Non-empty string |
| `solution` | yes | Non-empty string |
| `outcome` | yes | Non-empty string |
| `client_authorized` | yes | MUST be `true` (fail-closed) |
| `testimonial` | no | Non-empty string when present |
| `image` | no | Non-empty string when present |
| `seo_title` | no | Non-empty string when present |
| `seo_description` | no | Non-empty string when present |
| `product` | no | Non-empty string when present |
| `status` | no | Only `draft`; defaults to `draft` for validation |

Unknown fields are rejected. Fields expressing publication intent (`publish`, `published`, `case_publish`, `case_unpublish`, `case_delete`) are rejected explicitly.

## Extension fields (case-operations only)

| Field | Scope | Content |
|---|---|---|
| `fixture` | case-operations only | `true` for synthetic test data. Must NOT be combined with production execution. |

`execution_mode` is a caller-provided keyword argument, never a payload field. If found in the payload, validation fails.

## Forbidden terms (domain)

The following terms are rejected in any string field: `解决方案`, `数字营销`, `新零售`, `新商业`, `新营销`, `新消费`.

## Absolute marketing phrases

The following superlative phrases are rejected: `最领先`, `最优秀`, `最大`, `最小`, `最好`, `最差`, `最强`, `最弱`, `最优`, `最先进`, `最具`, `最完善`, `最专业`, `最权威`, `最丰富`, `最全面`, `首个`, `首家`, `首屈一指`, `唯一`, `独家`, `无与伦比`, `遥遥领先`, `行业第一`, `全国第一`, `全球第一`.

Bare `最` characters in neutral context (e.g. `最近`, `最后`) are allowed — only specific multi-character phrases are blocked.

## MCP tool

After deterministic validation succeeds, the agent calls MCP `case_create(payload)` with the validated case fields. The tool always creates the case with `status=draft` and returns its case ID and draft status.

The Skill scripts do not implement MCP transport. OpenCode connects to the lnkwebsite Streamable HTTP MCP server at `http://127.0.0.1:5580/mcp` with MCP Bearer authentication.

## Shared validation

Core case payload validation (fields, forbidden terms, slug pattern, industry enum) delegates to `content-operations/scripts/case_payload.py` via `scripts/content_ops_loader.py`. Case-operations adds:

- Absolute marketing phrase rejection
- `publish`/`unpublish`/`delete` intent interception
- Fixture mode enforcement
