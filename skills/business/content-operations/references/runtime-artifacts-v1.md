# Runtime Artifact Contract v1

Contract version: `1.0.0`

## Root

`CONTENT_OUTPUT_BASE` defaults to `/opt/code/docs/lanlnk/lnkwebsite/content`. Runtime artifacts are operational state outside the Skill repository and lnkwebsite repository.

## Taxonomy

| Directory | Owner | Required artifact |
|---|---|---|
| `research-packs/` | Research | `<content-id>.md` from `templates/v1/research-pack.md` |
| `drafts/` | Generation | `<content-id>.md` from `templates/v1/pattern-draft.md` |
| `review/` | Human review | `<content-id>.json` from `templates/v1/review-record.json` |
| `publish-jobs/` | Validation and Draft Import | `<slug>/article.json`, `validation-report.json`, `import-receipt.json` |
| `published/` | External human-controlled release process | Reserved snapshots; this Skill does not write here |
| `reports/` | Operations reporting | Optional run summaries that reference receipts |

Paths passed to the importer must resolve within the expected directory. Symlinks or `..` segments cannot be used to escape the runtime root.

## Handoff invariants

1. Research Pack precedes Pattern Draft.
2. Review record identifies the absolute source draft, exact payload SHA-256, approval decision, and completed slug availability check.
3. Validation report identifies the same payload SHA-256 and has `valid=true` with no issues.
4. Receipt is written only after the CMS returns `status=draft`.
5. No artifact contains endpoint credentials or tokens.

## Retention

Keep the source draft, review record, exact Article JSON, validation report, and receipt together for audit. Editing Article JSON invalidates both its validation report and review record because the SHA-256 changes.
