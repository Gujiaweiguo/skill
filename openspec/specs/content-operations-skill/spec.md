## ADDED Requirements

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
- **WHEN** a Product payload has slug="mallsense-ai" and details.capabilities includes "精准客流"
- **THEN** the Skill SHALL reject the payload (roadmap item in capabilities)

## MODIFIED Requirements

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
