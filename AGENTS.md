# AGENTS.md

## Repository Purpose

OpenCode skills repository: **skill definitions** (markdown) + **command configurations**. No runtime app code. Two categories:

- **OpenSpec skills** (10) — workflow: proposal → specs → design → tasks → archive. Bundled upstream artifacts, **do not edit**. Tracked in `.opencode/skills/openspec-*/`.
- **Custom skills** (10) under `skills/<category>/` — domain tools (PPT, PDF, Word, bidding, crawler, importer, etc.)

## File Structure

```
skills/                              # ACTUAL files — edit here
├── ppt/                             # 3 PPT skills (Node.js + pptxgenjs)
│   ├── ppt-master/
│   ├── frontend-slides/
│   └── mckinsey-pptx/
├── pdf/pdf-toc-master/              # Python, uv-managed
├── business/                        # 4 business skills
│   ├── bid-doc-master/              # Python, uv-managed
│   ├── company-intro-generator/     # Python, uv-managed
│   ├── material-importer/           # Python, uv-managed
│   └── project-proposal-generator/  # Python, uv-managed
├── crawler/winshang-crawler/        # Python, self-contained (src/, pyproject.toml)
├── word/word-master/                # Python, uv-managed (python-docx)
├── daily/crela-daily-skill/          # CRON-based daily report (SKILL.md)

.opencode/                           # OpenCode entry point
├── skills/                          # Symlinks to skills/<category>/<name>/
│   ├── openspec-*/ (10 dirs)        # REAL dirs, NOT symlinks — DO NOT EDIT
│   └── custom-skills/               # Symlinks into skills/<category>/
├── command/                         # 10 opsx-*.md commands
├── package.json                     # @opencode-ai/plugin only
└── .gitignore                       # Excludes node_modules, package json/lock

openspec/
├── config.yaml                      # schema: spec-driven
├── specs/                           # Main specs (synced from changes)
└── changes/                         # Active changes → archive/
```

## CRITICAL: Broken Symlinks & Unlinked Skills (RESOLVED)

All 6 skills with broken/missing symlinks have been fixed:
- `bid-doc-master` → was pointing to `skills/bidding/` (nonexistent), now points to `skills/business/` ✅
- `company-intro-generator`, `material-importer`, `project-proposal-generator` → symlinks created ✅
- `word-master` → symlink created ✅
- `crela-daily-skill` → directory created + symlinked, converted from YAML to SKILL.md ✅

## OpenSpec Workflow

```
proposal.md → specs/<capability>/spec.md → design.md → tasks.md → [implementation] → archive
```

Each "change" = `openspec/changes/<name>/` holding all artifacts. `openspec` CLI v1.1.1 available on PATH.

| Step | Command | What it does |
|------|---------|-------------|
| Start | `/opsx-new` | Scaffold new change directory |
| Next | `/opsx-continue` | Create next artifact in sequence |
| Fast-forward | `/opsx-ff` | Generate all artifacts at once |
| Implement | `/opsx-apply` | Execute tasks from tasks.md |
| Verify | `/opsx-verify` | Validate implementation vs artifacts |
| Archive | `/opsx-archive` | Finalize and archive |
| Bulk archive | `/opsx-bulk-archive` | Archive multiple changes |
| Sync specs | `/opsx-sync` | Delta specs → main specs |
| Explore | `/opsx-explore` | Think through problems (no code) |
| Onboard | `/opsx-onboard` | Guided walkthrough |

**Key gotchas**:
- `openspec list --json` to list changes
- `openspec status --change "<name>" --json` for artifact states
- `openspec instructions <artifact-id> --change "<name>" --json` for templates
- Mark tasks `- [x]` in `tasks.md` after implementing
- Transient artifacts (`proposal.md`, `design.md`, `tasks.md`, `specs/`) are gitignored
- Archived changes are at `openspec/changes/archive/`

## Custom Skill Notes

### Skill File Format
```markdown
---
name: <skill-name>
description: <when to trigger>
compatibility: <runtime requirements>  # optional
---

<step-by-step instructions + guardrails>
```

### Verify Frontmatter — Don't Trust It Blindly
Cross-check `compatibility` against files-on-disk. The `bid-doc-master` previously claimed "Python 3.9+ or Node.js" but only shipped Python scripts — that got corrected. **Check**:
1. List `skills/<category>/<skill>/` for `package.json`, `pyproject.toml`, `*.js`, `*.ts`
2. Grep SKILL.md for actual tool/command names
3. Match `compatibility` claims to real files

