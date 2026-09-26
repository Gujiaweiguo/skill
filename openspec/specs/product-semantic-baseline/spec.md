# product-semantic-baseline Specification

## Purpose
TBD - created by archiving change product-semantic-prd-handoff. Update Purpose after archive.
## Requirements
### Requirement: Product semantic baselines SHALL declare their model kind and ownership
Each product configuration consumed by the skills SHALL declare a `model_kind`, authoritative source paths, stable identifier namespace, and owning product/repository. Supported model kinds SHALL include `business-ontology`, `capability-model`, `operational-domain-model`, `product-runtime-model`, and `semantic-release`.

#### Scenario: LnkCRE uses multiple semantic layers
- **WHEN** the skills process an LnkCRE product configuration
- **THEN** the configuration SHALL distinguish the shared business ontology/capability matrix, the operational domain model, the PRD, the target repository, and any Semantic Release instead of treating them as one file

#### Scenario: A non-business platform is processed
- **WHEN** the skills process an LnkReport, LnkChatBI, or LnkChat configuration
- **THEN** the configuration SHALL allow a capability or runtime model without requiring a CRE-style operational domain model

### Requirement: Product adapters SHALL isolate domain-specific terminology and scanners
Product-specific aliases, ontologies, source-of-truth order, code scanners, verification gates, and unsupported areas SHALL be declared by an adapter or project configuration. Shared skill instructions SHALL NOT assume CRE-only concepts for other products.

#### Scenario: LnkReport capability mapping
- **WHEN** LnkReport is analyzed
- **THEN** its datasource, dataset, report, rendering, export, sharing, embedding, and permission terms SHALL be loaded from the LnkReport adapter rather than the LnkCRE adapter

#### Scenario: Unsupported scanner coverage
- **WHEN** a product adapter disables a scanner
- **THEN** generated reports SHALL expose the scanner as unsupported or not scanned and SHALL NOT treat the unscanned area as product absence

### Requirement: Semantic releases SHALL be treated as versioned consumption slices
When a product exposes a semantic release for an AI or integration consumer, the release SHALL identify its source product-model version, source repository revision, status, included objects/events/metrics/commands, and consumer compatibility constraints.

#### Scenario: Accepted release is consumable
- **WHEN** a downstream consumer selects a semantic release
- **THEN** the release SHALL be accepted, version-pinned, and traceable to a source model revision

#### Scenario: Raw planning material is not consumable
- **WHEN** a PRD or unverified code-map is available without an accepted semantic release
- **THEN** the skills SHALL not describe that material as an AI-consumable semantic contract

