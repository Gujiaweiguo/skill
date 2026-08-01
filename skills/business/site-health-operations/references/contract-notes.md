# Reference Notes

> This directory holds reference documents for the **site-health-operations** skill.

## Current artifacts (v0.2)

- `config/thresholds.json` — per-site alert threshold configuration
- `fixtures/synthetic-fixture.json` — synthetic test data for CLI and test runner
- `SKILL.md` — full workflow documentation with 5 check dimensions

## Planned references (when skill promotes to pilot)

- `payload-v1.md` — payload schema (when validated in production)
- `runtime-artifacts-v1.md` — artifact path conventions (when validated)
- `troubleshooting.md` — operational pitfalls (after pilot)

## Architecture overview

```
HealthChecker (orchestrator)
├── OnlineCheckerProtocol → CurlOnlineChecker (curl subprocess)
├── SSLCheckerProtocol → SSLCertChecker (ssl + socket)
├── ServiceCheckerProtocol → SystemdServiceChecker (systemctl subprocess)
└── ResourceCheckerProtocol → SystemResourceChecker (df + /proc/meminfo)
```

All checkers are dependency-injectable for test isolation.

## Cross-references

- Skill portfolio: `/opt/code/lnkwebsite/docs/strategy/dogfooding/skill-portfolio.md`
- Dogfooding narrative: `/opt/code/lnkwebsite/docs/strategy/dogfooding/narrative.md`
- Phase 5 mapping plan: `/opt/code/lnkwebsite/docs/strategy/dogfooding/phase5-mapping-plan.md`
- OpenSpec change: `define-website-operations-skill-portfolio`

## Status history

- 2026-07-24: contract skeleton created (status=planned)
- 2026-08-01: executable workflow added — health_check.py, thresholds.json, 61 new tests (status=planned, blocked on business decision)
