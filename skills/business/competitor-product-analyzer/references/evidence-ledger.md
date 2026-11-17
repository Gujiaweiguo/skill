# Evidence Ledger — 证据台账与置信度规则

本文件定义 `evidence-ledger.json` 的字段规范与置信度判定规则。SKILL.md 的 P3、P7 阶段强制遵循。**本文件是 evidence 相关字段与枚举的唯一权威位置**（evidence_kind / source_type / source_version / source_sha256 / artifact_locator / verification_status / usage_scope / limitations）；SKILL.md 与 capability-schema.md 只保留链接与简例。安装包静态分析与定点逆向的操作纪律见 `static-analysis-and-reverse-engineering.md`。

## 设计原则

**每条能力判断必须可追溯。** 证据台账是本 skill 的质量底线，防止把销售话术当产品事实、把 demo 看不到当竞品没有、把代码存在当功能运行。

## 证据类型与强度

### source_type 强度分级

| source_type | 含义 | 默认强度 | 可达置信度上限 |
|---|---|---|---|
| `manual` | 操作手册 / 功能手册（实施与服务类）| 强 | high（需 ≥2 份互证）|
| `demo-runtime` | demo 运行时探测（亲见）| 强 | high（需 manual 互证）|
| `data-dictionary` | 数据字典 / 表结构 / SQL DDL | 强 | high（数据结构类能力的权威证据）|
| `package-static` | 安装包/交付包静态结构观察（包/模块/DDL/静态路由/配置/部署文件盘点）| 强 | high（**仅限结构层主张**；"已部署/已启用/完整业务能力"需 runtime 或 document 佐证）|
| `code-analysis` | 定点代码/字节码/反编译投影分析（问题驱动的窄深读）| 强 | high（**仅限实现层主张**；"当前环境实际执行/已授权/已启用"需 runtime 佐证）|
| `screenshot` | 截图（已脱敏）| 中 | medium（单一来源）|
| `proposal` | 方案汇报 PPT / 售前方案 | 弱 | medium（汇报会夸大）|
| `sales-material` | 销售策略 / 培训资料 / 话术 | 极弱 | **low（强制上限）** |

**关键规则**：

- `sales-material` 类证据的 capability，`confidence` **强制上限为 low**，无论其他证据多少
- `proposal` 单独存在时置信度上限 medium，需 manual 或 demo-runtime 佐证才能升 high
- `manual` 与 `demo-runtime` 互证（描述同一能力且语义一致、版本/适用范围匹配）可达 high
- 同类型的两份 manual 互证也可达 high（如操作手册 + 功能手册都描述同一字段）
- `package-static` / `code-analysis` 的置信度上限只覆盖其认识论边界**内**的主张；越界主张（已部署、已启用、实际执行、完整业务功能可用）不因证据数量升 high
- 同一安装包内的 DDL、路由和代码可互相补充，但**默认同属一条来源链**（原件 = 该安装包），不因载体/文件不同自动计为独立来源；确系独立原件须正向确认 `independence=independent`

## evidence_kind — 观察来源类别（四类互补，非强弱等级）

`evidence_kind` 回答"这条观察来自哪一类来源"，与 `source_type`（载体形式）正交。四类**互补，不是由弱到强的等级**：

| evidence_kind | 含义 | 典型 source_type |
|---|---|---|
| `document` | 文档记录：手册、方案、厂商说明、PPT、白皮书 | manual / proposal / sales-material / 手册插图 |
| `structure` | 结构观察：数据库结构、静态路由、配置、部署文件等静态结构 | data-dictionary / package-static |
| `runtime` | 运行时观察：授权 demo 中实际观察到的页面与行为 | demo-runtime / demo 截图 |
| `implementation` | 实现观察：相关代码、字节码或反编译投影中的实现 | code-analysis / 反编译界面截图 |

规则：

