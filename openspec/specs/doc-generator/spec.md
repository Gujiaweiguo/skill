### Requirement: Pipeline Phase Ordering

The skill SHALL execute the documentation pipeline in fixed phase order: **P0 环境检测 → P1 应用结构发现 → P2 截图规划 → P2.5 登录凭据 → P3 截图执行 → P4 渲染输出 → P5 交互确认**. The agent SHALL NOT skip P0 (环境检测) under any circumstance. Phases P1-P5 MAY be skipped only when explicitly allowed by graceful degradation rules.

#### Scenario: Normal full pipeline execution

- **WHEN** user invokes the skill against a running SPA with valid `$USERGUIDE_BASE` configured
- **THEN** the agent executes P0 through P5 in order, producing all output files in `$USERGUIDE_BASE/{name}/`

#### Scenario: P0 failure aborts pipeline before any side effect

- **WHEN** P0 detects a blocking environment issue (e.g., `$USERGUIDE_BASE` unset AND no default path writable)
- **THEN** the agent aborts before P1, creates no directories, and prints actionable guidance to the user

#### Scenario: Degraded pipeline still completes P4/P5

- **WHEN** P3 cannot execute (Playwright MCP unavailable) but P0-P2 succeeded
- **THEN** the agent skips P3, proceeds to P4 with placeholder screenshots, and completes P5 with a degradation warning in the final summary

### Requirement: UserGUIDE_BASE Environment Variable

The skill SHALL read `$USERGUIDE_BASE` to determine the documentation root. When unset, the skill SHALL default to `/opt/code/docs/lanlnk/UserGuide/`. The skill SHALL NOT write any documentation output outside `$USERGUIDE_BASE`.

#### Scenario: Env var explicitly set

- **WHEN** `$USERGUIDE_BASE=/some/path` is set in the environment
- **THEN** all input is read from `$USERGUIDE_BASE/_input/{name}/` and all output is written to `$USERGUIDE_BASE/{name}/`

#### Scenario: Env var unset uses default

- **WHEN** `$USERGUIDE_BASE` is not set
- **THEN** the skill uses `/opt/code/docs/lanlnk/UserGuide/` and informs the user that the default is being used

### Requirement: Software Name Discovery

The skill SHALL discover the software name by trying, in order: (1) `name` field of `package.json` (with `@scope/` prefix stripped); (2) source project directory name; (3) explicit name in user's invocation; (4) interactive prompt to user. The discovered name SHALL be normalized to directory-safe kebab-case (lowercase, non-alphanumerics replaced with `-`, no leading/trailing `-`).

#### Scenario: Name from package.json

- **WHEN** source project's `package.json` has `"name": "mysqlbot"`
- **THEN** the skill uses `mysqlbot` as the software name without prompting

#### Scenario: Scoped package name stripped

- **WHEN** `package.json` has `"name": "@myorg/mysql-bot"`
- **THEN** the skill uses `mysql-bot` (scope stripped, kebab-case preserved)

#### Scenario: Name with spaces normalized

- **WHEN** user invokes with "为 MySQL Bot v2 生成手册" and no `package.json` exists
- **THEN** the skill uses `mysql-bot-v2` as the directory name

#### Scenario: Fallback to interactive prompt

- **WHEN** no `package.json` exists, the source directory name is generic (e.g., `src`, `app`, `code`), and the user did not specify a name
- **THEN** the agent asks the user for the software name before proceeding

### Requirement: Input/Output Directory Layout

The skill SHALL use a separated layout: inputs under `$USERGUIDE_BASE/_input/{name}/` and outputs under `$USERGUIDE_BASE/{name}/`. Inputs include `references/` (any-format files + `urls.txt`) and optional `config.yaml`. Outputs include `操作手册.md`, `chunks.jsonl`, `llms.txt`, `manifest.json`, `analysis.json`, and `imgs/`.

#### Scenario: Input references directory

- **WHEN** the agent reads user-provided reference materials
- **THEN** they are stored under `$USERGUIDE_BASE/_input/{name}/references/`, never inside the output directory

#### Scenario: Output artifacts isolated from inputs

- **WHEN** the agent renders outputs
- **THEN** no output file is written under `_input/`, and no input file is read from `{name}/` (except `analysis.json` and `manifest.json` for incremental updates)

### Requirement: First-Run Auto-Creation of Input Directory

