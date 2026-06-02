# AGENTS.md

## Repository Purpose

This is an **OpenCode skills repository** combining:

- **OpenSpec workflow skills** (10) — managed change workflow: proposal → specs → design → tasks → implementation → archive
  - **Governance**: NOT managed in this repo. Tracked in `.opencode/skills/openspec-*/` directly as bundled upstream artifacts. Do not edit, do not move, do not copy into `skills/<category>/`. Upgrades come from the OpenSpec project, not from here.
- **Custom skills** (6) under `skills/<category>/` — domain-specific (PPT, PDF, bidding, crawler)
  - `skills/ppt/` — 3 PPT generation skills (ppt-master, frontend-slides, mckinsey-pptx) — downloaded from GitHub, **maintained as a local fork** so prompts/templates can be tuned to team style
  - `skills/pdf/` — pdf-toc-master
  - `skills/bidding/` — bid-doc-master (custom, sole developer)
  - `skills/crawler/` — winshang-crawler (custom, with its own pyproject.toml + uv workflow)

`.opencode/skills/` is the **OpenCode entry point** and contains symlinks to `skills/<category>/`. Always edit files under `skills/<category>/` — never under `.opencode/skills/`.

## Critical Context

### This is NOT a typical application codebase

This repo contains **skill definitions** (markdown files) and **command configurations** for OpenCode. There is no runtime code to build, test, or deploy. The "code" is the workflow logic embedded in skill markdown files.

### File structure (single source of truth)

```
skills/                              # ACTUAL files — edit here
├── ppt/
│   ├── ppt-master/
│   ├── frontend-slides/
│   └── mckinsey-pptx/
├── pdf/
│   └── pdf-toc-master/
├── bidding/
│   └── bid-doc-master/              # Python-only (despite old "or Node.js" wording — was wrong)
└── crawler/
    └── winshang-crawler/            # Self-contained: full Python project (src/, pyproject.toml) managed by uv

.opencode/                           # OpenCode entry — symlinks + commands
├── skills/                          # Symlinks to skills/<category>/<name>/
│   ├── openspec-*/ (10 dirs)        # OpenSpec workflow skills (real dirs)
│   └── ppt-master, frontend-slides, mckinsey-pptx, pdf-toc-master, bid-doc-master, winshang-crawler
│                                    # (all symlinks into skills/<category>/)
├── command/                         # 10 opsx-*.md commands for OpenSpec
├── package.json                     # @opencode-ai/plugin only
└── .gitignore

openspec/
├── config.yaml                      # schema: spec-driven
├── specs/                           # Main specs (synced from changes)
└── changes/                         # Active changes → archive/YYYY-MM-DD-<name>
```

### The OpenSpec Workflow

OpenSpec skills implement a change management workflow with this artifact sequence:

```
proposal.md → specs/<capability>/spec.md → design.md → tasks.md → [implementation] → archive
```

**Key concept**: Each "change" is a container at `openspec/changes/<name>/` that holds all artifacts for a piece of work.

### Skill ↔ Command Mapping

Only OpenSpec skills have commands. Custom skills are triggered by description match.

| Skill | Command | Purpose |
|-------|---------|---------|
| `openspec-new-change` | `/opsx-new` | Create a new change with scaffolded directory |
| `openspec-continue-change` | `/opsx-continue` | Create the next artifact in sequence |
| `openspec-ff-change` | `/opsx-ff` | Fast-forward: create all artifacts at once |
| `openspec-apply-change` | `/opsx-apply` | Implement tasks from a change |
| `openspec-verify-change` | `/opsx-verify` | Verify implementation matches artifacts |
| `openspec-archive-change` | `/opsx-archive` | Archive a completed change |
| `openspec-bulk-archive-change` | `/opsx-bulk-archive` | Archive multiple changes at once |
| `openspec-sync-specs` | `/opsx-sync` | Sync delta specs to main specs |
| `openspec-explore` | `/opsx-explore` | Think through problems (no code changes) |
| `openspec-onboard` | `/opsx-onboard` | Guided onboarding walkthrough |

