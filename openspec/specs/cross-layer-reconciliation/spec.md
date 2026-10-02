# cross-layer-reconciliation Specification

## Purpose
TBD - created by archiving change product-three-layer-governance-sync. Update Purpose after archive.
## Requirements
### Requirement: The three product layers SHALL be reconciled pairwise
For each in-scope product, governance SHALL be able to record separate reconciliation results for ontology-to-PRD, PRD-to-code, and ontology-to-code. Each result SHALL identify the compared artifact versions/revisions, timestamp, coverage and known scan limitations, evidence references, outcome, owner/reviewer, and required follow-up. A single aggregate status SHALL NOT replace the three pairwise results.

#### Scenario: Full product reconciliation is requested
- **WHEN** an owner requests a three-layer reconciliation for a product
- **THEN** the report SHALL provide distinct ontology-to-PRD, PRD-to-code, and ontology-to-code results or explicitly mark an unavailable comparison

#### Scenario: Only one pair can be inspected
- **WHEN** a run has evidence for only one pair of layers
- **THEN** it SHALL report that pair and mark the other comparisons not scanned or unavailable rather than implying full synchronization

### Requirement: Reconciliation SHALL distinguish drift from uncertainty and decisions
Pairwise outcomes SHALL distinguish aligned, drifted, conflicting, missing, not-scanned, inaccessible, deferred, intentionally unsupported, and false-positive-corrected states as applicable. Findings SHALL record evidence and SHALL identify whether resolution requires ontology review, PRD/product decision, implementation work, scanner coverage, or no action.

#### Scenario: Code scanner does not cover an area
- **WHEN** a scanner has not examined a relevant code/spec/test area
- **THEN** the comparison SHALL be marked not-scanned or unknown and SHALL NOT assert that implementation is missing

#### Scenario: Target repository disproves a PRD gap
- **WHEN** target-repository code/spec/test evidence shows a reported gap is already implemented
- **THEN** the PRD-to-code result SHALL record a false-positive correction with evidence and SHALL route any PRD or scanner correction to review

#### Scenario: Ontology and PRD concepts disagree
- **WHEN** ontology-to-PRD reconciliation finds an unmodeled PRD concept or a stale PRD reference
- **THEN** it SHALL distinguish a proposed ontology change from a PRD correction, link the source requirement/evidence/owner judgment, and identify the required owner decision

#### Scenario: An approved ontology version changes
- **WHEN** a first ontology baseline or an incremental ontology delta is approved and promoted
- **THEN** reconciliation SHALL compare the promoted ontology version with affected PRD and code revisions and create separate findings for each affected layer pair

### Requirement: Reconciliation decisions SHALL not overwrite layer authorities
Reconciliation SHALL produce reviewable findings and proposed actions. It SHALL NOT directly mutate canonical ontology, PRD baseline, product registry, or code/spec authority. Each accepted resolution SHALL record the decision owner, rationale, source evidence, affected trace identifiers, and destination layer.

#### Scenario: Finding is accepted for action
- **WHEN** an owner approves a reconciliation finding
- **THEN** the approved action SHALL identify the owning layer and a traceable follow-up record without changing unrelated layer authorities

#### Scenario: Finding remains unresolved
- **WHEN** evidence or owner judgment is insufficient to resolve a mismatch
- **THEN** the finding SHALL remain pending with an explicit blocker and SHALL NOT be converted to an implementation requirement by default

### Requirement: Code-led documentation recovery SHALL route through independent reconciliation
When code/spec/test evidence is used to recover an existing product's ontology or PRD, the workflow SHALL record implementation facts separately from semantic/product decisions, including target revision and scan coverage. Findings SHALL route to OPC for ontology/product-intent decisions or remain pending when evidence is insufficient. Reverse recovery SHALL NOT mark layers aligned merely because documentation was generated from code.

#### Scenario: Reverse-generated documentation is a candidate
- **WHEN** a code scan is used to draft ontology or PRD content
- **THEN** reconciliation SHALL retain the code revision and coverage, identify generated content as proposed, and require OPC review before canonical promotion

