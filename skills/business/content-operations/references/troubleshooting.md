# Troubleshooting

## Digest mismatch

The payload changed after validation or review. Rerun `scripts.validate_article`, review the changed payload, and replace the review record with the new SHA-256. Do not edit digest fields manually.

## Slug conflict

Stop the import. Select an available slug through the existing CMS review process, update Article JSON, revalidate, and obtain a new approval record. The importer never updates an existing article.

## MCP connection failure

Confirm that the lnkwebsite backend is running, OpenCode's MCP server URL is `http://127.0.0.1:5580/mcp`, and its MCP Bearer token is configured. Do not run `scripts.write_receipt` unless `article_create` returned an article ID. A failed MCP call creates no receipt, so the validated artifacts remain available for retry.