- **kind 不是强度维度**：不得把 implementation 自动判为"最强证据"，不得把 structure 判为"功能全集"。confidence 仍按决策树（独立互证）判定；来源类别改变不得自动提升 confidence，多一份同源摘要也不升级（来源链折叠规则不变）。
- **截图的 kind 按实际来源判**：demo 截图 = runtime，手册插图 = document，反编译界面截图 = implementation；不一律归为 document。
- 新采集必填；旧条目缺失时按 `unknown` 解释（不推断、不批量回填；人工核实后可单条补写并在 notes 留痕，见「向后兼容」）。

## confidence 判定决策树

```
Step 1: 证据中是否含 sales-material？
    └── 是 → confidence = low（强制）

Step 2: 证据是否只有单一来源？
    └── 是 → confidence = medium

Step 3: 是否有 ≥2 条独立来源描述同一能力且语义一致？
    │  （独立 = 不同原件且经来源链折叠后仍分属不同链，须正向确认 independence=independent；
    │   「不同 source_type / 不同文件 / 不同 evidence_kind」本身不构成独立性依据——
    │   同一安装包内的 DDL、路由与代码默认同链（原件 = 该安装包）；
    │   independence=unknown 的并存证据不计入独立来源数；
    │   两条来源的版本/适用范围（source_version / applies_to）未确认一致时不互证升级，
    │   分别记录、不拼接成同一部署状态）
    ├── 是（且均为独立来源链）→ confidence = high
    └── 独立性无法判定（unknown）→ 不得因并存升级，相关条目进 pending 待核实

Step 4: 仅 proposal 类？
    └── 是 → confidence = medium（不能升 high，除非有 manual/runtime 佐证）

Step 5: 运行时无法复现 manual 描述的能力？
    └── 是 → confidence = low + 进 review（可能是版本差异/权限不足/手册过旧）

Step 6: 资料日期 >2 年？
    └── 是 → confidence 降一级（high→medium, medium→low）+ 标注"基于 YYYY 版"
```

## Evidence 对象字段

`evidence-ledger.json` 顶层：

```json
{
  "schema_version": "1.2",
  "workspace_company": "lanlnk",
  "target_company": "lanlnk",
  "target_product": "lnkcre",
  "competitor_company": "qimao",
  "competitor_product": "旗茂 BS 商管系统",
  "vendor": "qimao",
  "generated_at": "2026-07-06T11:30:00+08:00",
  "evidence": [
    { /* 见下方 Evidence 对象 */ }
  ]
}
```

> **统一竞品关系上下文字段**（workspace_company / target_company / target_product / competitor_company / competitor_product）定义唯一权威源：`skills/business/material-importer/references/material-classification.md`；`vendor` = competitor_company 的 legacy 别名。均为可选增量：旧台账缺失按 `unknown` 解释（目标产品未知 = 无目标产品模式），不批量回填。
> `schema_version=1.1` = 在 1.0 基础上新增可选字段（evidence_kind / source_version / source_sha256 / artifact_locator / verification_status / usage_scope / limitations）与 source_type 新值（package-static / code-analysis）。1.0 台账按「向后兼容」规则可读。

