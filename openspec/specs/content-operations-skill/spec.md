# content-operations-skill Specification

## Purpose
TBD - created by archiving change add-content-operations-skill. Update Purpose after archive.
## Requirements
### Requirement: Content Operations Skill defines governed stages
The Content Operations Skill SHALL define separate Research, Generation, Validation, and Draft Import stages. Each stage SHALL state its required inputs, produced artifacts, and handoff conditions.

#### Scenario: Generation follows research evidence
- **WHEN** an operator requests a Pattern Draft from a Research Pack
- **THEN** the Skill SHALL require the Research Pack and the selected content pattern as inputs before generation.

#### Scenario: CMS import follows validation
- **WHEN** an operator requests CMS draft creation
- **THEN** the Skill SHALL require a validated Article JSON payload and an approved source draft before the agent calls MCP `article_create`.

### Requirement: Runtime content artifacts have a fixed location and taxonomy
The Skill SHALL resolve runtime artifacts from `CONTENT_OUTPUT_BASE` and SHALL use the directories `research-packs`, `drafts`, `review`, `publish-jobs`, `published`, and `reports`. The Skill SHALL NOT treat runtime artifacts as versioned source assets.

#### Scenario: A draft import produces traceable artifacts
- **WHEN** a validated draft is prepared for CMS import
- **THEN** the Skill SHALL store its payload and validation report under `publish-jobs` and retain an import receipt after successful creation.

### Requirement: Article payloads conform to the draft-import contract
The Skill SHALL validate an Article payload before CMS import. The payload SHALL contain non-empty `title`, HTML `body`, `slug`, and a permitted `category`; it MAY contain `summary`, `source_name`, and `commentary`. The Skill SHALL reject payloads that fail validation or whose slug already exists.

#### Scenario: Valid payload is accepted for draft creation
- **WHEN** an approved Pattern Draft is transformed into a complete payload with an available slug
- **THEN** the Skill SHALL allow the agent to invoke MCP `article_create` during the draft import stage.

#### Scenario: Invalid payload is rejected without CMS mutation
- **WHEN** a payload is missing a required field or has an unsupported category
- **THEN** the Skill SHALL report validation failure and SHALL NOT create or update a CMS article.

### Requirement: The Skill creates drafts only
The Skill SHALL use lnkwebsite MCP `article_create`, which hardcodes `status=draft`, and SHALL require resulting CMS records to have `status=draft`. The Skill SHALL NOT invoke an article publication operation or accept a `published` status as an import input.

#### Scenario: T-01 is imported as a non-public draft
- **WHEN** the approved T-01 Pattern Draft is imported through MCP `article_create`
- **THEN** the CMS SHALL contain a record with slug `what-is-ai-agent`, category `ai-trends`, and status `draft`.

#### Scenario: Draft remains absent from public outputs
- **WHEN** the imported T-01 record remains in draft status
- **THEN** it SHALL be absent from public article listings, sitemap, RSS, and `llms.txt` outputs.

### Requirement: Draft imports retain an execution receipt
After a successful CMS draft creation, the Skill SHALL write a receipt identifying the source draft, payload digest, article ID, slug, category, and returned status. The receipt SHALL record the status as `draft`.

#### Scenario: Successful import receipt is available
- **WHEN** MCP `article_create` returns a successful draft-creation result
- **THEN** the Skill SHALL persist a receipt before reporting success to the operator.

