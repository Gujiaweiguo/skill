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

## 词表与版本唯一权威（2026-11-13，change align-governance-handoff-contracts A2）

- implementation-return 新回执的 `schema_version` 唯一目标值为 `1.0`；`review_status` 的唯一词表是 `implementation-return.schema.json` 的 enum（`pending`/`reviewed`/`absorbed`/`rejected`）。
- `'1.1'` 与 `accepted`/`incomplete` 属 2026-11 历史漂移形态，**不是已发布标准**：兼容读取（`product_prd_generator/implementation_return_compat.py`）按原值折叠/记 warning 保留原文，不升级为标准值、不无条件映射到词表；映射处置待 owner 裁决。
- 吸收完成 = `reviewed → absorbed`，且 `absorbed` 受 schema 既有约束（须 `verification_refs` + `review_owner` 等证据锚）；证据不齐 = 停留原状态 + 显式缺口记录（compat warning），不引入第二状态值。
- 严格校验三段报告（`product_prd_generator.implementation_return_report.strict_validation_report`）：source（原件）与 normalized（归一化视图）各自独立校验、均允许失败并报告全部剩余错误；invocation 语义以 source 为唯一裁决输入——normalized 通过不等于源件通过。CLI 退出码：0=source 通过、1=source 失败（即使 normalized 通过）、2=依赖/输入操作性错误。

## 对账范围声明（`reconciliation-record.schema.json` `reconciliation_scope`，2026-11-13）

- 可选枚举字段：`increment-scoped`（仅覆盖本次增量交付涉及的切片）/ `product-wide`（产品级全量对账）；`schema_version` 保持 const `1.0`。
- 字段缺省仅表示**未声明**，不推断为任一范围；增量交付默认 increment-scoped，不得冒充 product-wide。

## Flow Direction and Approval

The default for new product work and PRD increments is forward governance: assess ontology impact against the current accepted baseline, record either no ontology change or a reviewable ontology candidate, prepare the PRD baseline/delta, then hand approved intent to code implementation. A forward ontology impact check is required even when the result is no change.

For existing code that leads its PRD or ontology documentation, code/spec/test scans may run in reverse to recover implementation facts. Such facts must identify repository revision and scan coverage and may produce reconciliation findings and ontology/PRD candidates only. Reverse-origin records do not bypass OPC review or directly promote canonical content. An `implementation-return` with `origin_flow: code-evidence-reverse` therefore requires `source_revision` and `scan_coverage`, and permits only proposed ontology/PRD/reconciliation updates.

Flow direction belongs to an individual change/return record, never to a product registry entry. OPC is the approval owner for product and ontology decisions. Code facts remain evidence tied to a target repository revision and scan scope; OPC approval does not imply unperformed technical verification.

Product completeness is separate from skill adapter maturity. A complete product may have a partial or unsupported adapter; an accepted ontology baseline may still be explicitly incomplete in coverage. `product_status` (authoritative source: `company.yaml` products, the sole product ledger) describes product lifecycle/completeness, while `adapter_status` (authoritative source: the consuming skill's `references/adapter-capabilities.yaml`) describes the skill's ability to resolve and process that product.

Migration-period note (owner decision O3/Batch 2, 2026-10-04; closed by D1/D2, same date): the per-consumer adapter capability authority lives in each consuming skill's `references/adapter-capabilities.yaml` (Plan B, Batch 1). The retired `product-registry.yaml` (deleted by owner decision D1, 2026-10-04) previously carried a frozen `adapter_status` snapshot whose enum could not express `blocked`/`not-applicable` (lnkgateway, lnkwebsite); the capability file prevails. Registry consumers, replacement sources, and the retirement closure are audited in skill-repo `references/product-registry-迁移审计-2026-10-04.md`.

Consumers MUST retain product-specific IDs such as competitor `evidence_id` and `capability_id` and material index paths. These schemas link to those IDs; they do not replace the owning skill's records.

Paths in references are relative to the active company/product root unless the source is an external URL or code repository reference. Missing authority and incomplete scans MUST be represented explicitly; consumers MUST NOT substitute another product's authority or infer absence from an unscanned area.

The in-scope product IDs are `lnkcre`, `lnkcrm`, `lnkchatbi`, `lnkreport`, `lnkvision`, `lnkgateway`, and `lnkchat`. `lnkwebsite` website/CMS operations are outside this software product contract.