Evidence 对象：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `evidence_id` | string | 是 | 全局唯一，格式 `EV-NNN`（如 `EV-001`）|
| `capability_id` | string | 是 | 关联的 capability_id（如 `CAP-合同管理-新合同申请`）|
| `competitor_company` | string \| null | 否 | 竞品公司（material-classification.md 定义；缺失按台账顶层/unknown 解释，不猜公司）|
| `competitor_product` | string \| null | 否 | 竞品公司的具体产品；缺失 = unknown，不得把竞品公司当产品（禁止猜测回填）|
| `target_company` / `target_product` | string \| null | 否 | 目标公司/目标产品（无目标产品模式 = unknown；缺失按台账顶层解释）|
| `claim` | string | 是 | 一句话声明，如"旗茂支持免租期分段（前 3 个月全免，后续 3 个月半免）"|
| `claim_type` | enum | 是 | `证据` / `判断` / `假设` |
| `evidence_kind` | enum | 新采集必填 | `document` / `structure` / `runtime` / `implementation`（见上方四类互补规则）；旧条目缺失按 unknown 解释 |
| `source_type` | enum | 是 | 见上方强度分级 |
| `source_ref` | string | 是 | 文件路径 + 章节 + 页码，或 URL（人类可读定位）|
| `source_version` | string \| null | 否 | 来源版本标识（安装包版本 / 手册版本 / demo 环境版本）；缺失 = unknown，禁止猜测回填 |
| `source_sha256` | string \| null | 否 | 原件 SHA-256（安装包归档 / 原始文档）；缺失 = 待核实，禁止伪造 |
| `artifact_locator` | object \| string \| null | 否 | 原件锚点（机器可校验的结构化定位），见下方「artifact_locator 锚点规范」；与 `source_ref` 必须指向同一原件，`source_ref` 保留人类可读定位 |
| `verification_status` | enum | 否 | `unverified` / `static-only` / `runtime-observed` / `snapshot-observed` / `cross-checked`（见下方规则）；缺省按 unverified 解释 |
| `usage_scope` | string | 否 | 缺省 = `internal-product-research`；本条证据对蓝联侧的使用限制（与 `applies_to` 的竞品侧适用范围正交），见「治理交接」的导出纪律 |
| `limitations` | string \| null | 否 | 本条证据的局限说明（版本限定 / 角色限定 / 配置限定 / 未复现 / 反编译失败原因等）|
| `screenshot` | string \| null | 否 | 相对 `imgs/` 路径，已脱敏 |
| `url` | string \| null | 否 | demo-runtime 时必填，完整 URL |
| `probed_at` | string \| null | 否 | ISO 8601 时间戳，demo-runtime 时必填（= 上下文字段 captured_at 的证据侧表达）|
| `account_role` | string \| null | 否 | demo-runtime 时必填，如"管理员"/"普通商户"|
| `permission_scope` | string \| null | 否 | demo 账号可见权限范围（如"管理员/全菜单"）；缺失按 unknown 解释，不得泛化到其他角色（状态 `runtime-scope-unknown`）|
| `source_date` | string \| null | 否 | 资料日期（YYYY-MM 或 YYYY），手册版本日期 |
| `confidence` | enum | 是 | `high` / `medium` / `low`（按决策树判定）|
| `notes` | string | 否 | 自由备注（脱敏后的观察）|

### artifact_locator 锚点规范

原件锚点按来源载体取以下结构（示例值）：

| 来源 | 锚点结构 | 示例 |
|---|---|---|
| SQL / DDL | 归档相对路径 + 表名/约束名/语句位置 | `incoming/competitor-hd/packages/hd-mall-3.2.zip → sql/init.sql#T_CONTRACT(T_CONTRACT_PK)` |
| 前端 | 归档路径 + 包内路径 + 路由/符号 | `packages/web-dist.zip → static/js/app.9f2c.js#route:/contract/new` |
| 代码 | 归档哈希 + 内部类/方法/描述符 | `sha256:<pkg-hash> → com.hd.contract.ContractServiceImpl#approve(Long)`；**反编译行号仅作投影辅助标注，不作定位权威** |
| demo | URL + 观察时间 + 角色 + 场景 + 脱敏快照哈希 | `url + probed_at + account_role + scenario + screenshot_sha256` |
| 运行时快照 | 快照包路径 + page-id + 产物哈希 + 批次 manifest | `raw/.../runtime-snapshots/<batch>/pages/<page-id>/ → manifest.json#pages[<page-id>].artifacts[].sha256`（`source_version`=demo 环境版本、`source_sha256`=产物哈希或缺失待核实、`limitations`=版本/角色/场景限定；见 `runtime-snapshot-protocol.md`）|

### 五个维度字段：语义分离，不得互相替代

| 字段 | 回答的问题 | 取值 / 表达 |
|---|---|---|
| provenance_class（谱系角色）| 这条记录是原始来源关联，还是派生转换记录？ | 由 lineage（`derived_from`）表达：空 = 原始观察，非空 = 派生记录。**不新增同义字段**，谱系规则见「来源谱系」 |
| `evidence_kind` | 观察来自哪一类来源？ | document / structure / runtime / implementation / unknown（旧条目）|
| `verification_status` | 对该主张做过何种**验证动作**？ | unverified / static-only / runtime-observed / cross-checked |
| `evidence_state` | 主张处于何种观察/推断状态？ | observed / inferred / not_found / not_scanned / inaccessible / conflicting |
| `implementation_status` | 目标能力的实现状态判定？ | existing / partial / missing / explicitly-not-do / unknown（capability 级，见 capability-schema.md）|

