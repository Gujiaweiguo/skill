# Content Operations Skill Specification

## Purpose
Defines the lnkwebsite content-operations skill contracts: draft-only article/case/product payload validation (client authorization gates, forbidden brand-term checks) before CMS draft creation, and evidence-gated maintenance revisions for published content (build → diff review → human review → apply, with the Skill never approving or applying).

## Requirements

### Requirement: Case payloads conform to the draft-import contract

The Skill SHALL validate a Case payload before CMS import. The payload SHALL contain non-empty `slug`, `client_name`, `industry`, `problem`, `solution`, `outcome`; it MAY contain `testimonial` and `image`. The payload SHALL include `client_authorized: true` confirming the client has authorized publication. The Skill SHALL reject payloads with forbidden brand terms (`解决方案`, `数字营销`, `新零售`, `新商业`, `新营销`, `新消费`) in any text field.

#### Scenario: Valid case payload is accepted
- **WHEN** a Case payload has all required fields, valid industry, client_authorized=true, and no forbidden terms
- **THEN** the Skill SHALL accept the payload for draft import

#### Scenario: Case payload without authorization is rejected
- **WHEN** a Case payload has client_authorized=false or missing
- **THEN** the Skill SHALL reject the payload without CMS mutation

#### Scenario: Case payload with forbidden term is rejected
- **WHEN** a Case payload contains "解决方案" in any text field
- **THEN** the Skill SHALL reject the payload

### Requirement: Product payloads conform to the draft-import contract

The Skill SHALL validate a Product payload before CMS import. The payload SHALL contain non-empty `product_type`, `slug`, `title`; it MAY contain `headline`, `description`, `seo_title`, `seo_description`, `image`, and `details` (JSON). The Skill SHALL reject payloads with forbidden brand terms. If the product references AI Vision (`slug` contains `mallsense` or `vision`), `details.capabilities` SHALL only claim MVP items (通道拥堵, 火灾烟雾, 地面脏污); roadmap items MUST be absent from `capabilities`.

#### Scenario: Valid product payload is accepted
- **WHEN** a Product payload has all required fields, valid product_type, and no forbidden terms
- **THEN** the Skill SHALL accept the payload for draft import

#### Scenario: Product payload with invalid product_type is rejected
- **WHEN** a Product payload has product_type="invalid"
- **THEN** the Skill SHALL reject the payload

#### Scenario: AI Vision product claims non-MVP capability
- **WHEN** a Product payload has slug="mallsense-ai" or slug="lnkvision" and details.capabilities includes "精准客流"
- **THEN** the Skill SHALL reject the payload (roadmap item in capabilities)

### Requirement: The Skill creates drafts only

The Skill SHALL use lnkwebsite MCP `article_create`, `case_create`, and `product_create`, all of which hardcode `status=draft`. The Skill SHALL require resulting CMS records to have `status=draft`. The Skill SHALL NOT invoke any publication operation or accept a `published` status as an import input for any entity type.

#### Scenario: T-01 is imported as a non-public draft
- **WHEN** the approved T-01 Pattern Draft is imported through MCP `article_create`
- **THEN** the CMS SHALL contain a record with slug `what-is-ai-agent`, category `ai-trends`, and status `draft`.

#### Scenario: Case draft is non-public
- **WHEN** a Case payload is imported through MCP `case_create`
- **THEN** the CMS SHALL contain a record with status `draft`

#### Scenario: Product draft is non-public
- **WHEN** a Product payload is imported through MCP `product_create`
- **THEN** the CMS SHALL contain a record with status `draft`

### Requirement: Maintenance revision payloads follow the build-and-validate contract

The Skill SHALL build maintenance revisions for published `article`, `case`, and `product` content by comparing current and desired field values into `proposed_fields`, excluding server-controlled fields, and SHALL render a human-readable diff document for review. The payload SHALL carry a valid `entity_type`, non-empty `entity_id`, `rationale`, and `base_digest` of the current snapshot; `proposed_fields` SHALL be non-empty. The Skill SHALL NOT approve, reject, or apply revisions.

#### Scenario: Valid maintenance payload is accepted

- **WHEN** a maintenance payload targets entity_type="article" with non-empty entity_id, rationale, base_digest, and proposed_fields containing only mutable fields
- **THEN** the Skill SHALL accept the payload and emit a validation report with valid=true

#### Scenario: Maintenance payload proposing a server-controlled field is rejected

- **WHEN** a maintenance payload includes `id`, `status`, `published_at`, `created_at`, or `updated_at` in proposed_fields
- **THEN** the Skill SHALL reject the payload before any MCP call

#### Scenario: Empty rationale or empty proposed_fields is rejected

- **WHEN** a maintenance payload has an empty rationale or empty proposed_fields
- **THEN** the Skill SHALL reject the payload

#### Scenario: Skill never approves, rejects, or applies

- **WHEN** any maintenance workflow step executes
- **THEN** the Skill SHALL NOT call maintenance approve, reject, or apply operations; human review and application happen outside the Skill

### Requirement: Maintenance receipts and post-apply verification are evidence-gated

The Skill SHALL write a create receipt only when MCP `maintenance_revision_create` returns `status=pending-review` and a `base_digest` matching the payload's `base_digest`. After a human approves and applies the revision outside the Skill, the Skill SHALL verify via MCP `maintenance_revision_get` that `status=applied` and `post_snapshot_id` is non-empty before writing the post-apply verification artifact.

#### Scenario: Receipt requires pending-review status and matching base digest

- **WHEN** MCP `maintenance_revision_create` returns status="pending-review" and base_digest equal to the payload's base_digest
- **THEN** the Skill SHALL write the create receipt recording the revision id and echoed digests

#### Scenario: Non-pending-review create result is rejected

- **WHEN** MCP `maintenance_revision_create` returns any status other than "pending-review", or a base_digest that does not match the payload
- **THEN** the Skill SHALL NOT write a receipt

#### Scenario: Post-apply verification requires applied status and a snapshot

- **WHEN** the post-apply check runs against a revision whose status is not "applied" or whose post_snapshot_id is missing
- **THEN** the Skill SHALL NOT write the post-apply verification artifact
- **WHEN** the revision has status="applied" and a non-empty post_snapshot_id
- **THEN** the Skill SHALL write the post-apply verification artifact