## Working with Skills

### Skill File Format

Each skill follows this structure:
```markdown
---
name: <skill-name>
description: <when to use this skill>
compatibility: <runtime requirements>  # optional
---

<Instructions with steps, guardrails, and output format>
```

### Key Patterns in OpenSpec Skills

1. **Change selection**: `openspec list --json` when ambiguous
2. **Status checking**: `openspec status --change "<name>" --json` returns artifact states
3. **Instructions retrieval**: `openspec instructions <artifact-id> --change "<name>" --json` returns templates
4. **Task completion**: Mark tasks as `- [x]` in `tasks.md` after implementation

### Schema System

The default schema is `spec-driven` (proposal → specs → design → tasks). Custom schemas live in `openspec/config.yaml`.

## Modification Guidelines

### When editing or analyzing skills — verify before trusting frontmatter

**Files-on-disk beat prose.** Always cross-check the actual skill contents against the frontmatter's compatibility claims before answering questions about a skill:

- `compatibility: ... Python 3.9+ or Node.js ...` can be wrong. Check what tools/scripts the skill actually ships with.
- The bug we hit: `bid-doc-master` declared "Python 3.9+ or Node.js" but only listed Python tools (`python-docx`, `openpyxl`, `markitdown`) and had no Node.js scripts. The "or Node.js" wording was misleading and got removed.

**Practical checklist before claiming a skill is "dual-stack" or "Python-only":**

1. List files in `skills/<category>/<skill>/` — note any `package.json`, `pyproject.toml`, `*.js`, `*.ts`
2. Grep the SKILL.md and reference files for the actual commands and tool names
3. Check if `requires` / `compatibility` lists tools that exist in the repo, not phantom ecosystems

### When editing OpenSpec skills:

- Preserve the YAML frontmatter structure (name, description, metadata)
- Maintain the step-by-step instruction format
- Keep guardrails sections intact
- Do not change the artifact sequence unless intentionally modifying the workflow
- Test changes by running the corresponding command (e.g., edit `openspec-new-change/SKILL.md`, test with `/opsx-new`)

### When editing custom skills:

- **Always edit under `skills/<category>/<skill>/`**, never under `.opencode/skills/` (the latter is symlinks)
- The `compatibility` field is plain prose — keep it accurate to what the skill actually needs
- For Python skills that pull in dependencies, include the **Optional uv bootstrap** block (see "uv guidance" below)
- Test by running the skill's documented commands

### When adding new custom skills:

1. Create directory: `skills/<category>/<skill-name>/`
2. Add `SKILL.md` with frontmatter (name, description, optional compatibility)
3. Create symlink: `ln -s ../../skills/<category>/<skill-name> .opencode/skills/<skill-name>`
4. Update AGENTS.md skill inventory if it's a major addition

### uv strategy for Python skills

All Python skills in this repo now use `pyproject.toml` for deterministic dependency management. The approach varies by skill type:

**Skills WITH Python code** (e.g., `pdf-toc-master`, `winshang-crawler`):

Full project structure with `src/<package>/`, entry points, and build backend:
```
skills/<category>/<skill>/
├── SKILL.md
├── pyproject.toml
├── .gitignore
└── src/<package>/
    ├── __init__.py
    └── *.py
```
Usage: `cd skills/<...>/<skill> && uv sync && uv run <entry-point>`

**Skills WITHOUT Python code but WITH tool dependencies** (e.g., `bid-doc-master`):

`pyproject.toml` declares only dependencies (no build artifacts). Build backend is `setuptools` with no packages:
```toml
[project]
name = "bid-doc-tools"
requires-python = ">=3.10"
dependencies = ["python-docx>=1.1.0", "openpyxl>=3.1.0", ...]

[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"
```
Usage: `cd skills/bidding/bid-doc-master && uv sync && source .venv/bin/activate`

Both patterns replace the old "Optional uv bootstrap" manual `uv pip install` approach.

### Dependency note:

The only OpenCode runtime dependency is `@opencode-ai/plugin` (v1.15.13). Skills are markdown-based and do not require compilation.