### verification_status 规则

描述**具体验证动作**的状态，不用一个含糊的 `verified` 同时代替哈希校验和业务验证：

| 取值 | 含义 |
|---|---|
| `unverified` | 未做过任何已登记的验证动作 |
| `static-only` | 仅经静态核对（结构 / 代码 / 文档层面比对）|
| `runtime-observed` | 在授权 demo 中实际观察过（记录 URL / 时间 / 角色 / 场景）|
| `snapshot-observed` | 仅基于离线运行时快照证据包（manifest + page-id + 哈希，见 `runtime-snapshot-protocol.md`）；只证明采集时刻的行为 |
| `cross-checked` | 静态与运行时（或多种已确认独立的手段）交叉核对且结论一致 |

- **不得把 verification_status 自动映射为 `evidence_state=observed`**：验证动作是过程维度，evidence_state 是主张状态维度，各自独立记录。
- 升级为 `cross-checked` 须按「证据状态继承与升级」的 upgrade 行逐项留痕；demo 观察窗口不足时只保全只读观察，**不得提前标 cross-checked**。
- **snapshot-observed 不得自动升级**为 `runtime-observed` / `cross-checked`：离线快照不等于当前 runtime re-verified；陈述"当前行为"须重新登录核实并以新 `probed_at` 登记，升级按 upgrade 行留痕。
- 旧条目缺该字段按 `unverified` 解释——仅表示"未登记验证动作"，不改变既有 evidence_state / confidence，不要求回填。

### 向后兼容（旧台账条目）

新字段全部为可选增量；旧条目缺失时按以下语义解释，**不批量回填、不猜版本、不伪造哈希、不静默升级**：

| 缺失字段 | 解释 |
|---|---|
| evidence_kind | unknown（不推断具体类别）|
| source_version | 适用范围未知（沿用既有 source_date/version 行）|
| source_sha256 | 来源身份待核实 |
| artifact_locator | 用既有 source_ref / screenshot / url / probed_at 组合定位 |
| verification_status | unverified（未登记验证动作）|
| usage_scope | internal-product-research（默认值语义）|
| limitations | 未登记（不代表无限制）|
| workspace/target/competitor 上下文字段 | 按 unknown 解释（目标产品未知 = 无目标产品模式；不猜公司、不把竞品公司当产品、不批量回填）|
| permission_scope | unknown（不得泛化到其他角色）|

人工复核确认后可**单条**补写并在 notes 留痕（"补写于 YYYY-MM-DD，依据：…"）；禁止批量脚本回填。

## claim_type 三类标记

每条 evidence 必须标 `claim_type`：

| 标记 | 含义 | 要求 |
|---|---|---|
| `证据` | 来自资料或运行时的事实 | 必须有具体 source_ref |
| `判断` | 基于证据的推理 | 必须列出依据的 evidence_id |
| `假设` | 未证实的假设 | 必须说明如何验证 |

## 来源谱系

Evidence 对象在既有字段之外支持三个**可选** lineage 字段（`derived_from` / `independence` / `applies_to`）。三个字段均为可选增量：旧条目缺失这些字段时按 `independence=unknown` 解释，不破坏既有条目，也不要求回填。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `derived_from` | string[] | 否 | 本条目依据/派生自哪些证据（evidence_id 列表）；空/缺省 = 直接观察 |
| `independence` | enum | 否 | `independent` / `same-chain` / `unknown`；**缺省 = unknown（fail closed）**；`independent` 必须正向确认（确系不同原件）才可填，不得默认 |
| `applies_to` | string | 否 | 适用范围限定（产品/版本/客户/环境），如「客户蓝图：仅 X 项目」|

### 同源去重（来源链折叠）

