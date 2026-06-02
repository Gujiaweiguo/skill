# AGENTS.md

## Repository Purpose

This is an **OpenCode skills repository** combining:

- **OpenSpec workflow skills** (10) — managed change workflow: proposal → specs → design → tasks → implementation → archive
- **Custom skills** (6) under `skills/<category>/` — domain-specific (PPT, PDF, bidding, crawler)
  - `skills/ppt/` — 3 PPT generation skills (ppt-master, frontend-slides, mckinsey-pptx)
  - `skills/pdf/` — pdf-toc-master
  - `skills/bidding/` — bid-doc-master (custom)
  - `skills/crawler/` — winshang-crawler (custom)

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
    └── winshang-crawler/            # Has its own pyproject.toml + uv workflow

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

### uv guidance for Python skills

Skills are not full projects — they don't need `pyproject.toml` or `uv.lock`. When declaring Python dependencies, use the **Optional uv bootstrap** pattern in `compatibility`:

```yaml
compatibility: >
  Requires Python 3.9+ with <deps>.

  Optional: bootstrap an isolated environment with uv (recommended for one-off runs):
  ```bash
  uv venv && uv pip install <deps>
  source .venv/bin/activate
  ```
  Otherwise `pip install <deps>` into your system Python works equally well.
```

This preserves pip as a fully supported option while giving new users a one-liner to start. Exception: `winshang-crawler` has its own `pyproject.toml` and is meant to be run with `uv run` directly.

### Dependency note:

The only OpenCode runtime dependency is `@opencode-ai/plugin` (v1.15.13). Skills are markdown-based and do not require compilation.
