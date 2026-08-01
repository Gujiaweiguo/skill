# Contract Notes (v0.2)

> This directory holds reference documents for the **redirect-audit** skill.

## Current state: ready (2026-08-01)

v0.2 — 可执行 workflow 就绪。包含：

- `scripts/audit_runner.py`：核心审计逻辑（cross-check / db-only / nginx-only / online-only）
- `scripts/validate.py`：payload 校验器
- `scripts/synthetic_runner.py`：合成测试 runner
- `tests/`：106 tests（validation + synthetic runner + audit runner + CLI）
- `fixtures/synthetic-fixture.json`：合成测试数据

## References

- `payload-v1.md` — payload schema (when validated, during pilot)
- `runtime-artifacts-v1.md` — artifact path conventions (when validated, during pilot)
- `troubleshooting.md` — operational pitfalls (after pilot)

## Cross-references

- Skill portfolio: `/opt/code/lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md`
- Dogfooding narrative: `/opt/code/lnkwebsite/docs/strategy/dogfooding/narrative.md`
- Phase 5 mapping plan: `/opt/code/lnkwebsite/docs/strategy/dogfooding/phase5-mapping-plan.md`
- OpenSpec change: `define-website-operations-skill-portfolio`

## Status history

- 2026-07-24: contract skeleton created (status=planned)
- 2026-08-01: executable workflow added, status promoted planned → ready