- **来源链判定**：沿 `derived_from` 传递闭包折叠到根。同一原件派生的以下产物归入**同一来源链**：原文、转换 Markdown、OCR/图片投影、能力模型条目、分析摘要、PRD 交接、汇总 brief——互证计数只计一次。
- **折叠只影响计数语义**：各条目保留各自 `evidence_id` 与原始锚点，不静默删除。
- 下列派生产物**不得**反向作为原始主张的独立证据：转换文本、OCR 结果、统一能力模型、evidence index、S1 能力清单、S1 对比矩阵、产品改进建议、PRD、实施交接包、汇总 brief。
- **正例**：同一 PPT 主张同时出现在转换文本、能力模型条目、分析结果与交接包 → 折叠为同一来源链，互证计数仍只计一个原始来源。

### independence=unknown 三不等规则

`unknown` ≠ 独立（不得参与互证升级）、≠ 同链重复（不得据此合并或丢弃条目）、≠ verified/false（不得改变证据状态）。两条证据描述同一能力但独立性无法判定时：不得因并存提升 confidence、不得按重复丢弃、保持待核实语义。

## 来源类型认识论上限

每种来源类型只能证明其认识论边界内的结论，不得自动越界：

| 来源类型 | 只能证明 | 不得自动证明 |
|---|---|---|
| 操作手册 | 文档记载了该操作/功能 | 已部署/普遍交付 |
| Demo 运行时 | 被观察环境（URL/账号角色/探测时间/版本/配置/场景）中的行为 | 生产部署/所有客户/其他版本 |
| 数据字典/SQL/表结构 | 数据结构存在、实现线索 | 完整业务流程或业务能力 |
| 安装包结构（package-static）| **该版本包内**存在该结构（表/路由/配置/部署文件）| 已部署、已启用、完整业务功能可用 |
| 代码/反编译投影（code-analysis）| **该版本代码中**存在该实现（类/方法/分支）| 当前环境实际执行该分支、已授权、已启用、运行成功 |
| 第三方依赖 | 依赖/组件存在 | 竞品自研能力或产品规模（必须先区分第三方依赖、运维组件与业务代码）|
| 方案 PPT/厂商宣称 | 方案提出/厂商声称 | 标准产品已交付 |
| 客户蓝图/实施方案/验收交付材料 | 该客户项目中已设计/已交付 | 标准产品能力（不自动泛化）|

可执行正反例：

- **WHEN** 某能力仅有方案 PPT 主张 → **THEN** 只保持「方案提出/厂商声称」语义与弱证据置信上限，不得仅凭 PPT 变成已交付能力
- **WHEN** 某能力仅有操作手册记载 → **THEN** 结论停留在「文档记载」层级，不得自动变成普遍交付
- **WHEN** 某能力仅来自 demo 运行时观察 → **THEN** 结论限定被观察环境（URL/账号角色/探测时间/版本/配置/场景），不得泛化到生产部署、所有客户或其他版本
- **WHEN** 仅有数据字典/SQL 表结构线索（仅见表结构）→ **THEN** 只形成 structure 层观察主张（"该版本存在表 X"），结论限定数据结构层面，不得自动等于完整业务功能可用
- **WHEN** 仅观察到包内静态路由/菜单代码（未启用路由）→ **THEN** 只宣称"该版本包内包含该路由的代码"，不得宣称功能已授权、已启用或可用
- **WHEN** 安装包版本与 demo 环境版本未确认一致 → **THEN** 两条来源分别记录各自的 source_version 与 applies_to，结论不跨版本拼接成同一部署状态，也不互证升级 confidence
- **WHEN** 同一安装包中的 DDL、路由与代码都指向同一能力 → **THEN** 可以互补引用，但互证计数只计一条来源链（原件 = 该安装包），不因载体/文件/evidence_kind 不同计为独立证据
- **WHEN** 反编译失败、代码混淆或工具不可用 → **THEN** 标 `not_scanned` 或 `inaccessible` + limitations 注明原因，不得判功能缺失（not_found / implementation_status=missing）
- **WHEN** 按文件数量评估竞品产品规模 → **THEN** 必须先剥离第三方依赖与运维组件，只统计已区分的业务代码；禁止按 JS/JAR 文件总数推断产品规模
- **WHEN** 同一 PPT 的转换文本、能力模型条目与交接包都出现同一主张 → **THEN** 三者只能算一条来源链，互证计数仍只计一个原始来源
- **WHEN** 厂商材料截图中可见调试工具痕迹（如 vConsole 调试按钮）→ **THEN** 该屏判定为演示环境/原型证据，支持「方案宣称≠生产交付」的上限判断（2026-10-31 海鼎移动方案 PPT 多屏实证）

