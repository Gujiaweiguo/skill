# ontology-lifecycle-governance Specification

## Purpose
Defines product ontology profiles (business vs tool), first-version synthesis and incremental deltas with classified provenance, OPC-owned review and release gates, and forward/reverse flow governance for the seven in-scope software products.
## Requirements
### Requirement: Product ontologies SHALL declare their profile and authority
For each in-scope product, governance records SHALL identify whether its semantic model is a business ontology or a tool/product ontology, its owner, canonical authority, stable identifier namespace, and relationship to PRD and code authorities. Business ontology profiles MAY model business objects, relationships, lifecycles, rules, and domain terms. Tool ontology profiles MAY model product concepts such as capabilities, workflows, datasets, charts, executions, or integrations and SHALL NOT be forced into a business-entity taxonomy.

#### Scenario: Business product authority is resolved
- **WHEN** a skill processes `lnkcre` or `lnkcrm`
- **THEN** it SHALL resolve the registered business ontology authority and SHALL NOT substitute a tool ontology or another product's ontology

#### Scenario: Tool product authority is resolved
- **WHEN** a skill processes `lnkchatbi`, `lnkreport`, `lnkvision`, `lnkgateway`, or `lnkchat`
- **THEN** it SHALL resolve that product's registered tool ontology/profile and SHALL NOT require CRE-style business entities

#### Scenario: Product authority is unknown or incomplete
- **WHEN** a product's ontology path, owner, or profile is unresolved or inaccessible
- **THEN** the result SHALL identify the unresolved authority and SHALL NOT silently fall back to another product's ontology

### Requirement: Ontology changes SHALL follow a reviewed lifecycle
Ontology changes SHALL be represented as candidates with stable identifiers, affected concepts, source references, rationale, owning product, proposer, and review status. A candidate SHALL NOT mutate canonical ontology content until the designated owner approves it. The lifecycle and allowed transitions SHALL distinguish at minimum draft/candidate, under review, accepted, released, and rejected or superseded outcomes.

#### Scenario: Candidate moves through review before canonical update
- **WHEN** an ontology candidate is submitted for review
- **THEN** its lifecycle state and owner decision SHALL be recorded, and the canonical ontology SHALL remain unchanged until approval

### Requirement: First-version ontology generation SHALL synthesize a reviewable baseline from available inputs
When no canonical ontology baseline exists for an in-scope product, the ontology workflow SHALL be able to synthesize a first-version ontology draft from available customer requirements, competitor information, code/spec/test facts, and OPC/product-owner ideas. It SHALL classify each input by provenance and distinguish observed evidence, inference, and product judgment. It SHALL preserve source references and unresolved questions for each proposed concept, relationship, lifecycle, rule, capability, or term. Generated content SHALL remain a draft until reviewed and approved by the product's designated ontology owner.

#### Scenario: First ontology version is generated for a business product
- **WHEN** an owner requests an initial ontology for `lnkcre` or `lnkcrm` and no accepted baseline exists
- **THEN** the workflow SHALL synthesize business-domain concepts from available inputs, preserve provenance per proposal, and label the result as a draft baseline pending owner review

#### Scenario: First ontology version is generated for a tool product
- **WHEN** an owner requests an initial ontology for `lnkchatbi`, `lnkreport`, `lnkvision`, `lnkgateway`, or `lnkchat` and no accepted baseline exists
- **THEN** the workflow SHALL synthesize product/tool concepts appropriate to that product without imposing a business-entity model, and label the result as a draft baseline pending owner review

#### Scenario: Initial inputs disagree or are incomplete
- **WHEN** customer requirements, competitor information, code facts, or OPC ideas are absent, inaccessible, unverified, or conflicting
- **THEN** the generated draft SHALL preserve those states and identify the affected concepts for review rather than inventing facts or claiming complete coverage

#### Scenario: Initial ontology draft is approved
- **WHEN** the designated owner reviews and approves the first-version ontology draft
- **THEN** the accepted content SHALL be promoted as the canonical ontology baseline with a version, decision record, source references, and source revision where available

#### Scenario: PRD discovery suggests a new concept
- **WHEN** PRD analysis identifies a missing object, relationship, term, rule, or capability concept
- **THEN** the skill SHALL create or report an ontology-change candidate linked to its evidence and SHALL keep it separate from the authoritative ontology until reviewed

#### Scenario: Implementation reveals a semantic mismatch
- **WHEN** code implementation or verification reveals that an ontology concept is incomplete or incorrect
- **THEN** the return record SHALL propose an ontology change with code/spec/test evidence and SHALL NOT directly rewrite the canonical ontology

#### Scenario: Owner rejects a candidate
- **WHEN** the ontology owner rejects a proposed change
- **THEN** the decision, reason, reviewer, and affected trace identifiers SHALL remain recorded and the canonical ontology SHALL remain unchanged by that candidate

### Requirement: Ontology releases SHALL gate downstream semantic consumption
An ontology release intended for downstream consumption SHALL identify the product, ontology profile, version, accepted status, source revision, approving owner or decision, included semantic scope, and compatibility constraints. Consumers SHALL distinguish editable source ontology from a version-pinned released snapshot.