### Python Skills (uv-only)
All Python skills use **uv** exclusively (no pip). Two patterns:

**With runnable code** (pdf-toc-master, winshang-crawler, word-master):
```
cd skills/<cat>/<skill> && uv sync && uv run <entry-point>
```

**Dependencies only** (bid-doc-master, material-importer, etc.):
```
cd skills/<cat>/<skill> && uv sync && source .venv/bin/activate
```

### PPT Skills (Node.js)
ppt-master, frontend-slides, mckinsey-pptx need `pptxgenjs` (declared in `skills/ppt/ppt-master/package.json`). Generate `.pptx` programmatically.

### External Data: LANLNK_BASE
- `config/lanlnk.yaml` defines a materials directory structure
- Set `export LANLNK_BASE=/opt/code/docs/lanlnk` (used by bid-doc-master, material-importer, etc.)
- `.trae/rules/project_rules.md` also documents this
- Three-tier input structure: `incoming/` (source files) → `raw/` (converted artifacts) → `materials/` (structured output)

### Shared Domain Tags
- `skills/business/material-importer/references/domain-tags.md` defines the canonical business-line tags (商管/会员/AI客服/AI问数/通用)
- `company-intro-generator` shares the same tag system — update both if changing tags
- Tags are customizable; modify the `references/domain-tags.md` file to add/remove business lines

### CRON Skill (crela-daily-skill)
- `skills/daily/crela-daily-skill/SKILL.md` — converted from original YAML format to standard SKILL.md
- Scheduled CRON `30 8 * * 1-5` Asia/Shanghai for daily commercial real estate reports
- Uses `web_search` (bing, zh-CN). The CRON trigger is handled by external scheduler, not SKILL.md itself.

## Editing Rules

1. **Edit under `skills/<category>/<name>/`** — `.opencode/skills/` is symlinks (except openspec-* dirs). Never edit symlink targets.
2. **OpenSpec skills are read-only** — upgrades come from upstream. Edit only if intentionally modifying the workflow.
3. **New custom skill**: create `skills/<category>/<name>/SKILL.md` + `pyproject.toml` if Python → `ln -s ../../skills/<category>/<name> .opencode/skills/<name>`
4. **Python always uses uv** + `pyproject.toml` (no pip, no requirements.txt)
5. **No CI, no linting, no formatter config** — repo is markdown-weighted, no unified build

## Inventory Summary (21 skills total)

| Name | Category | Source | Status |
|------|----------|--------|--------|
| openspec-new-change | OpenSpec | `.opencode/skills/` | ✅ symlinked |
| openspec-continue-change | OpenSpec | `.opencode/skills/` | ✅ |
| openspec-ff-change | OpenSpec | `.opencode/skills/` | ✅ |
| openspec-apply-change | OpenSpec | `.opencode/skills/` | ✅ |
| openspec-verify-change | OpenSpec | `.opencode/skills/` | ✅ |
| openspec-archive-change | OpenSpec | `.opencode/skills/` | ✅ |
| openspec-bulk-archive-change | OpenSpec | `.opencode/skills/` | ✅ |
| openspec-sync-specs | OpenSpec | `.opencode/skills/` | ✅ |
| openspec-explore | OpenSpec | `.opencode/skills/` | ✅ |
| openspec-onboard | OpenSpec | `.opencode/skills/` | ✅ |
| ppt-master | PPT | `skills/ppt/` | ✅ symlinked |
| frontend-slides | PPT | `skills/ppt/` | ✅ symlinked |
| mckinsey-pptx | PPT | `skills/ppt/` | ✅ symlinked |
| pdf-toc-master | PDF | `skills/pdf/` | ✅ symlinked |
| winshang-crawler | Crawler | `skills/crawler/` | ✅ symlinked |
| bid-doc-master | Business | `skills/business/` | ✅ (was broken, fixed) |
| company-intro-generator | Business | `skills/business/` | ✅ (was missing, created) |
| material-importer | Business | `skills/business/` | ✅ (was missing, created) |
| project-proposal-generator | Business | `skills/business/` | ✅ (was missing, created) |
| word-master | Word | `skills/word/` | ✅ (was missing, created) |
| crela-daily-skill | Daily | `skills/daily/crela-daily-skill/` | ✅ converted from YAML to SKILL.md |
