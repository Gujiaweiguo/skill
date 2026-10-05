# Product Governance Contracts

These versioned schemas define skill-to-skill references for the product layers. They are interfaces, not product data stores and not authorities for any product's canonical ontology, PRD, or code.

## Contracts

- `source-reference.schema.json`: references source material, observations, code facts, ontology assertions, and product decisions without embedding source content. Material index `source_id` and `content_sha256` may be carried through this reference.
- `layer-reference.schema.json`: identifies a product layer authority and its version/revision, or explicitly records unresolved status.
- `ontology-change-set.schema.json`: records a proposed first baseline or delta against a named ontology version. Approval is required before canonical promotion.
- `reconciliation-record.schema.json`: records one independently inspectable pairwise comparison among ontology, PRD, and code.
- `implementation-return.schema.json`: records reviewed implementation evidence and proposed destination-layer writeback.
- `scan-coverage.schema.json`: shared machine-readable scanner scope, limitations, and artifact counts.

Reverse code scans should carry the machine-readable `scan_coverage` manifest from
`current-code-map.json` into reconciliation and implementation-return artifacts. The
manifest records scanner scope, artifact counts, exclusions or limitations, and
explicit `not-scanned` states; an empty result from an unrun scanner is not evidence
of absence.

The bounded direct scanners are opt-in. Their allowlists and capability terms come
from project code-map rules; matches are static `code` or test-file `test` evidence
only. They do not execute source or tests and cannot establish runtime verification,
test pass status, product acceptance, or canonical promotion.

Python matches may carry a syntax-context role (`import`, `declaration`, `fixture`,
`assertion`, `mapping`, or `other`). Roles are navigation hints only and do not rank
evidence or imply requirement satisfaction.

Ontology changes carry proposed semantic content in `changes[].proposed_content`; an ontology-change-set is a reviewable content proposal, not merely a missing-concept pointer. An accepted review requires owner decision metadata and a versioned `proposed_release` record before canonical promotion.

## Flow Direction and Approval

The default for new product work and PRD increments is forward governance: assess ontology impact against the current accepted baseline, record either no ontology change or a reviewable ontology candidate, prepare the PRD baseline/delta, then hand approved intent to code implementation. A forward ontology impact check is required even when the result is no change.

For existing code that leads its PRD or ontology documentation, code/spec/test scans may run in reverse to recover implementation facts. Such facts must identify repository revision and scan coverage and may produce reconciliation findings and ontology/PRD candidates only. Reverse-origin records do not bypass OPC review or directly promote canonical content. An `implementation-return` with `origin_flow: code-evidence-reverse` therefore requires `source_revision` and `scan_coverage`, and permits only proposed ontology/PRD/reconciliation updates.

Flow direction belongs to an individual change/return record, never to a product registry entry. OPC is the approval owner for product and ontology decisions. Code facts remain evidence tied to a target repository revision and scan scope; OPC approval does not imply unperformed technical verification.

Product completeness is separate from skill adapter maturity. A complete product may have a partial or unsupported adapter; an accepted ontology baseline may still be explicitly incomplete in coverage. `product_status` (authoritative source: `company.yaml` products, the sole product ledger) describes product lifecycle/completeness, while `adapter_status` (authoritative source: the consuming skill's `references/adapter-capabilities.yaml`) describes the skill's ability to resolve and process that product.

Migration-period note (owner decision O3/Batch 2, 2026-10-04; closed by D1/D2, same date): the per-consumer adapter capability authority lives in each consuming skill's `references/adapter-capabilities.yaml` (Plan B, Batch 1). The retired `product-registry.yaml` (deleted by owner decision D1, 2026-10-04) previously carried a frozen `adapter_status` snapshot whose enum could not express `blocked`/`not-applicable` (lnkgateway, lnkwebsite); the capability file prevails. Registry consumers, replacement sources, and the retirement closure are audited in skill-repo `references/product-registry-迁移审计-2026-10-04.md`.

Consumers MUST retain product-specific IDs such as competitor `evidence_id` and `capability_id` and material index paths. These schemas link to those IDs; they do not replace the owning skill's records.

Paths in references are relative to the active company/product root unless the source is an external URL or code repository reference. Missing authority and incomplete scans MUST be represented explicitly; consumers MUST NOT substitute another product's authority or infer absence from an unscanned area.

The in-scope product IDs are `lnkcre`, `lnkcrm`, `lnkchatbi`, `lnkreport`, `lnkvision`, `lnkgateway`, and `lnkchat`. `lnkwebsite` website/CMS operations are outside this software product contract.