#### Scenario: Accepted ontology release is consumed
- **WHEN** a PRD or downstream tool/AI consumer uses released semantic content
- **THEN** it SHALL record the accepted release identifier and source revision used

#### Scenario: Draft ontology is available without an accepted release
- **WHEN** only a draft, candidate, or proposed ontology is available
- **THEN** a consumer MAY inspect it for planning but SHALL label it unaccepted and SHALL NOT present it as a released runtime semantic contract

#### Scenario: Ontology changes after a PRD baseline
- **WHEN** a new ontology release is accepted after a PRD baseline was created
- **THEN** the system SHALL mark affected PRD/reconciliation records as requiring comparison and SHALL NOT silently rewrite the existing PRD baseline

### Requirement: Incremental ontology modification SHALL be expressed as a delta against a named baseline
When a canonical ontology baseline exists, the workflow SHALL compare newly supplied customer requirements, competitor information, code/spec/test facts, and OPC/product-owner ideas against a named ontology version. It SHALL produce a reviewable change set that identifies additions, modifications, deprecations, and relationship changes, with rationale, provenance, affected concepts, compatibility/impact notes, and related PRD/code trace identifiers. Inputs SHALL remain distinct: a customer request or competitor capability SHALL NOT by itself become an approved product ontology assertion, and an OPC idea SHALL be recorded as product judgment rather than external evidence. Only owner-approved changes SHALL be promoted into a new canonical ontology version/release.

#### Scenario: New customer input proposes an ontology change
- **WHEN** a customer requirement introduces a potentially reusable business or product concept not represented in the named ontology baseline
- **THEN** the workflow SHALL propose a delta linked to the requirement and explain why it is a candidate ontology concept rather than silently adding it to the baseline

#### Scenario: Competitor information proposes an ontology change
- **WHEN** competitor information reveals a potentially relevant concept, relationship, state, rule, or capability
- **THEN** the workflow SHALL preserve competitor evidence references and propose an ontology delta for product-owner review without treating competitor presence as a product mandate

#### Scenario: OPC idea proposes an ontology change
- **WHEN** OPC/product-owner input proposes a new or changed concept or rule
- **THEN** the workflow SHALL record it as a product judgment with owner, rationale, and decision status, distinguish it from observed evidence, and include it in the candidate delta

#### Scenario: Incremental ontology candidate is rejected or deferred
- **WHEN** an owner rejects or defers one or more proposed ontology changes
- **THEN** the decision and reason SHALL be recorded against the candidate trace IDs, and rejected/deferred content SHALL NOT be represented as part of the canonical ontology version

#### Scenario: Incremental ontology candidate is approved
- **WHEN** an owner approves a change set against a named ontology baseline
- **THEN** the workflow SHALL produce a new version/release linked to the parent version, accepted delta, review decision, source references, and source revision where available

#### Scenario: Ontology delta is promoted
- **WHEN** an ontology delta is promoted to a new canonical version
- **THEN** the workflow SHALL request impact reconciliation for affected ontology-to-PRD, PRD-to-code, and ontology-to-code records without automatically rewriting PRD or code authorities

### Requirement: Future product changes SHALL use forward governance independent of historical product state
For new products and future incremental changes, the workflow SHALL assess impact against the accepted ontology baseline before forming the PRD baseline or delta and before code implementation. The assessment SHALL record either proposed ontology changes or a reasoned no-change result. This default SHALL NOT encode or infer a product-specific historical source order.

#### Scenario: Incremental PRD has no ontology change
- **WHEN** an increment does not change product semantics
- **THEN** the workflow SHALL record the ontology baseline inspected and the rationale for no ontology change before producing the PRD delta

#### Scenario: Increment changes product semantics
- **WHEN** an increment introduces a semantic change
- **THEN** the workflow SHALL create a reviewable ontology candidate and trace the PRD delta to the accepted ontology baseline or the pending candidate before handing the change to code implementation

### Requirement: Existing code facts MAY be synchronized in reverse only as reviewed candidates
When existing code/spec/test evidence leads documentation, the workflow MAY inspect the implementation to recover as-is facts. Each fact SHALL identify target repository revision and scan coverage. Reverse synchronization SHALL create reconciliation findings or proposed ontology/PRD updates only; it SHALL NOT convert implementation facts directly into product intent or mutate canonical ontology/PRD. OPC is the product and ontology decision owner; approval records SHALL identify OPC. OPC approval does not replace code verification evidence.

#### Scenario: Code evidence suggests an ontology or PRD update
- **WHEN** a reverse scan finds a behavior or capability absent from ontology/PRD
- **THEN** the result SHALL retain code/spec/test provenance and revision, record scan limitations, and route an ontology/PRD candidate to OPC review without promoting it

#### Scenario: Product and adapter maturity differ
- **WHEN** product completeness and skill adapter support have different states
- **THEN** the registry and generated reports SHALL preserve them as independent values; neither state SHALL be inferred from the other