## 缺失字段失败关闭（fail-closed）

Evidence 条目缺失溯源字段时严格按此映射处理，不得静默补齐：

| 缺失项 | 处理 |
|---|---|
| source_sha256 | 来源身份待核实 |
| slide/page 锚点 | 页面定位待核实 |
| artifact_locator | 用既有定位字段组合定位；定位能力下降需在 limitations 注明 |
| evidence_id | 不作为完整可追溯证据消费 |
| evidence_state | 不得推断为 verified |
| evidence_kind | 不推断类别，按 unknown 解释 |
| verification_status | 不推断已验证，按 unverified 解释 |
| source_type | 按弱解释（取最低证明力解释）|
| source_date/version | 适用范围未知 |
| lineage/independence | 不得重复计证（independence 按 unknown）|
| target scope | 不得泛化到标准产品 |

- `unknown` ≠ false ≠ missing ≠ verified ≠ not applicable——五者语义互不替代，不得混用。
- 处理动作 = `claim_type=假设` + `confidence` 降 `low`（导出共享契约时映射为 schema 合法值 `unassessed`）+ 强制进 pending-items（行类型 `missing-provenance`）。
- **禁止**静默补齐；**禁止**自动生成完整 ID 或用当前日期填 `source_date`。

## 证据状态继承与升级

- **只降不升**：文档转换、OCR、摘要、能力合并、能力矩阵生成、PRD 交接、归档或重新表述等下游产物，其证据状态只能**保持或降级**原值，不得自动升级；升级必须有明确新增证据。
- **升级条件**：新增证据 `independence=independent` 且支持同一主张，且 `applies_to`/产品/客户/版本/时间/验证范围与目标结论匹配。
- **升级留痕**（pending-items `upgrade` 行）：新增 evidence_id、升级前状态、升级后状态、升级理由、新增证据证明了什么、产品/客户/版本/时间、实际验证范围、**仍未证明的范围**、受影响的原 evidence_id。
- **范围不匹配 → 不升级**：记录不匹配原因，待人工裁决。
- **单链不判演进**：判定「版本演进/术语变更」前必须先对照文档链当前版本——仅凭单链（单一时期 demo 或单一客户旧版实拍）判演进不可靠，客户环境用词会被误判为产品演进（2026-10-31 实证：demo「已结束」vs 东苑 2021「已结案」，经手册核对纠正为客户端用词差异，非产品演进轴）。两链不一致时优先登记术语别名/冲突；演进判定需文档链版本序列或第三链佐证。

## 治理交接：导出为共享 source-reference

跨 skill 交接（PRD / ontology 工作流）挂接共享契约 `/opt/code/skill/skills/business/product-prd-generator/references/product-governance/`（owner 为 product-prd-generator；本 skill 只消费不修改，字段与枚举以共享 schema 为准，此处不重复定义），包括 `source-reference.schema.json` 与 `ontology-change-set.schema.json`。导出映射：

| 台账字段 | 共享 source-reference 字段 | 说明 |
|---|---|---|
| `evidence_id` | `evidence_id` | 原值透传；台账仍是唯一权威记录 |
| `capability_id` | `capability_id` | 原值透传 |
| `source_ref` | `source_ref` | 公司根（`$COMPANY_BASE` ∥ `$LANLNK_BASE`）相对路径；外部 URL 与代码仓引用保持原样 |
| `source_sha256` | `content_sha256` | 原值透传（语义合适的既有字段）|
| `source_version` | `revision` | 原值透传（语义合适的既有字段）|
| `artifact_locator` | `location` | 取主定位表达（或序列化摘要）；语义合适的既有字段 |
| `probed_at`（缺失时用 `source_date`） | `observed_at` | 运行时探测时间优先 |
| `confidence` | `confidence` | 按台账原值 |

