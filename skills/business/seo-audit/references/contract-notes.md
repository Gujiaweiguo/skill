# Contract Notes

> This directory holds reference documents for the **seo-audit** skill.

## Current state: v0.2 — executable workflow ready

- `scripts/seo_audit_runner.py` — production SEO audit engine (HTML parsing, sitemap, robots, JSON-LD validation, meta checks)
- `scripts/validate.py` — payload validation (forbidden jargon, absolute phrases, forbidden actions, fixture mode)
- `scripts/synthetic_runner.py` — synthetic test runner (integrates audit engine for real findings)
- `fixtures/synthetic-fixture.json` — fixture with mock HTML pages for testing
- 121 tests passing

## Planned references (when skill promotes to pilot/validated)

- `payload-v1.md` — payload schema (when validated)
- `runtime-artifacts-v1.md` — artifact path conventions (when validated)
- `troubleshooting.md` — operational pitfalls (after pilot)

## Cross-references

- Skill portfolio: `/opt/code/lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md`
- Dogfooding narrative: `/opt/code/lnkwebsite/docs/strategy/dogfooding/narrative.md`
- Phase 5 mapping plan: `/opt/code/lnkwebsite/docs/strategy/dogfooding/phase5-mapping-plan.md`
- OpenSpec change: `define-website-operations-skill-portfolio`

## Status history

- 2026-07-24: contract skeleton created (status=planned)
- 2026-08-01: executable workflow added — seo_audit_runner.py with 121 tests (status remains planned: GSC < 2 weeks)
