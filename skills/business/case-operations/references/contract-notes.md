# Contract Notes

> Case operations skill — v0.2 可执行 workflow 就绪。

## Status history

- 2026-07-24: contract skeleton created (status=planned)
- 2026-08-01: executable workflow added — screening / validate / generate / import CLI, templates, references, 81 tests passing. status 保持 planned（业务方书面同意待落实）

## Cross-references

- Skill portfolio: `/opt/code/lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md`
- Dogfooding narrative: `/opt/code/lnkwebsite/docs/strategy/dogfooding/narrative.md`
- Phase 5 mapping plan: `/opt/code/lnkwebsite/docs/strategy/dogfooding/phase5-mapping-plan.md`
- OpenSpec change: `define-website-operations-skill-portfolio`

## Shared modules

- `content-operations/scripts/case_payload.py` — core payload parsing + forbidden terms
- `content-operations/scripts/validate_case.py` — CLI validator (shared)
- `case-operations/scripts/content_ops_loader.py` — runtime loader for shared parser