**新字段不写入共享对象**：共享 schema 是 `additionalProperties:false` 的只消费接口，禁止把 `evidence_kind` / `verification_status` / `usage_scope` / `limitations` 等新字段塞进共享 source-reference 对象；台账保留完整元数据，共享侧只做链接与回链（`evidence_id`）。

### usage_scope / limitations 的导出纪律

共享 source-reference schema 没有语义合适的既有字段承载使用限制。导出时：

1. 台账保留完整元数据（usage_scope / limitations 不删改）；
2. 导出包必须附**伴随说明**（handoff 伴随文档），逐条列出受限条目的 `evidence_id` 及其 `usage_scope` / `limitations`；
3. 接收方流程无法保留该使用限制时（如目标产物将脱离 internal-product-research 范围），**停止该项导出并在 pending-items 说明原因**——不得让 usage_scope / limitations 在导出过程中静默丢失。

`source_ref` 路径规范：materials/raw 内证据写公司根相对路径（如 `materials/13-competitors/qimao/05-实施与服务/合同模块操作手册.pdf`），demo-runtime 另填 `url`。不得改写为其他产品或其他公司的权威路径，也不得把未核实的绝对路径伪装成相对路径。

**决策不是证据（来源边界）**：

- `claim_type=证据` 导出为 `observed` 的竞品观察；`claim_type=判断` 导出为 `inferred`，且必须能回溯到依据的 `evidence_id`
- OPC/产品 owner 的 roadmap、优先级或 ontology 方向决策，在共享契约里是独立的 `product_decision`（decision 对象按共享 schema），由决策 owner 单独记录。这类决策不进本台账，也不抬高任何竞品观察的 `confidence`
- 只有单独记录的 owner decision 能批准路线图或 ontology 方向；本台账的【判断】条目最多作为决策的 supporting source
- 竞品观察可以支撑共享 `ontology-change-set` 的 `draft` 提案，但永不自动写入 canonical ontology，也不强制任何 PRD feature

## 禁止行为

- 禁止无 source_ref 的 evidence
- 禁止把 sales-material 当 `证据` 类（必须降级为 `判断` 或 `假设`）
- 禁止把 proposal PPT 的功能列表等同于实际能力（proposal 只能作弱证据）
- 禁止把"demo 账号看不到"等同于"竞品没有"——必须标 `claim_type=假设` + `notes="可能权限不足"`
- 禁止把 evidence_kind / verification_status 当作 confidence 或 evidence_state 的自动升降依据
- 禁止把不同文件、不同 source_type、不同 evidence_kind 自动当独立来源（独立性须正向确认；同包多载体默认同链）
- 禁止把静态路由/菜单代码当功能全集，把代码分支当实际运行
- 禁止 source_date 不明时填当前日期（必须留空或填资料标注的版本日期）
- 禁止猜测或伪造 source_version / source_sha256（缺失即待核实语义）
- 禁止截图未脱敏就进 evidence
- 禁止凭据、许可证密钥、序列号、数据库连接串、API token、个人数据进入 materials、台账 notes 或任何日志（见「脱敏规则」与 safety-and-ethics.md）

## 脱敏规则

截图写入 `imgs/` 前必须脱敏：

| 敏感类型 | 处理方式 |
|---|---|
| 客户/商户真实名称 | 替换为 `客户A` / `商户B` |
| 手机号 | 打码为 `138****1234` |
| 身份证号 | 打码为 `4401**********1234` |
| 金额 | 保留数量级，替换为 `X 万` |
| 邮箱 | 打码为 `z***@example.com` |
| 地址 | 保留城市，具体地址打码 |
| 许可证密钥/序列号 | 完全移除，不进任何层（incoming 记录来源与哈希即可）|
| 数据库连接串 | 主机/账号/密码打码，只保留类型（如 `jdbc:mysql://***`）|
| 包内个人数据（配置中的姓名/手机号）| 打码或移除；取证记录只保留字段名与类型 |

