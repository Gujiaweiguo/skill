# Troubleshooting

## Digest mismatch

The payload changed after validation or review. Rerun `scripts.validate_article`, review the changed payload, and replace the review record with the new SHA-256. Do not edit digest fields manually.

## Slug conflict

Stop the import. Select an available slug through the existing CMS review process, update Article JSON, revalidate, and obtain a new approval record. The importer never updates an existing article.

## Non-draft CMS response

Treat the configured endpoint as unsafe or misconfigured. The importer rejects the response and writes no receipt. Correct the endpoint contract before retrying.

## Credential handling

Configure `CONTENT_CMS_TOKEN` in the process environment. Do not add a `.env` file, pass the token as a CLI argument, or paste it into a report. Error output names the missing variable but never prints its value.
