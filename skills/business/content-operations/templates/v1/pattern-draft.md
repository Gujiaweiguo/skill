---
contract_version: "1.0.0"
content_id: "<content-id>"
pattern: "<pattern-id: term-entry | industry-insight>"
research_pack: "<absolute path under CONTENT_OUTPUT_BASE/research-packs>"
review_state: "pending"
---

# <Article title>

<Pattern Draft body in Markdown. Derive content ONLY from the linked Research Pack. Do not introduce new claims.>

## Section structure

Choose the outline matching the selected pattern. Sections are guidelines, not rigid templates — adapt to the topic.

### term-entry pattern

For explanatory articles that define a concept for enterprise decision-makers.

```
## 定义 (Definition)
  What it is, stated precisely. Cite the authoritative source.

## 边界 (Boundary)
  What it is NOT. Distinguish from commonly confused concepts.

## 常见误解 (Misconceptions)
  2-3 frequent misunderstandings, each corrected with evidence.

## 与 LangChat 的关联 (Capability mapping)
  How this concept maps to LangChat platform capabilities.
  MUST label as "product mapping, not industry definition" (claim_type=product_mapping).

## 证据来源 (Evidence)
  Name the authoritative sources. Client-facing version — do not dump full citation list.
  Keep to 4-6 named sources with one-line description each.

## 人机边界 (Human-machine boundary) [if applicable]
  What AI can do vs. what requires human judgment for this concept.
```

### industry-insight pattern

For analysis articles about an industry trend or business problem.

```
## 行业变化 (Industry shift)
  What is changing and why it matters now.

## 企业痛点 (Enterprise pain points)
  Specific problems the target reader faces.

## AI 机会 (AI opportunity)
  How AI addresses the pain points. Tie to specific capabilities.

## 实施路径 (Implementation path)
  Practical steps or phases. Avoid vague "leverage AI" language.

## 案例 (Case reference) [if evidence available]
  Concrete example or client scenario. Must have authorization or be anonymized.
```

## Source notes

Map each Research Pack claim to where it appears in this draft:

- C-01: §<section> (<how it's used>)
- C-02: §<section> (<how it's used>)

## Items requiring review

List anything a reviewer should check:
- Claims with weak evidence (grade C or single-source B)
- Wording that might need brand or legal review
- Capability mapping phrasing (product suggestion vs. industry fact)
- Section balance (too long/short for the target audience)