**脱敏后必须在 evidence.notes 标注**："截图已脱敏：客户名/手机号/金额"。

## 待确认项规则

`review/pending-items.md` 必须记录以下情况：

| 类型 | 触发 | 处理 |
|---|---|---|
| 术语未映射 | standard_term=null | 列出 original_term + 候选映射，待用户确认 |
| demo 权限不足 | accessible=false 的页面/模块 | 列出模块名 + requires_role，标注"该模块能力未探测"|
| 手册版本过旧 | source_date >2 年前 | 列出文件 + 日期，建议补充新版 |
| 资料类型单一 | 只有 sales-material 或只有 proposal | 标注置信度上限，建议补充 manual |
| 能力冲突 | manual 与 runtime 描述不一致 | 列出冲突点，标注"可能是版本差异"，置信度降级 |
| 蓝联现状无法判断 | status_vs_lanlnk=unknown | 列出 capability + 原因（功能清单未覆盖/语义不清）|
| `missing-provenance` | 缺 SHA/锚点/evidence_id/状态/来源类型/版本/独立性 | 列出缺失字段与待核实影响，禁补齐 |
| `upgrade` | 有新增独立证据拟升级状态/置信度 | 按「证据状态继承与升级」的留痕字段逐项记录 |
| `not-analyzable` | 反编译失败/代码混淆/工具不可用 | 列出目标模块、工具与失败原因；标 `not_scanned`/`inaccessible` + limitations，不得判功能缺失 |
| `version-mismatch` | 安装包版本与 demo/手册版本未确认一致 | 分别记录各自 source_version/applies_to，禁止互证升级或跨版本拼接结论 |
| `runtime-scope-unknown` | demo 账号角色/权限范围未知（account_role 或 permission_scope = unknown） | 结论限定为"被观察环境"，不得泛化到其他角色；补采后在 notes 留痕 |
| `entity-conflict` | 同名竞品公司/产品疑似但未确认同一实体 | 不自动合并；列出两侧证据与差异点，待人工裁决 |
| `same-source-chain` | 同一来源链的派生产物被当作多份独立证据 | 按来源链折叠计数只计一次（见「来源谱系」），保留各条目不删除 |
| `term-context-conflict` | 同名术语在不同产品语境语义不同（跨目标产品复用 standard_term） | 不自动证明语义相同；映射存疑进 pending，按目标产品 ontology 分别归一 |
| `target-context-missing` | 目标公司/产品缺失或无法解析 | 走无目标产品模式：不输出 existing/partial/missing、不归一 standard_term |
| `competitor-context-missing` | 缺竞品公司或竞品产品 | 字段保持 unknown；公司级线索单列，不出具体产品能力结论 |
| `baseline-unavailable` | 目标产品功能清单/基线缺失 | 只输出能力清单，不做现状映射；不回退其他产品基线 |
| `snapshot-issue` | 运行时快照失败模式（动态内容未保存/资源缺失/截图与 HTML 不同状态/脱敏失败/版本角色未知/快照过期 `snapshot-stale`/快照与 demo 当前行为冲突 `runtime-conflict`） | 按 `runtime-snapshot-protocol.md`「失败模式与处理」逐项标状态与处理；snapshot-observed 不自动升级 |
| `conflict-eula` | EULA/保密/客户合同使用限制与拟执行操作冲突 | 单列记录冲突条款与拟执行动作，按 safety-and-ethics.md 冲突流程处理，不自动执行 |
| `export-blocked` | 导出目标无法保留 usage_scope/limitations | 停止该项导出，记录原因与受影响 evidence_id |

## 复核建议

`evidence-ledger.md`（人类可读版）按 capability 分组列出全部证据，便于：

- 用户抽查关键能力的证据链
- product-prd-generator 复用改进建议时追溯依据
- strategy-brief-generator 引用竞品能力时核对置信度
