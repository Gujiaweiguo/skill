# Runtime Artifact Contract v0.1

Contract version: `0.1.0`

## Root

`CASE_OUTPUT_BASE` defaults to `/opt/code/docs/lanlnk/lnkwebsite/content/cases`. Runtime artifacts are operational state outside the Skill repository and lnkwebsite repository.

## Taxonomy

| Directory | Owner | Required artifact |
|---|---|---|
| `research-packs/` | Research | `<case-id>.md` from `templates/v1/case-research-pack.md` |
| `publish-jobs/` | Validation and Import | `<slug>/case-payload.json`, `validation-report.json`, `import-receipt.json` |
| `reports/` | Operations | Optional screening reports and run summaries |

Paths passed to scripts must resolve within the expected directory. Symlinks or `..` segments cannot be used to escape the runtime root.

## Required Artifacts (4 per case)

| # | Artifact | Path under `publish-jobs/<slug>/` | Content |
|---|---|---|---|
| 1 | case-research-pack.md | `research-packs/<case-id>.md` | 证据来源 + 客户授权 |
| 2 | case-payload.json | `publish-jobs/<slug>/case-payload.json` | Case 字段 + client_authorized |
| 3 | validation-report.json | `publish-jobs/<slug>/validation-report.json` | 禁词 + 字段完整性 + 授权检查 |
| 4 | import-receipt.json | `publish-jobs/<slug>/import-receipt.json` | MCP case_create 回执 |

## Handoff invariants

1. Research Pack precedes payload generation.
2. Review record (gate 1 + gate 2) must both be approved before MCP call.
3. Validation report must have `valid=true` with no errors.
4. Receipt is written only after the CMS returns `status=draft`.
5. No artifact contains endpoint credentials or tokens.

## Retention

Keep the research pack, case payload, validation report, and receipt together for audit. Editing case-payload.json invalidates its validation report because the content changes.
