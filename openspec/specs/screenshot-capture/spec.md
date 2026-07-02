### Requirement: Plan Generation from Analysis

During P2, the skill SHALL generate `screenshot-plan.json` from `analysis.json`. The plan SHALL be a list of page-level tasks, each containing `id`, `page_title`, `url`, `requires_auth` (bool), and an ordered `actions[]` list. Each action SHALL have a `type` from the fixed set `{navigate, wait, screenshot, fill, click, hover, scroll, select, assert}`.

#### Scenario: Plan covers every accessible route

- **WHEN** `analysis.json.routes[]` contains 10 accessible routes
- **THEN** `screenshot-plan.json` contains 10 page-level tasks, one per route (auth-required routes additionally reference the auth pre-step)

#### Scenario: Action ordering matches inferred flow

- **WHEN** a route's `flows[]` describes `[open_create_modal, fill_form, submit, verify_list_updated]`
- **THEN** the corresponding page task's `actions[]` includes screenshot actions interspersed with the flow's actions (e.g., screenshot-after-load, screenshot-after-modal-open, screenshot-after-submit)

### Requirement: Locator Strategy (Text, Role, Placeholder)

Every action in `screenshot-plan.json` that targets a DOM element SHALL use text-based, role-based, or placeholder-based locators. The plan SHALL NOT contain CSS selectors (`.`-prefixed classes, `#`-prefixed ids) or XPath expressions as primary locators.

#### Scenario: Button targeted by text

- **WHEN** an action clicks the "新建" button
- **THEN** the action is `{type: "click", locator: {strategy: "text", value: "新建"}}`

#### Scenario: Input targeted by placeholder

- **WHEN** an action fills the username field
- **THEN** the action is `{type: "fill", locator: {strategy: "placeholder", value: "用户名"}, value: "<from .auth.json>"}`

#### Scenario: Button targeted by role+name as fallback

- **WHEN** a button has no visible text but has `aria-label="关闭"`
- **THEN** the action is `{type: "click", locator: {strategy: "role", role: "button", name: "关闭"}}`

### Requirement: Action Type Support

The plan SHALL support action types covering the most common SPA interactions. Each type SHALL have a defined schema in `references/screenshot-plan-schema.md`. Unsupported action types SHALL cause validation to fail at P2 before reaching P3.

#### Scenario: Supported action types enumerated

- **WHEN** the renderer or playwright skill parses `screenshot-plan.json`
- **THEN** only these `type` values are valid: `navigate`, `wait`, `screenshot`, `fill`, `click`, `hover`, `scroll`, `select`, `assert`

#### Scenario: Unknown action type rejected at P2

- **WHEN** the agent emits an action `{type: "drag_drop", ...}` not in the supported set
- **THEN** P2 validation fails with the message "Unsupported action type: drag_drop" before any P3 execution

### Requirement: Authenticated Context Reuse

When `analysis.json.auth` is non-null, the plan SHALL include a single auth pre-step (the first task in the plan) that logs in once. All subsequent tasks SHALL reuse the authenticated browser context (same cookies/localStorage), avoiding repeated logins.

#### Scenario: Auth pre-step appears once

- **WHEN** `analysis.json.auth` is populated and 8 routes require auth
- **THEN** `screenshot-plan.json.tasks[0]` is the auth task (navigate to login, fill credentials, click submit, assert dashboard visible), and `tasks[1..8]` reference the same browser context without re-authenticating

#### Scenario: No auth means no auth task

- **WHEN** `analysis.json.auth` is null
- **THEN** `screenshot-plan.json.tasks[]` has no auth task and no action has `requires_auth: true`

### Requirement: Credential Persistence

