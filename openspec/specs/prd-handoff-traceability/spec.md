# prd-handoff-traceability Specification

## Purpose
TBD - created by archiving change product-semantic-prd-handoff. Update Purpose after archive.
## Requirements
### Requirement: Actionable capability records SHALL carry traceable source and implementation identity
Each new or revised actionable capability/requirement SHALL carry a stable `trace_id`, source references, target product/repository, implementation status, evidence state, and links to downstream PRD/OpenSpec/verification records when available.

#### Scenario: Competitor evidence becomes an incremental PRD item
- **WHEN** a competitor capability is selected for product improvement
- **THEN** the generated PRD item SHALL retain the capability evidence IDs and a stable trace ID

#### Scenario: A target repository completes implementation
- **WHEN** an OpenSpec change is verified and archived
- **THEN** the implementation return package SHALL link the change ID and verification evidence back to the originating trace ID

### Requirement: Evidence state SHALL be distinct from implementation status
The skills SHALL represent `observed`, `inferred`, `not_found`, `not_scanned`, `inaccessible`, and `conflicting` evidence states separately from `existing`, `partial`, `missing`, `explicitly-not-do`, and `unknown` implementation statuses.

#### Scenario: Demo access is incomplete
- **WHEN** a competitor page is unavailable to the authorized account
- **THEN** the result SHALL be marked inaccessible or not observed and SHALL NOT claim that the competitor lacks the capability

#### Scenario: Code scanner is incomplete
- **WHEN** a target repository scanner does not cover a source area
- **THEN** the result SHALL be not scanned/unknown and SHALL NOT create a missing implementation gap without further evidence

### Requirement: Incremental PRD handoffs SHALL include target-repository consumption and return sections
An incremental PRD handoff SHALL include source/semantic baseline versions, current-state evidence, goals and non-goals, acceptance scenarios, proposed OpenSpec split, target-repository gates, open decisions, consumption instructions, and write-back requirements.

#### Scenario: LnkCRE consumes an incremental PRD
- **WHEN** the target repository receives a generated consumption prompt
- **THEN** it SHALL be instructed to read its own AGENTS.md/specs/active changes, validate the gap against current code, create OpenSpec changes locally, and return verification evidence

#### Scenario: Implementation finds a false positive
- **WHEN** the target repository proves that a reported gap already exists
- **THEN** the return package SHALL record the false positive and identify the code/spec evidence needed for docs-side reconciliation

### Requirement: Documentation write-back SHALL be explicit and reviewed
The skills SHALL generate proposed write-back records for PRD status, capability status, reconciliation ledger, and model change candidates without silently overwriting authoritative product documents.

#### Scenario: Verified implementation is returned
- **WHEN** a target repository returns a verified implementation package
- **THEN** the docs-side record SHALL be able to update the originating trace status and link the archived change and verification evidence

#### Scenario: Domain semantics change is discovered
- **WHEN** implementation reveals a domain-model or product-model mismatch
- **THEN** the result SHALL create a model-change proposal or decision item rather than automatically changing the model

