# Troubleshooting (case-operations)

## Common issues

### content-ops loader fails to import

**Symptom**: `ModuleNotFoundError` or `ImportError` from `content_ops_loader.py`.

**Cause**: The content-operations skill directory is missing or the `scripts.case_payload` module cannot be found.

**Fix**:
1. Verify `/opt/code/skill/skills/business/content-operations/scripts/case_payload.py` exists.
2. Ensure case-operations is at the expected relative path (`../content-operations/` from case-operations root).
3. Run `uv sync --group dev` in the case-operations directory.

### Fixture mode validation error

**Symptom**: `fixture_requires_synthetic_mode` error.

**Cause**: A fixture payload (`fixture: true`) was processed without `execution_mode=synthetic-test`.

**Fix**: The caller (test or CLI) must pass `execution_mode=SYNTHETIC_TEST_MODE`. This is a safety measure — fixture data must never enter production.

### MCP case_create returns error

**Symptom**: MCP call to `case_create` fails.

**Check**:
1. MCP server is running at `http://127.0.0.1:5580/mcp`.
2. Bearer token is configured in OpenCode MCP settings.
3. The payload has `client_authorized: true`.
4. The payload does not contain forbidden terms or absolute marketing phrases.
5. No `publish`/`unpublish`/`delete` keys in the payload.

### Forbidden term in case content

**Symptom**: `forbidden_term` validation error.

**Cause**: One of the domain-forbidden terms appeared in a string field.

**Fix**: Replace `解决方案` with descriptive text like `提供XX系统` or `部署XX平台`. Replace `数字营销` with specific channel description. Avoid all `新XX` marketing buzzwords.

### Absolute marketing phrase detected

**Symptom**: `absolute_marketing_term` validation error.

**Cause**: A superlative phrase like `最领先`, `唯一`, `行业第一` was detected.

**Fix**: Rewrite using factual, verifiable language. Instead of `行业最领先`, use specific metrics or qualifications.

### Synthetic runner writes outside temp dir

**Symptom**: `ArtifactDirError: artifact_dir must resolve inside ...`

**Cause**: `artifact_dir` resolves outside the system temp directory.

**Fix**: Use a path under the system temp dir. This is a security measure — synthetic test artifacts must not pollute production paths.
