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
The skills SHALL generate structured proposed write-back records for ontology-to-PRD, PRD-to-code, and ontology-to-code reconciliation, PRD/capability status, implementation return evidence, and ontology change candidates without silently overwriting authoritative product documents. Canonical updates SHALL occur only after the destination layer's owner reviews and accepts the proposal. New implementation-return artifacts SHALL use the single authoritative vocabulary and schema version defined by the shared `implementation-return` contract: `review_status` values `pending`/`reviewed`/`absorbed`/`rejected` and `schema_version` value `1.0`; advisory documents and absorption workflows SHALL NOT introduce parallel status values (for example `accepted` or `incomplete`) or alternative version strings, and a legacy value appearing in historical files SHALL NOT by itself be adopted as a new standard. Reading-side compatibility for historical artifacts SHALL keep the original values, the original validation errors, the normalization actions, and the post-normalization result distinguishable: a file that passes validation only after normalization SHALL NOT be reported as passing strict validation as-written, and out-of-vocabulary status values SHALL be preserved verbatim with a warning instead of being unconditionally mapped into the vocabulary.

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
- **THEN** the return SHALL remain at its current lifecycle status with the missing evidence recorded explicitly and SHALL NOT be treated as verified synchronization

#### Scenario: Return record carries trace, revision, and decision fields
- **WHEN** a write-back or implementation return record is generated
- **THEN** it SHALL identify the originating trace IDs, product, source and target layer revisions, OpenSpec change and verification evidence where applicable, findings/false positives, proposed destination updates, decision owner, and review status

#### Scenario: New return uses the authoritative vocabulary and version
- **WHEN** a session writes a new implementation-return artifact
- **THEN** its `review_status` SHALL be one of `pending`/`reviewed`/`absorbed`/`rejected` and its `schema_version` SHALL be `1.0`, and any advisory document instructing absorption SHALL use the same vocabulary

#### Scenario: Legacy status values are preserved, not remapped
- **WHEN** a historical return carries an out-of-vocabulary status such as `accepted` or an unissued version string such as `1.1`
- **THEN** compatible reading SHALL preserve the original value verbatim with a warning for owner disposition and SHALL NOT silently map it to `reviewed` or `absorbed` or treat `1.1` as a released schema version

#### Scenario: Normalized pass is distinguished from source pass
- **WHEN** a historical return fails strict validation and is mechanically normalized for absorption
- **THEN** the absorption record SHALL report the original error count, the normalization actions, and the post-normalization result (including remaining error paths and counts) as distinct facts and SHALL NOT describe the source file as passing strict validation or fabricate review_owner, verification_refs, change IDs, or other facts to obtain a pass

### Requirement: Incremental PRD version chains SHALL absorb multiple related events and permit evidence-driven correction
An incremental PRD SHALL evolve as one living document per increment whose version history itemizes each triggering event. Slice delivery lifecycle, implementation status, evidence state, and open-question status SHALL stay distinct. New evidence MAY correct a fact judgment or reopen an open question while retaining the original judgment and correction basis; errata SHALL NOT back-date or rewrite occurred authorization, consumption, or verification history.

#### Scenario: One version absorbs a multi-return batch
- **WHEN** several related execution or verification returns are absorbed in the same review batch
- **THEN** the increment MAY record them as one internal version whose history lists each return separately

#### Scenario: New evidence reopens a question
- **WHEN** verified code or review evidence contradicts a previously closed judgment
- **THEN** the increment SHALL reopen the question with the original judgment, the new evidence, and the correction basis retained, and SHALL NOT refuse the reopening on monotonic-status grounds

#### Scenario: Erratum must not rewrite consumption history
- **WHEN** a correction is applied after implementation has already consumed an earlier version
- **THEN** the correction SHALL be recorded as a new entry and SHALL NOT overwrite which version was actually consumed or back-date prior authorization

#### Scenario: Inferred initial judgment is corrected by verification
- **WHEN** code-level verification corrects an implementation status that was initially assigned from baseline inference
- **THEN** the correction record SHALL verify whether the initial judgment was marked `inferred` with a stated basis rather than blanket-declaring the original judgment faultless

#### Scenario: Mixed version naming remains valid
- **WHEN** an increment uses letter-suffixed versions while another uses dot-suffixed versions
- **THEN** neither naming scheme SHALL be force-migrated, and each increment SHALL keep its internal version rules consistent and distinguishable