On the first invocation for a software name, the skill SHALL create `$USERGUIDE_BASE/_input/{name}/references/` automatically. The skill SHALL NOT require the user to pre-create any directory.

#### Scenario: First run creates input directory

- **WHEN** the skill runs for `mysqlbot` and `$USERGUIDE_BASE/_input/mysqlbot/` does not exist
- **THEN** the agent creates `$USERGUIDE_BASE/_input/mysqlbot/references/` before P1 and informs the user of the path

#### Scenario: Pre-staged input directory respected

- **WHEN** `$USERGUIDE_BASE/_input/mysqlbot/references/` already exists with files
- **THEN** the agent uses those references without prompting the user to re-provide them

### Requirement: Incremental Update Mode

When `$USERGUIDE_BASE/{name}/analysis.json` already exists, the skill SHALL prompt the user to choose between "full regeneration" and "incremental update". Incremental mode SHALL reuse prior `analysis.json`, `manifest.json`, and `imgs/` for unchanged routes, regenerating only new or changed routes.

#### Scenario: Existing analysis triggers mode prompt

- **WHEN** `$USERGUIDE_BASE/mysqlbot/analysis.json` exists at P0
- **THEN** the agent asks the user: full regeneration or incremental update

#### Scenario: Incremental mode reuses unchanged screenshots

- **WHEN** user selects incremental mode and P1 detects that route `/users` is unchanged from prior `analysis.json`
- **THEN** the agent does not re-screenshot `/users`, reuses the prior `imgs/users_*.png`, and only regenerates the final markdown output

#### Scenario: Force-full flag bypasses prompt

- **WHEN** user invokes with `--full` flag
- **THEN** the skill performs full regeneration without prompting, even if `analysis.json` exists

### Requirement: Graceful Degradation

The skill SHALL produce a usable manual even when components are unavailable. When the builtin `playwright` skill cannot be loaded, or the dev server is unreachable, or individual pages time out, the skill SHALL continue and mark affected sections with explicit warnings in the output.

#### Scenario: Playwright skill unavailable

- **WHEN** P0 cannot load the builtin `playwright` skill (MCP not configured)
- **THEN** the agent skips P2.5/P3, runs P4 with `manifest.json` containing `null` entries for all screenshots, and the final `操作手册.md` shows "⚠️ 截图失败：Playwright 不可用" placeholders

#### Scenario: Dev server unreachable

- **WHEN** P0 cannot reach the dev server on any probed port (5173/3000/8080) and no `--port` is provided
- **THEN** the agent aborts with actionable guidance: "请启动 dev server（如 `npm run dev`）后重试，或用 `--port <N>` 指定端口"

#### Scenario: Individual page timeout does not abort pipeline

- **WHEN** P3 encounters a timeout or selector-not-found on route `/settings`
- **THEN** the agent logs the failure in `manifest.json`, marks `/settings` screenshots as failed, and continues with the next route

### Requirement: Cross-Skill Coordination via Builtin Playwright

The skill SHALL integrate with the builtin `playwright` skill via artifact-passing: the agent loads `skill(name="playwright")` during P3 and feeds it actions from `screenshot-plan.json`. The skill SHALL NOT bundle or install Playwright itself.

#### Scenario: Loading playwright skill mid-execution

- **WHEN** the agent reaches P3 with a valid `screenshot-plan.json`
- **THEN** the agent invokes `skill(name="playwright")` and follows its instructions to execute each action in the plan

#### Scenario: Screenshot plan is the only contract surface

- **WHEN** the builtin `playwright` skill's API evolves
- **THEN** the doc-generator skill continues to function as long as `screenshot-plan.json` schema remains compatible; no other integration point exists

### Requirement: Skill Installation Layout

The skill SHALL be installed at `skills/docs/doc-generator/` with a symlink at `.opencode/skills/doc-generator` pointing to `../../skills/docs/doc-generator`. The `skills/docs/` category directory SHALL be created if it does not exist.

#### Scenario: Symlink uses relative path

- **WHEN** the skill is installed
- **THEN** `.opencode/skills/doc-generator` is a symlink with target `../../skills/docs/doc-generator` (relative, matching the repo convention)

#### Scenario: Existing symlink not duplicated

- **WHEN** the skill is re-installed and `.opencode/skills/doc-generator` already exists
- **THEN** the install process skips symlink creation without error
