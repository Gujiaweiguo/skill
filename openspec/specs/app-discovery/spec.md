### Requirement: Runtime Structure Probing

During P1, the skill SHALL probe the running application via Playwright to discover its actual navigation structure: visible menu items, sidebar entries, top-bar links, and router state. The skill SHALL NOT rely solely on source code parsing to enumerate routes.

#### Scenario: Sidebar menu discovery

- **WHEN** the agent visits the application's root URL and a sidebar with menu items (e.g., 用户管理、订单、设置) is rendered
- **THEN** the agent extracts each menu item's text and target route into `analysis.json.routes[]`

#### Scenario: Hidden routes revealed via router state

- **WHEN** the application has routes not exposed in any visible menu (e.g., `/profile` reachable only via avatar click)
- **THEN** the agent reads the SPA's router state (Vue Router / React Router global instance) to enumerate registered routes and includes them in `analysis.json.routes[]` with `discovered_via: "router_state"`

### Requirement: Source Code as Hint

The skill SHALL read source code (router config files, page components, menu definitions) as supplementary hints to identify pages that runtime probing might miss (permission-gated routes, modal-triggered sub-flows, dynamically registered routes).

#### Scenario: Permission-gated route from source hint

- **WHEN** source code defines a route `/admin` with `meta.requiresAdmin: true` and the demo user is not an admin
- **THEN** the agent includes `/admin` in `analysis.json.routes[]` with `accessible: false` and `requires_role: "admin"` so the renderer can document it as "需管理员权限"

#### Scenario: Modal flow identified from source

- **WHEN** source code shows a "新建" button opening a `<el-dialog>` or `<Modal>` component with form fields
- **THEN** the agent records the modal flow in the parent route's `analysis.json.routes[].flows[]` so P2 can plan modal-open screenshots

### Requirement: Interactive Element Extraction

For each route, the skill SHALL extract the list of user-visible interactive elements: buttons, form inputs, tables, dropdowns, links. The skill SHALL capture the element's visible text (or placeholder / aria-label), element type, and primary user-visible action (e.g., `@click` handler name from source hint).

#### Scenario: Button with text content

- **WHEN** the agent encounters `<el-button>新建用户</el-button>` or `<Button>New User</Button>`
- **THEN** `analysis.json.routes[].elements[]` contains `{type: "button", text: "新建用户", action: "open_create_modal"}` (action inferred from handler name)

#### Scenario: Input with placeholder

- **WHEN** the agent encounters `<el-input placeholder="请输入用户名" />`
- **THEN** the element is recorded as `{type: "input", placeholder: "请输入用户名"}`

#### Scenario: Table columns captured

- **WHEN** a page renders a table with columns 用户名、邮箱、角色、操作
- **THEN** `analysis.json.routes[].elements[]` records `{type: "table", columns: ["用户名", "邮箱", "角色", "操作"]}`

### Requirement: User Flow Inference

The skill SHALL infer primary user flows by analyzing the order and dependencies of interactive elements across routes. A flow is a sequence of actions leading to a meaningful outcome (e.g., login → dashboard → click "新建" → fill form → submit → see new entry in list).

#### Scenario: CRUD flow inference

- **WHEN** a list page has "新建" button, the resulting modal has a form with submit button, and the list page has edit/delete actions per row
- **THEN** `analysis.json.routes[].flows[]` includes a flow with steps: `[open_create_modal, fill_form, submit, verify_list_updated]`

#### Scenario: Flow step references elements by stable ID

- **WHEN** the agent emits an inferred flow
- **THEN** each step references the corresponding `elements[]` entry by `element_id` (not by re-stating the text), so downstream P2 plan generation can look up locators

### Requirement: Login Flow Identification

The skill SHALL identify whether the application requires authentication by detecting a login route, login form, or auth redirect. The skill SHALL record the login route, required form fields, and post-login landing route in `analysis.json.auth`.

#### Scenario: Login route detected

- **WHEN** the agent visits the root URL and is redirected to `/login`, or source code defines a `/login` route with a form
- **THEN** `analysis.json.auth` is populated with `{login_route: "/login", form_fields: [{name: "username", placeholder: "用户名"}, {name: "password"}], post_login_route: "/dashboard"}`

#### Scenario: No auth required

- **WHEN** the agent visits the root URL and reaches an authenticated page directly with no redirect
- **THEN** `analysis.json.auth` is `null`, and P2.5 is skipped

### Requirement: Analysis JSON Schema Compliance

The skill SHALL produce `analysis.json` compliant with `references/analysis-schema.md`. The schema SHALL include top-level fields: `app_name`, `version`, `framework_hint`, `dev_server_url`, `routes[]`, `auth`, `generated_at`. Each route entry SHALL include `path`, `title`, `accessible`, `elements[]`, `flows[]`, and `discovered_via`.

#### Scenario: Schema validation passes

- **WHEN** P1 completes for a 5-route application
- **THEN** the resulting `analysis.json` validates against `references/analysis-schema.md` (required fields present, types correct)

#### Scenario: Unknown fields tolerated

- **WHEN** the agent emits additional helper fields not in the schema (e.g., `_debug_notes`)
- **THEN** schema validation passes (the schema permits additional fields), but the renderer ignores them

### Requirement: Framework-Agnostic Operation

The skill SHALL operate on any SPA framework without framework-specific code paths. The agent's reasoning over source code and runtime DOM SHALL treat framework as a hint (`analysis.json.framework_hint`), not as a determinant of pipeline behavior.

#### Scenario: Vue 3 application processed identically

- **WHEN** the target app is a Vue 3 + Element Plus project
- **THEN** P1 produces `analysis.json` with `framework_hint: "vue3"` and the same route/element structure as any other framework

#### Scenario: React application processed identically

- **WHEN** the target app is React + Ant Design
- **THEN** P1 produces `analysis.json` with `framework_hint: "react"` and the same schema as the Vue case

#### Scenario: Unknown framework still processed

- **WHEN** the agent cannot identify the framework (no `package.json` or unrecognized)
- **THEN** P1 proceeds with `framework_hint: "unknown"`, relying entirely on runtime probing

### Requirement: Module Exclusion via Config

When `$USERGUIDE_BASE/_input/{name}/config.yaml` contains `ignore_modules: [...]`, the skill SHALL exclude any route whose title matches an entry in the list from `analysis.json.routes[]` and from all downstream phases.

#### Scenario: Module excluded by config

- **WHEN** `config.yaml` has `ignore_modules: ["实验性功能", "内部调试页"]` and the app has a route titled "实验性功能"
- **THEN** that route is not included in `analysis.json.routes[]` and no screenshots are planned for it

### Requirement: Incremental Diff Detection

When `analysis.json` already exists for the software name, P1 SHALL produce a diff identifying routes that are new, removed, or changed (by comparing path, elements, and flow signatures). The diff SHALL be written to `analysis.json.diff` and used by P2 to scope plan regeneration.

#### Scenario: New route detected

- **WHEN** the prior `analysis.json` had routes `[/login, /dashboard, /users]` and current P1 finds `[/login, /dashboard, /users, /reports]`
- **THEN** `analysis.json.diff.added === ["/reports"]` and `analysis.json.diff.unchanged === ["/login", "/dashboard", "/users"]`

#### Scenario: Element change detected

- **WHEN** route `/users` had 5 elements previously and now has 6 (a new "导出" button)
- **THEN** `/users` is in `analysis.json.diff.changed`, not in `.unchanged`
