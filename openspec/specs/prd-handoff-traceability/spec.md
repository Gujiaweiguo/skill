# prd-handoff-traceability Specification

## Purpose
Defines the traceability contract for actionable capability and PRD handoff records across the evidence → ontology → PRD → target-repository chain: every new or revised actionable item carries a stable trace ID, canonical product, source references, ontology and PRD basis, target repository, implementation status, and evidence state, with customer evidence, competitor evidence, code facts, ontology assertions, and owner judgments kept as distinct provenance classes. Evidence states (observed, inferred, not_found, not_scanned, inaccessible, conflicting) stay separate from implementation statuses so an unscanned or inaccessible area is never reported as a missing capability, and first/full or incremental PRD handoffs identify their baseline and delta, acceptance scenarios, and target-repository consumption plus return obligations, with the target repository owning its local OpenSpec changes, implementation, and verification.
## Requirements
### Requirement: Actionable capability records SHALL carry traceable source and implementation identity
Each new or revised capability SHALL carry a stable `trace_id`, canonical product ID, source references, ontology profile/version or explicit unresolved state, PRD baseline/version, target repository, implementation status, evidence state, and downstream PRD/OpenSpec/verification links. Customer, competitor, code, ontology, and owner/OPC inputs SHALL keep distinct provenance classes. Ontology-generation and ontology-delta records SHALL trace back to their inputs and reviewed decisions.

#### Scenario: Competitor evidence becomes an incremental PRD item
- **WHEN** a competitor capability is selected for product improvement
- **THEN** the generated PRD item SHALL retain the capability evidence IDs and a stable trace ID

#### Scenario: Owner decision contributes to an actionable item
- **WHEN** an owner/OPC decision contributes to a new or revised capability
- **THEN** the trace record SHALL link the decision identifier, decision owner, rationale, status, and supporting evidence separately from observations

#### Scenario: Ontology concept is synthesized from source inputs
- **WHEN** an ontology draft or delta includes a concept synthesized from customer, competitor, code, or OPC input
- **THEN** the ontology item SHALL link to each contributing source/decision trace and retain whether each contribution is evidence, inference, or product judgment

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
First/full and incremental PRD implementation handoffs SHALL identify the PRD baseline/version and ontology basis, source/current-state evidence, goals and non-goals, acceptance scenarios, proposed OpenSpec split where applicable, target-repository gates, open decisions, consumption instructions, and write-back requirements. Incremental handoffs SHALL additionally identify the baseline delta. The target repository SHALL own its local OpenSpec changes, implementation, and verification.

#### Scenario: Target repository consumes a PRD handoff
- **WHEN** a target repository receives a first/full or incremental PRD implementation handoff
- **THEN** it SHALL be instructed to read its own AGENTS.md/specs/active changes, validate the gap against current code, create OpenSpec changes locally, and return verification evidence

#### Scenario: Implementation finds a false positive
- **WHEN** the target repository proves that a reported gap already exists
- **THEN** the return package SHALL record the false positive and identify the code/spec evidence needed for docs-side reconciliation

### Requirement: Documentation write-back SHALL be explicit and reviewed
The skills SHALL generate structured proposed write-back records for ontology-to-PRD, PRD-to-code, and ontology-to-code reconciliation, PRD/capability status, implementation return evidence, and ontology change candidates without silently overwriting authoritative product documents. Canonical updates SHALL occur only after the destination layer's owner reviews and accepts the proposal.

#### Scenario: Verified implementation is returned
- **WHEN** a target repository returns a verified implementation package
- **THEN** the docs-side record SHALL be able to update the originating trace status and link the archived change and verification evidence

#### Scenario: Implementation return proposes a semantic update
- **WHEN** implementation verification identifies an ontology, PRD, or authority mismatch
- **THEN** the return record SHALL identify the affected pairwise reconciliation and propose a reviewed update in the owning layer without directly changing another layer

#### Scenario: Domain semantics change is discovered
- **WHEN** implementation reveals a domain-model or product-model mismatch
- **THEN** the result SHALL create a model-change proposal or decision item rather than automatically changing the model

#### Scenario: An implementation return is incomplete
- **WHEN** a target repository returns without required revision, verification, or trace references
- **THEN** the return SHALL remain incomplete/pending and SHALL NOT be treated as verified synchronization

#### Scenario: Return record carries trace, revision, and decision fields
- **WHEN** a write-back or implementation return record is generated
- **THEN** it SHALL identify the originating trace IDs, product, source and target layer revisions, OpenSpec change and verification evidence where applicable, findings/false positives, proposed destination updates, decision owner, and review status