User-provided credentials SHALL be stored at `$USERGUIDE_BASE/_input/{name}/.auth.json` (gitignored via the skill's documentation). The skill SHALL NOT log, echo, or write credentials to any other location. Credentials SHALL be re-used on subsequent runs without re-prompting.

#### Scenario: First-run credential prompt

- **WHEN** P2.5 runs and `.auth.json` does not exist
- **THEN** the agent prompts the user for username/password, writes them to `_input/{name}/.auth.json` with restrictive permissions (mode 0600), and proceeds

#### Scenario: Subsequent run reuses credentials

- **WHEN** P2.5 runs and `.auth.json` exists with valid credentials
- **THEN** the agent does not prompt; P3 reads credentials directly from the file

#### Scenario: No-auth flag bypasses credential prompt

- **WHEN** user invokes with `--no-auth` flag
- **THEN** the skill skips P2.5 entirely, marks auth-required routes as inaccessible, and proceeds to P3 for public routes only

### Requirement: Playwright Skill Loading

During P3, the skill SHALL load the builtin `playwright` skill via `skill(name="playwright")` and follow its instructions to execute each action in `screenshot-plan.json`. The skill SHALL NOT call Playwright Python libraries directly.

#### Scenario: Builtin playwright skill is the executor

- **WHEN** P3 begins with a valid `screenshot-plan.json`
- **THEN** the agent invokes `skill(name="playwright")` and feeds it actions sequentially, capturing screenshots to `$USERGUIDE_BASE/{name}/imgs/`

#### Scenario: Playwright skill failure surfaces actionable error

- **WHEN** loading `skill(name="playwright")` fails (e.g., MCP not configured)
- **THEN** the agent aborts P3, records the failure in `manifest.json.executor_error`, and triggers graceful degradation in P4

### Requirement: Single-Page Failure Tolerance

When an action within a page task fails (selector timeout, navigation error, assertion failure), the skill SHALL record the failure for that action, skip remaining actions in the same task, and continue with the next page task. The skill SHALL NOT abort the entire P3 phase on a per-page failure.

#### Scenario: Selector timeout recorded and skipped

- **WHEN** action `{type: "click", locator: {strategy: "text", value: "不存在的按钮"}}` times out
- **THEN** `manifest.json.tasks[<page_id>].actions[<i>].status === "failed"` with the timeout error, remaining actions in the same task have `status === "skipped"`, and the next page task executes normally

#### Scenario: Navigation error contains URL

- **WHEN** a `navigate` action fails for `http://localhost:5173/missing-route`
- **THEN** the manifest entry includes `error: "navigation_failed"` and `url: "http://localhost:5173/missing-route"` for diagnosis

### Requirement: Execution Manifest Logging

P3 SHALL produce `manifest.json` recording every executed action with its outcome. The manifest SHALL include per-task and per-action status (`success` / `failed` / `skipped`), elapsed time, screenshot paths (when applicable), and resolved locators (the actual locator used, in case fallback strategies were applied).

#### Scenario: Successful action recorded

- **WHEN** a `screenshot` action succeeds, writing to `imgs/users_2_create_modal.png`
- **THEN** `manifest.json` entry contains `{action_id: "...", type: "screenshot", status: "success", output_path: "imgs/users_2_create_modal.png", elapsed_ms: <number>}`

#### Scenario: Locator fallback recorded

- **WHEN** primary locator `{strategy: "text", value: "保存"}` fails and the fallback `{strategy: "role", role: "button", name: "保存"}` succeeds
- **THEN** the manifest entry contains both `primary_locator` and `resolved_locator` so reviewers can see the fallback that worked

### Requirement: Screenshot Naming Convention

Screenshot files SHALL be named `{module_slug}_{step_index}_{description_slug}.png` where `module_slug` is the kebab-cased route title, `step_index` is the action's position within the page task, and `description_slug` is a short kebab-case description from the action's `name` field.

#### Scenario: Naming follows convention

- **WHEN** the "用户管理" page task has a screenshot action at step 2 with `name: "新建用户弹窗"`
- **THEN** the screenshot file is `imgs/用户管理_2_新建用户弹窗.png` (or its slug-normalized form `imgs/user-management_2_create-modal.png` when ASCII-only filesystems require it)

#### Scenario: Naming collision avoided

- **WHEN** two screenshot actions in the same task would produce the same filename
- **THEN** the second file is suffixed with `_2` (e.g., `users_2_create_2.png`) and the manifest records both with distinct `output_path`s
