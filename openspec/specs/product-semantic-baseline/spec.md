# product-semantic-baseline Specification

## Purpose
TBD - created by archiving change product-semantic-prd-handoff. Update Purpose after archive.
## Requirements
### Requirement: Product semantic baselines SHALL declare their model kind and ownership
Each product configuration consumed by the skills SHALL declare its canonical product ID, product class, ontology profile, authoritative source paths for ontology, PRD, and code, stable identifier namespace, and owning product/repository. Business ontology and tool/product ontology profiles SHALL be supported without requiring tool products to use business-domain entities. The initial governance scope SHALL include business products `lnkcre` and `lnkcrm`, and tool products `lnkchatbi`, `lnkreport`, `lnkvision`, `lnkgateway`, and `lnkchat`. Website/CMS operations product `lnkwebsite` is outside this software product governance scope.

Registry metadata SHALL distinguish product lifecycle/completeness from skill adapter maturity. Governance flow direction is per change/return, not a product-level classification. OPC SHALL be the approval owner for product and ontology decisions; code evidence SHALL retain technical provenance and verification independently.

#### Scenario: A business product uses multiple semantic artifacts
- **WHEN** the skills process an `lnkcre` or `lnkcrm` product configuration
- **THEN** the configuration SHALL distinguish its business ontology artifacts, PRD baseline/deltas, target code repository, and any released semantic snapshot instead of treating them as one file

#### Scenario: A tool product is processed
- **WHEN** the skills process an `lnkchatbi`, `lnkreport`, `lnkvision`, `lnkgateway`, or `lnkchat` configuration
- **THEN** the configuration SHALL resolve that product's own tool ontology/profile without requiring a CRE-style operational domain model or loading another product's ontology

#### Scenario: Website operations are processed
- **WHEN** the skills process `lnkwebsite` website or CMS operations
- **THEN** those operations SHALL remain governed by website-operations contracts and SHALL NOT be treated as an in-scope software product baseline unless the product scope is explicitly changed

### Requirement: Product adapters SHALL isolate domain-specific terminology and scanners
Product-specific aliases, ontologies, source-of-truth order, code scanners, verification gates, and unsupported areas SHALL be declared by an adapter or project configuration. Shared skill instructions SHALL NOT assume CRE-only concepts for other products.

#### Scenario: LnkReport capability mapping
- **WHEN** LnkReport is analyzed
- **THEN** its datasource, dataset, report, rendering, export, sharing, embedding, and permission terms SHALL be loaded from the LnkReport adapter rather than the LnkCRE adapter

#### Scenario: Unsupported scanner coverage
- **WHEN** a product adapter disables a scanner
- **THEN** generated reports SHALL expose the scanner as unsupported or not scanned and SHALL NOT treat the unscanned area as product absence

### Requirement: Semantic releases SHALL be treated as versioned consumption slices
When a product exposes a semantic release for an AI, integration, or PRD consumer, the release SHALL identify its source product-model version, source repository revision, status, approving decision/owner, included semantic scope, and consumer compatibility constraints.

#### Scenario: Accepted release is consumable
- **WHEN** a downstream consumer selects a semantic release
- **THEN** the release SHALL be accepted, version-pinned, and traceable to a source model revision

#### Scenario: Raw planning material is not consumable
- **WHEN** a PRD or unverified code-map is available without an accepted semantic release
- **THEN** the skills SHALL not describe that material as an AI-consumable semantic contract

#### Scenario: A PRD baseline records its ontology basis
- **WHEN** a first/full or incremental PRD is generated from a released ontology
- **THEN** the PRD metadata SHALL identify the release/version and source revision used; if only an unaccepted model is available, the PRD SHALL label that basis as draft or proposed

### Requirement: Product-layer authorities SHALL be explicit and non-substitutable
For every in-scope product, skills SHALL identify the authoritative ontology, PRD baseline, and code/spec repository independently. Missing or inaccessible authority SHALL be reported as unresolved, unsupported, or not scanned. Skills SHALL NOT use a generated output as canonical authority before reviewed promotion and SHALL NOT silently substitute another product's authority.

#### Scenario: Generated PRD output has not been promoted
- **WHEN** a PRD artifact exists only in a generation/output area
- **THEN** it SHALL be treated as generated work, not as the canonical PRD baseline, until the product owner reviews and promotes it

#### Scenario: A product authority cannot be resolved
- **WHEN** one layer's canonical source is missing or inaccessible
- **THEN** the skill SHALL report the unresolved layer and SHALL NOT silently use a different product's source

#### Scenario: Product completeness differs from adapter maturity
- **WHEN** a product is complete but the skill adapter is partial or unsupported, or vice versa
- **THEN** registry records SHALL preserve both statuses independently without inferring one from the other

#### Scenario: Flow direction varies by change
- **WHEN** a product change follows forward governance or a legacy code-evidence recovery
- **THEN** the direction SHALL be recorded on that change/return and SHALL NOT be used to classify the product's historical order

