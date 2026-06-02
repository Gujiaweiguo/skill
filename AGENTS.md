# AGENTS.md

## Repository Purpose

This is an **OpenCode skills repository** containing OpenSpec workflow skills. It defines structured workflows for managing software changes through a spec-driven process: proposal → specs → design → tasks → implementation → archive.

## Critical Context

### This is NOT a typical application codebase

This repo contains **skill definitions** (markdown files) and **command configurations** for OpenCode. There is no runtime code to build, test, or deploy. The "code" is the workflow logic embedded in skill markdown files.

### The OpenSpec Workflow

All skills implement a change management workflow with this artifact sequence:

```
proposal.md → specs/<capability>/spec.md → design.md → tasks.md → [implementation] → archive
```

**Key concept**: Each "change" is a container at `openspec/changes/<name>/` that holds all artifacts for a piece of work.

### Skill ↔ Command Mapping

Each skill in `.opencode/skills/` has a corresponding command in `.opencode/command/`:

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

## File Structure

```
.opencode/
├── skills/                    # Skill definitions (SKILL.md files)
│   ├── openspec-new-change/
│   ├── openspec-continue-change/
│   ├── openspec-ff-change/
│   ├── openspec-apply-change/
│   ├── openspec-verify-change/
│   ├── openspec-archive-change/
│   ├── openspec-bulk-archive-change/
│   ├── openspec-sync-specs/
│   ├── openspec-explore/
│   └── openspec-onboard/
├── command/                   # Command definitions (opsx-*.md files)
├── package.json               # Only dependency: @opencode-ai/plugin
└── node_modules/

openspec/
├── config.yaml                # Schema config (default: spec-driven)
├── specs/                     # Main specs (synced from changes)
└── changes/                   # Active changes
    └── archive/               # Archived changes (YYYY-MM-DD-<name>)
```

## Working with Skills

### Skill File Format

Each skill follows this structure:
```markdown
---
name: openspec-<name>
description: <when to use this skill>
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.1.1"
---

<Instructions with steps, guardrails, and output format>
```

### Key Patterns in Skills

1. **Change selection**: Skills prompt for change selection via `openspec list --json` when ambiguous
2. **Status checking**: `openspec status --change "<name>" --json` returns artifact states
3. **Instructions retrieval**: `openspec instructions <artifact-id> --change "<name>" --json` returns templates and context
4. **Task completion**: Mark tasks as `- [x]` in `tasks.md` after implementation

### Schema System

The default schema is `spec-driven` with artifact sequence: proposal → specs → design → tasks.

Custom schemas can be defined in `openspec/config.yaml`. Check `openspec schemas --json` for available schemas.

## Modification Guidelines

### When editing skills:

- Preserve the YAML frontmatter structure (name, description, metadata)
- Maintain the step-by-step instruction format
- Keep guardrails sections intact
- Do not change the artifact sequence unless intentionally modifying the workflow
- Test changes by running the corresponding command (e.g., edit `openspec-new-change/SKILL.md`, test with `/opsx-new`)

### When adding new skills:

1. Create directory: `.opencode/skills/openspec-<name>/`
2. Add `SKILL.md` with frontmatter and instructions
3. Create corresponding command: `.opencode/command/opsx-<name>.md`
4. Follow existing skill patterns for consistency

### Dependency note:

The only runtime dependency is `@opencode-ai/plugin` (v1.15.13). Skills are markdown-based and do not require compilation.
