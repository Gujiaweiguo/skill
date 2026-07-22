---
contract_version: "1.0.0"
content_id: "<content-id>"
selected_pattern: "<pattern-id: term-entry | industry-insight>"
audience: "<primary-audience>"
---

# Research Pack: <working title>

## Research question

<What must this content answer? Frame as the question the target reader would ask.>

## Evidence

| Claim ID | Proposed claim | Source | Exact location | Evidence grade | claim_type | Allowed use |
|---|---|---|---|---|---|---|
| C-01 | <factual claim> | <source path or URL> | <page/section/para> | A | fact | <how this claim may appear in the Pattern Draft> |
| C-02 | <contextual claim> | <source> | <location> | B | context | <usage> |
| C-03 | <quotation> | <source> | <location> | A | quote | <usage> |

### Evidence grades (per Editorial Policy v1 §4.1)

| Grade | Definition | Client-facing use |
|---|---|---|
| **A** | Primary source: peer-reviewed paper, official documentation, legal/regulatory document, named customer authorization | MAY appear as factual basis |
| **B** | Secondary source: authoritative industry analysis, established vendor documentation, named expert publication | MAY appear as factual basis (multi-source preferred) |
| **C** | Illustrative: industry survey, conference talk, blog post from recognized practitioner | MAY appear in explanatory/contextual text; MUST NOT be sole basis for a load-bearing claim |
| **D** | Internal product mapping: LangChat's own product model, capability definitions | MAY appear in product-relevance sections; MUST be labeled as product suggestion, not industry fact |

### claim_type values

| Value | Meaning |
|---|---|
| `fact` | A verifiable factual statement backed by evidence |
| `context` | Background or framing information |
| `quote` | Direct quotation from a source |
| `product_mapping` | LangChat product model mapping (not industry fact) |

## Gaps and constraints

List any of the following:
- **Missing evidence**: claim that needs a stronger source before it can be used
- **Uncertainty**: claim where sources disagree or evidence is ambiguous
- **Prohibited extrapolation**: inference that MUST NOT be drawn beyond what sources support
- **Data freshness**: source may be outdated; note verification date

## Generation handoff

- Selected pattern: `<term-entry | industry-insight>`
- Core claims ready: `yes/no`
- Blocking gaps: `<none or list>`
- Claims requiring multi-source confirmation: `<list or none>`
