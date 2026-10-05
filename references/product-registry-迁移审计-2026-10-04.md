# product-registry.yaml 迁移审计（2026-10-04，O3 / Batch 2）

> **依据**：owner decision O3 / Batch 2（`references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`，
> approved 2026-10-04，audit-only）。
>
> **审计对象**：`skills/business/product-prd-generator/references/product-registry.yaml`
> （155 行，8 产品条目）。方案 B（O1）批准后不建公共 adapter capability registry，
> 本表保留为 product-prd-generator **迁移期兼容元数据**。
>
> **本报告取代** `references/product-context-消费方审计-2026-10.md` §5 中
> 「后续迁移项：建立 per-consumer adapter_capabilities …… 未落地前不得复制第二套
> 注册表」的表述——Batch 1 六个 capability 文件已于 2026-10-04 落地（D-O1/D-O2）。
> 该报告其余内容仍为有效快照。
>
> **快照日期**：2026-10-04。行号为当日工作树状态（部分文件存在其他会话未提交修改）。

## 0. 审计方法与 registry 职责基线

```bash
cd /opt/code/skill
rg -ln "product-registry" shared skills references AGENTS.md
rg -n "product-registry" /opt/code/docs/lanlnk/30-products   # 跨仓引用（只读）
```

registry 当前承担**四重职责**（设计包 `references/adapter-capability-decision-2026-10.md` §4）：

| # | 职责 | 迁移状态判定 |
|---|---|---|
| 1 | prd-gen adapter 元数据（adapter_status / product_class / ontology_profile） | **已有替代权威源**（capability 文件，Batch 1）；registry 值冻结为兼容快照（§3） |
| 2 | 路径登记（docs_root / code_root / ontology / prd_root / term_aliases） | 已迁移 resolver-first；registry 为同步镜像（头部规则 6 双源同步税仍在，§4-B4） |
| 3 | 历史 decision 记录（头部规则 7/8/9） | 只读历史，无 drift 风险，不需迁移 |
| 4 | check_docs_consistency Check 4 对账面（30-products 目录 ↔ registry 条目） | 在用（程序化消费方，§1-A4）；替代方案需 owner 批准（§4-B2） |

## 1. 消费方清单

### A. 程序化读取方（读取 registry 文件内容）

| # | 位置 | 读取方式 | 消费字段 |
|---|---|---|---|
| A1 | `skills/business/product-prd-generator/tests/test_product_governance_contracts.py:109-141` | `yaml.safe_load`（`test_product_registry_contains_seven_software_products_and_lnkwebsite_prd_only`） | products 键集（7 软件 + lnkwebsite）、product_class、ontology_profile、ontology（lnkwebsite null）、product_status（lnkchatbi）、adapter_status（lnkwebsite=unsupported :130、lnkchatbi=partial :140） |
| A2 | `skills/business/product-prd-generator/tests/test_product_semantic_contracts.py:49-77` | `yaml.safe_load`（`test_product_registry_covers_registered_products`） | products 键集（7 产品覆盖）、code_root 值 + `Path.is_dir()` 存在性、docs_root 存在性、无 legacy_* 字段 |
| A3 | `skills/business/product-prd-generator/tests/test_product_authority_fixtures.py:151-166` | `yaml.safe_load`（`test_fixture_profiles_match_registry_and_business_tool_split`） | product_class、ontology_profile（fixture 镜像与 registry 一致性；business/tool 二分） |
| A4 | `references/scripts/check_docs_consistency.sh:218-226`（Check 4） | `grep -qE "^  ${pid}:"` | products 键集（30-products/<pid> 目录注册对账，缺条目 → WARN） |
| A5 | `skills/business/product-prd-generator/tests/test_paths.py:210` | 断言报错文案 | 仅断言 `_paths` 未注册产品报错信息包含 "product-registry.yaml" 字样（注册引导文案，非数据消费） |

**生产代码零读取**：`product_prd_generator/_paths.py` 不加载 registry（全部 5 处命中为
docstring / 注释 / 报错引导文案 ：40,:44,:159,:319,:397,:407）。运行时产品路径解析
唯一权威源 = `_paths.resolve_product_paths()`（resolver-first，经
`shared.product_context`，与前一阶段审计 §2 结论一致）。

### B. 文档 / prose 引用（skill 仓）

| # | 位置 | 引用性质 |
|---|---|---|
| B1 | `skills/business/product-prd-generator/SKILL.md:36`（参考文件表入口）、`:54`（已注册产品清单叙述） | 使用指引（本轮未触碰：存在其他会话未提交修改） |
| B2 | `references/product-semantic-baseline.md:43,64,73,78` | adapter_status 枚举与语义契约（本轮已补迁移期注记，见 §5） |
| B3 | `references/product-semantic-baseline.schema.json:7,20` | schema required + adapter_status enum（`implemented/partial/unsupported/onboarding`，**不可表达 blocked / not-applicable**，见 §3） |
| B4 | `references/product-governance/README.md:39` | product_status vs adapter_status 语义区分（本轮已补迁移期注记，见 §5） |
| B5 | `skills/business/pricing-generator/SKILL.md:85` | adapter_status 免责声明（同时指 resolver 字段与 registry 字段；本轮未触碰：其他会话未提交修改；Batch 3 文档级迁移候选） |
| B6 | `skills/business/competitor-product-analyzer/SKILL.md:25` | registry 定位为「迁移期 adapter 元数据」（语义已正确；本轮未触碰：其他会话未提交修改） |
| B7 | `shared/product_context/README.md:38` | 「resolver 不读取 product-registry.yaml」边界声明 |
| B8 | skill 仓 `AGENTS.md:221` | Check 4 对账机制说明 |
| B9 | `skills/business/product-prd-generator/references/adapter-capabilities.yaml` | evidence 溯源引用 registry 条目（8 处）；schema 校验测试 `shared/product_context/tests/test_adapter_capabilities_schema.py:65,346` 已界定「引用 ≠ 依赖」 |
| B10 | 治理文档族：`references/adapter-capability-decision-2026-10.md`（设计包 §4）、`references/adapter-capability-owner-recommendation-2026-10.md`、`references/adapter-capability-owner-decision-2026-10-04.md`、`references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`、`references/product-context-消费方审计-2026-10.md` §5 | 决策 / 审计记录（记录性引用，非调用方） |

### C. 跨仓引用（docs 仓，只读，本轮零改动）

| # | 位置 | 引用性质 |
|---|---|---|
| C1 | `30-products/external-owner-decisions-2026-10-02.md:5` | 回填通道描述：`product-registry-feedback.yaml`（docs）→ `product-registry.yaml` + `_paths.py`（skill） |
| C2 | `30-products/lnkcre/reconciliation/domain-architecture-migration-2026-09-26.md:33` | 历史注记（ontology_note 过时性说明，只读历史） |
| C3 | `out/prd/lnkchat/output/**`（source-references.json 等 5 处） | 生成区历史 run 快照（gitignored，下次运行自动刷新，不构成消费方） |
| — | **区分**：`30-products/lnkchat/ontology/README.md:12`、`30-products/lnkcrm/ontology/releases/SEM-CRM-OPS-001.yaml:19` 引用的是 docs 侧 `product-registry-feedback.yaml`（回填反馈文件），**不是**本表消费方 |

## 2. 字段清单、替代来源与迁移状态

替代来源 = 方案 B 定型后的 go-forward 权威源（registry 冻结为兼容快照后的正确读取位置）。

| 字段 | 出现范围 | 语义 | 替代来源（go-forward） | 迁移状态 |
|---|---|---|---|---|
| `display_name` / `kind` / `product_class` / `product_status` / `aliases` | 全部/部分 | 产品身份与分类 | **company.yaml products（唯一产品台账）**，经 `shared.product_context` resolver | ✅ 权威源已在位（8 产品全登记）；registry 为兼容镜像；A1/A3 测试仍读镜像值 |
| `docs_root` / `code_root` / `ontology` / `ontology_extra` / `prd_root` / `term_aliases` | 全部 | 三层路径事实 | company.yaml layers + `30-products/<产品>/` 治理 README → resolver；代码侧 `_paths.resolve_product_paths()`（resolver-first，未配置/null 一律显式报错） | ✅ resolver-first 已落地（前阶段审计 §2）；registry 按头部规则 6 与 `_paths` 保持同步（**双源同步税仍在** → §4-B4） |
| `feature_baseline` | lnkcre | 功能基线路径 | `30-products/lnkcre/prd/baseline/feature-baseline.yaml`（canonical）；pricing-generator 已 resolver-first 推导（`_mi_feature_baseline_paths()`） | ✅ canonical 在位；registry 为单产品登记 |
| `competitor_evidence_root` | lnkcre | 竞品证据根 | `30-products/lnkcre/evidence/competitors`（competitor-product-analyzer 按 skill 契约引用） | ✅ 同上 |
| `ontology_profile` | 7 软件产品 | prd-gen 处理 profile（business/tool ontology 入口选择） | `product-semantic-baseline.md` §3 契约 + 测试断言（A1/A3） | 🟡 在用；profile 语义归 prd-gen 契约，产品分类归 company.yaml——删除前需将 A1/A3 断言改指 baseline 契约或 company.yaml |
| `model_kind_hint` | 部分 | legacy 内部提示 | 无（头部规则 4 / baseline §3 已声明非入口概念） | 🟡 legacy，仅注释性提示，无运行时消费 |
| `adapter_status` | 全部 8 | 本 skill（及历史叙述上的「未来显式登记消费方」）adapter 支持度 | **`references/adapter-capabilities.yaml`**（本 skill 私有声明，Batch 1，2026-10-04 落地；全 skill 侧见六份 `skills/business/<skill>/references/adapter-capabilities.yaml`） | ✅ **已替代**：capability 文件为唯一权威源；registry 值冻结为兼容快照，**不再在本表变更状态**；A1 测试 2 处断言仍读旧值（→ §4-B1） |
| `history_note` / `ontology_note` / 各 `*_note` / 头部规则 7/8/9 | 部分 | 描述性注记 + 历史 decision 记录 | `30-products/<产品>/` 各 README（canonical 指针）+ 本表头部（只读历史） | ✅ 只读历史，无 drift 风险（职责 3） |

## 3. adapter_status 对齐矩阵（registry 冻结快照 vs capability 权威源）

registry 枚举（`product-semantic-baseline.schema.json:20`）：
`implemented | partial | unsupported | onboarding` —— **不可表达 `blocked` / `not-applicable`**。
capability schema（O2，schema_version 1）六态：`implemented | partial | onboarding |
unsupported | not-applicable | blocked`。**差异以 capability 文件为准。**

| product | registry（冻结快照） | capability 文件（权威） | 差异说明 |
|---|---|---|---|
| lnkcre | implemented | implemented | 一致 |
| lnkcrm | onboarding | onboarding | 一致 |
| lnkchat | partial | partial | 一致 |
| lnkchatbi | partial | partial | 一致 |
| lnkreport | partial | partial | 一致 |
| lnkvision | unsupported | unsupported | 一致（capability notes：升 partial 属 skill 自治，不依赖 owner 决策） |
| lnkgateway | unsupported | **blocked** | registry 枚举不可表达 blocked（ontology+prd unresolved，O11 pending 阻塞）→ 以 capability 文件为准 |
| lnkwebsite | unsupported | **not-applicable** | ★ O2 改判（2026-09-27 owner prd-only 裁定：无 PRD 生成场景，软件产品契约之外）；registry 枚举不可表达 → 以 capability 文件为准 |

**判读规则**：迁移期内任何消费方需要 adapter 支持度，一律读
`skills/business/<skill>/references/adapter-capabilities.yaml`；
registry `adapter_status` 仅作历史兼容快照（其 lnkgateway / lnkwebsite 两格与权威源
存在已登记的枚举性差异，非漂移）。

## 4. 删除阻塞项（deletion blockers）

**删除 registry = 独立 owner 批准动作（本轮明确不做）。** 以下为删除前必须逐项解除的
阻塞清单（解除动作本身亦需批准）：

| # | 阻塞项 | 类型 | 解除条件 |
|---|---|---|---|
| B1 | 三组回归测试直接读取 registry（§1-A1/A2/A3：governance / semantic / authority fixtures；含 adapter_status 2 处断言、code_root/docs_root 存在性断言、product_class/ontology_profile 镜像断言）——**已解除（2026-10-04，见下方注记）** | 程序化 | 断言迁移改指 company.yaml / resolver 输出 / capability 文件 / baseline 契约，并重写测试 |
| B2 | `check_docs_consistency.sh` Check 4 以 registry 为对账面（30-products 目录 ↔ 条目，防 ontology 静默回落商管，lnkcrm 实证）——**已解除（2026-10-04，见下方注记）** | 程序化 | 对账源改为 company.yaml products（或 resolver 产品清单），保持 WARN 语义 |
| B3 | 新产品注册流程（头部规则 1「新产品加入 = 补一条 entry」）与 `_paths.py` 未注册报错引导（:397/:407 引导注册 + A5 文案断言）以 registry 为注册入口——**已解除（2026-10-04，见下方注记）** | 流程 | owner 定义替代登记流程（如 company.yaml onboarding 契约）并同步改错误引导与断言 |
| B4 | 头部规则 6 双源同步契约（registry ↔ `_paths.resolve_product_paths()`，改一边必须改另一边） | 契约 | 路径解析收敛为单一来源（resolver）后撤销同步义务 |
| B5 | prose / 文档引用（§1-B：prd-gen SKILL.md×2、baseline.md、schema.json、governance README、pricing SKILL.md:85、competitor SKILL.md:25、shared README:38、AGENTS.md Check 4 说明） | 文档 | Batch 3 文档级迁移（其中 3 个 SKILL.md 存在其他会话未提交修改，需各文件会话处理） |
| B6 | capability 文件 evidence 溯源引用 registry 条目（B9，8 处） | 证据链 | 删除时 evidence 改指本审计 + owner decision 文档族（历史证据不要求存活目标，但需可追溯） |
| B7 | docs 侧跨仓引用（§1-C1 回填通道描述、C2 历史注记） | 跨仓 | docs 仓治理线更新回填通道描述（docs 改动，本轮禁改） |

> **B1 状态注记（2026-10-04 状态回写）**：B1 已执行并通过复核。授权来源为用户会话中
> 的明确「执行 B1」指令（**会话授权**）；**独立 owner 签署记录未记录**，不得表述为
> 已完成独立签署。B1 执行记录见
> `references/adapter-capability-owner-decision-b1-execution-2026-10-04.md`。
> 验证结果（引自 B1 执行记录，回写会话未重跑）：三组迁移后回归测试 + O4 门禁测试
> 通过、schema 校验通过、格式检查通过；未提交、未推送。B1 实施后 §1-A1/A2/A3 所列
> 断言已改读 capability 文件 / company.yaml + resolver / baseline 契约（范围对账见
> 执行记录 §4）；本报告 §1/§2 其余行保持 2026-10-04 快照原文，未重写。B2-B7 仍为
> pending / 冻结，各自需独立授权；B1 完成不构成 registry 字段删除批准。本状态回写
> 不改变 registry 数据区、authority 或产品事实。

> **B2 状态注记（2026-10-04 状态回写）**：B2 已执行并通过验证。授权来源为用户会话中
> 的明确「批准执行 B2」指令（**会话授权**）；**独立 owner 签署记录未记录**，不得表述为
> 已完成独立签署（与 B1 同口径）。B2 执行记录见
> `references/adapter-capability-owner-decision-b2-execution-2026-10-04.md`。
> 实施内容：`references/scripts/check_docs_consistency.sh` Check 4 对账面自
> product-registry.yaml 改为 company.yaml products（`products:` list 块内
> `  - id: <pid>` 键；块边界含 `# --- products-end ---` marker，防其他 section
> 同形 list 误判），WARN 语义保持。验证（B2 执行会话实测）：脚本全量运行与迁移前
> 基线一致（FAIL=0 / WARN=0 / PASS=33）、合成未注册目录 WARN 路径触发、正/负向
> pid 探针全部正确（无前缀撞车误判）、product-prd-generator 测试 169 passed /
> 3 skipped、shared/product_context 测试（含 O4 门禁与 capability schema）53 passed。
> B2 完成后 §1-A4 所列程序化消费已迁移；本报告 §1/§2 其余行保持 2026-10-04 快照
> 原文，未重写。遗留（B5 范围 prose，B2 有意未触碰，待 Batch 3 处理）：§1-B8
> （AGENTS.md:221 Check 4 机制说明）与本表头部规则 10(c)「Check 4 对账面」表述——
> 两者 B2 后均指向旧对账面。B3-B7 仍为
> pending / 冻结，各自需独立授权；B2 完成不构成 registry 删除或字段删除批准。
> 本状态回写不改变 registry 数据区、authority 或产品事实。

> **B5 状态注记（部分，2026-10-04 状态回写）**：B2 执行记录 §6.1 登记的两处
> Check 4 对账面 prose 已对齐：skill 仓 AGENTS.md:221 的 Check 4 机制说明、
> 本表（product-registry.yaml）头部规则 10(c) 的「Check 4 对账面」表述，均改述为
> 「Check 4 产品目录对账面 = company.yaml products（唯一产品台账）」，本表不再
> 承担该对账职责（保留为迁移期兼容元数据的表述不变，YAML 数据区零改动）。
> 授权来源为用户会话中明确的「批准执行 B5，仅处理 B2 报告中登记的两处 Check 4
> 过时说明」指令（**会话授权**）；**独立 owner 签署记录未记录**，不得表述为
> 已完成独立签署（与 B1/B2 同口径）。执行记录与证据路径见
> `references/adapter-capability-owner-decision-b5-execution-2026-10-04.md`。
> **B5 阻塞项整体仍为 pending**：§4-B5 所列其余 prose 引用（prd-gen SKILL.md×2、
> baseline.md、schema.json、governance README、pricing SKILL.md:85、
> competitor SKILL.md:25、shared README:38）未处理，需各文件会话或后续批次授权；
> 本注记不构成 B5 整体解除。B3/B4/B6/B7 仍为 pending / 冻结，各自需独立授权。
> 路径修正备注：授权提示词曾将 prose 目标 #1 写为 docs 仓 AGENTS.md；工作区实证
> 该文件无 Check 4 对账描述，实际登记位置为 skill 仓 AGENTS.md:221（§1-B8 口径），
> docs 仓因此零改动。本状态回写不改变 registry 数据区、authority 或产品事实。

> **B5-R1 状态注记（部分，2026-10-04 状态回写）**：B5 剩余 prose 经 B5-R1 会话授权
> 处理，结果 **partial / blocked-by-concurrent-change**。已完成 2/7 目标文件（工作区
> 干净、独立应用）：prd-gen `SKILL.md` :36（References 表行：registry→迁移期兼容
> 元数据，路径→resolver，adapter→capability 文件）与 :54（已注册产品台账改指
> company.yaml products 8 产品，registry 降为迁移期兼容元数据 + Check 4 非职责注记）、
> `product-semantic-baseline.schema.json` 顶层 description 追加迁移期注记（冻结词表 +
> capability 权威源 + 审计指针；:7 required / :20 enum 结构化约束按授权禁改未触碰）。
> 5 个目标文件因**其他会话未提交修改**标记 blocked-by-concurrent-change 未处理：
> baseline.md（M；:43 待对齐）、governance README（M；:40 待对齐）、pricing
> SKILL.md（M；:85 待对齐）、competitor SKILL.md（M；:25 语义已正确）、
> shared/product_context/README.md（shared/ 整目录 untracked；:38 语义已正确）。
> 授权来源为用户会话中明确的「批准执行 B5-R1」指令（**会话授权**）；独立 owner 签署
> 未记录，不得表述为已完成独立签署（B1/B2/B5 同口径）。执行记录与逐文件新旧口径见
> `references/adapter-capability-owner-decision-b5-r1-execution-2026-10-04.md`。
> **B5 阻塞项整体仍为 pending**：本注记不构成 B5 整体解除；剩余实质待对齐 3 处
> （baseline.md:43、governance README:40、pricing SKILL.md:85）+ 核对项 2 处
> （competitor:25、shared README:38）。B3/B4/B6/B7 仍为 pending / 冻结，各自需独立
> 授权。本状态回写不改变 registry 数据区、authority 或产品事实。
> **（B5-R5 更正注记：上文及 B5-R1/R2 时代所用「其他会话未提交修改」表述，经 B5-R5
> 重新分类更正为「未确认归属的未提交工作树修改」——git 不能证明修改者身份，且未发现
> 在册并发会话；历史记录保留当时判断，不重写。见下方 B5-R5 状态注记。）**

> **B5-R5 状态注记（B5 整体解除，2026-10-04 状态回写）**：B5-R5 已完成。目标文件
> `skills/business/pricing-generator/SKILL.md` 存在**未提交工作树修改，未确认归属**
> （git diff 实证 18 insertions / 0 deletions，两个 hunk 与 B5-R3/R4 记录一致；git
> 不能证明修改者身份；未发现在册并发 skill 会话）——**B5-R3/R4 的阻塞判定
> 「其他会话修改」就此更正为「未确认归属的工作树修改」，非已证实的其他会话**。本轮
> 仅对 B5 登记的最后一处 adapter_status prose（:85 目标句 2 行）做最小替换（对齐后
> 6 行：capability 文件为 pricing skill adapter 支持度权威源；registry adapter_status
> 为迁移期冻结兼容元数据、不再是在用权威源；capability 状态不得覆盖 product
> authority、产品台账以 company.yaml products 为准；registry 保留、删除需独立 owner
> 批准），其余既有 diff（frontmatter 2 行 + resolver 节 14 行）未改动。验证（B5-R5
> 会话实测）：check_docs_consistency.sh FAIL=0 / WARN=0 / PASS=33（exit 0）、
> pricing-generator pytest 6 passed、git diff --check 通过。至此 **B5 全部目标已完成
> 或 verified-no-change**：B5 两处 Check 4 prose（AGENTS.md:221 + registry 头部规则
> 10(c)）、B5-R1（prd-gen SKILL.md×2 + schema.json；competitor:25 / shared
> README:38 verified-no-change）、B5-R2（baseline.md + governance README）、
> B5-R5（pricing SKILL.md）——**B5 整体解除**。授权来源为用户会话中明确的「批准执行
> B5-R5」指令（**会话授权**）；**独立 owner 签署记录未记录**，不得表述为已完成独立
> 签署（B1/B2/B5/B5-R1—R4 同口径）。执行记录见
> `references/adapter-capability-owner-decision-b5-r5-execution-2026-10-04.md`。
> **product-registry.yaml 数据区未修改**（保留，删除仍需独立 owner 批准）；
> **B3、B4、B6、B7 仍冻结**（各自需独立授权，B5 解除不构成 registry 删除批准）；
> **O4 实际迁移、O5-O11 仍冻结**。本轮未提交、未推送。

> **B3 状态注记（2026-10-04 状态回写）**：B3 已执行并通过验证。授权来源为本轮用户
> 会话明确的「批准执行 B3」指令及随附 owner 决定（**会话授权**）；**独立 owner 签署
> 记录未记录**，不得表述为已完成独立签署（与 B1/B2/B5 同口径）。owner 决定：产品
> 注册的唯一入口 = docs 仓 onboarding 契约 `bash scripts/onboard.sh product <company>
> <pid> --name "<产品名>"`（写 company.yaml products 台账并创建
> 30-products/<pid>/{prd,ontology} 骨架）；product-registry.yaml 不再作为新产品注册
> 入口（保留为迁移期兼容元数据）；代码侧 canonical 目录名与 pid 不同时仍在
> `_paths._PRODUCT_CANONICAL_DIR` 补映射（代码实现细节，非产品台账来源；先例
> lnkcrm，acbae37）。实施：`_paths.py` `_guard_unregistered_fallback()` 警告/报错
> 引导改指 onboarding 契约、tests/test_paths.py A5 断言改指 onboard.sh product /
> company.yaml 关键词、本表头部规则 1 注释改指 onboarding 契约（**YAML 数据区零
> 改动**，git diff 实证仅头部注释 hunk）。验证（B3 执行会话实测）：test_paths.py
> 58 passed（A5 目标测试通过）、全量 168 passed / 3 skipped / 1 failed——该唯一
> 失败为**既有失败**（test_unconfirmed_lnkcrm_code_root_requires_explicit_override，
> 根因 docs 侧 company.yaml 已配置 lnkcrm code_root，/tmp 镜像回退本轮编辑后复跑
> 同样失败，与 B3 无因果，未修复——超出本轮清单，登记于执行记录 §5）、
> check_docs_consistency.sh FAIL=0 / WARN=0 / PASS=33、git diff --check 通过。
> 执行记录与证据指针见
> `references/adapter-capability-owner-decision-b3-execution-2026-10-04.md`。
> 本报告 §1-A5 行保持快照原文未重写（B1/B2 同口径）。O3 follow_up 的 B3 状态条目
> 未同步（该文件不在本轮授权清单内，待后续授权补记，见执行记录 §6.1）。
> **B4、B6、B7 仍为 pending / 冻结**，各自需独立授权；B3 完成不构成 registry 删除
> 批准。本状态回写不改变 registry 数据区、authority 或产品事实。

> **O5-lnkcrm-code 对账状态注记（2026-10-04 状态回写，路线 A）**：lnkcrm code 冻结线
> 经用户会话授权完成对账——ratify docs 已提交事实 c41a978 为现行基线：lnkcrm
> code_root = /opt/code/lnkcrm（revision 4323b8c…，source=company.yaml），code
> authority.status = complete。其余冻结线不变：lnkgateway ontology=unresolved（不得
> 跨产品 fallback）；lnkwebsite prd-only / ontology not-applicable。授权来源为本轮
> 用户会话明确授权；**独立 owner 签署记录未记录**，不得表述为已完成独立签署
> （B1/B2/B5/B3 同口径）。实施：三处测试断言改指新基线（shared/product_context 的
> test_adapter_status_migration_gate.py 与 test_resolver.py、product-prd-generator 的
> test_paths.py，均不弱化），B3 注记与 B3 执行记录 §5 登记的既有失败
> （test_unconfirmed_lnkcrm_code_root_requires_explicit_override）就此消除（历史注记
> 按惯例不重写，处置状态以本注记承载）。验证（对账会话实测）：shared 套件 53 tests
> 全绿、product-prd-generator 169 passed / 3 skipped（B2 基线恢复）、
> check_docs_consistency.sh FAIL=0 / WARN=0 / PASS=33。执行记录见
> `references/adapter-capability-owner-decision-lnkcrm-freeze-reconcile-2026-10-04.md`。
> 本对账**仅 ratify lnkcrm code 维度**：不构成 registry 删除、O4 字段删除或 O5 其余
> 子项批准；B4/B6/B7 与 O6-O11 仍冻结；registry 数据区、resolver 生产代码、
> company.yaml、30-products/**、产品代码零改动。

> **B4 状态注记（2026-10-04 状态回写）**：B4 已执行并通过验证。授权来源为
> MECH-BATCH-STANDING 用户会话授权（一次性批量放行，见
> `references/adapter-capability-owner-decision-mechanical-batch-standing-2026-10-04.md`）；
> **独立 owner 签署记录未记录**，不得表述为已完成独立签署（与 B1/B2/B5/B3 同口径）。
> 实施：`product-registry.yaml` 头部规则 6 注释改写——路径解析运行时唯一权威源 =
> resolver（`_paths.resolve_product_paths()`），本表保留为迁移期兼容元数据/历史镜像，
> 不构成双源同步义务（原「改一边必须改另一边」契约撤销）；**YAML 数据区零改动**
> （git diff -U0 全文件非注释行 = 0，yaml.safe_load 8 产品键完整）。相邻残留
> （登记未改，不在 B4 授权「仅规则 6」范围）：规则 8 末句「本表与代码解析保持同步」、
> 规则 10(c)「路径同步对」措辞、`_paths.py` :40/:44/:319 描述性登记指针——清理需后续
> 独立授权。验证（B4 执行会话实测）：prd-gen 169 passed / 3 skipped、shared 53 OK、
> check_docs_consistency.sh FAIL=0 / WARN=0 / PASS=33、git diff --check 通过。执行
> 记录见 `references/adapter-capability-owner-decision-b4-execution-2026-10-04.md`。
> B4 解除不构成 registry 删除或 adapter_status 删除批准。本状态回写不改变 registry
> 数据区、authority 或产品事实。

> **B6 状态注记（2026-10-04 状态回写）**：B6 已执行并通过验证。授权来源为
> MECH-BATCH-STANDING 用户会话授权（同上 standing 记录）；**独立 owner 签署记录
> 未记录**（同口径）。实施：prd-gen `references/adapter-capabilities.yaml` 8 处
> evidence 首条自 registry 条目改指本审计 §3（per-product 冻结快照值与差异语义保留，
> lnkgateway=blocked / lnkwebsite=not-applicable 枚举性差异说明随迁）+ 头部 3 行
> 迁移说明注释（同时指向本审计 §2/§3 与 O3/Batch 2 决策记录）；schema 测试
> `test_adapter_capabilities_schema.py` 两处说明性注释更新（溯源例外已消除，不再
> 描述为当前迁移目标；测试逻辑/状态矩阵/静态禁令零改动）。不变量：六态 status、
> 8 产品键、schema_version、verified_at 全部零变化；其余 5 个 capability 文件零
> 改动。验证（B6 执行会话实测）：capability schema 10 tests OK、O4 门禁与冻结线
> 12 tests OK（lnkgateway unresolved / lnkwebsite prd-only·not-applicable /
> lnkcrm complete / O4 白名单扫描）、全 suite shared 53 OK + prd-gen 169 passed /
> 3 skipped、check_docs_consistency.sh FAIL=0 / WARN=0 / PASS=33。执行记录见
> `references/adapter-capability-owner-decision-b6-execution-2026-10-04.md`。
> B6 解除不构成 registry 删除、adapter_status 删除或 O4 字段删除批准。本状态回写
> 不改变 registry 数据区、authority 或产品事实。

> **B7 状态注记（2026-10-04 状态回写）**：B7 已执行并通过验证（C1 最小修改；
> C2 verified-no-change）。授权来源为 MECH-BATCH-STANDING 用户会话授权（同上
> standing 记录）；**独立 owner 签署记录未记录**（同口径）。工作区重叠检查：两 docs
> 目标文件 targeted git status 为空，与既有未提交修改零重叠（无
> blocked-by-worktree-overlap）。实施 C1：`30-products/external-owner-decisions-2026-10-02.md:5`
> 回填通道描述改指当前有效路径（company.yaml products 经 onboarding 契约 + skill 侧
> resolver + `30-products/<产品>/` 产品治理记录；原 registry/_paths 通道标注为
> 2026-10-04 起迁移期兼容元数据/历史镜像，历史证据指针未删除）。C2
> （`domain-architecture-migration-2026-09-26.md:33`）判定 verified-no-change：带日期
> 历史注记、预测已发生且已解决（现行 registry lnkcre ontology_note 已指向新布局）、
> 无现行机制误述，不重写历史。验证（B7 执行会话实测）：docs 仓 git diff --check
> 通过、diff 仅新增 C1 目标一个 M（单行 hunk）；skill 侧全 suite 同批全绿。执行
> 记录见 `references/adapter-capability-owner-decision-b7-execution-2026-10-04.md`。
> docs 仓其余文件、company.yaml、30-products 产品内容、产品代码仓零改动。B7 解除
> 不构成 registry 删除或 adapter_status 删除批准。

> **R1 状态注记（2026-10-04 状态回写，README 冻结线 prose 对齐）**：R1 已完成——
> `shared/product_context/README.md` 冻结线 prose（原 :51-53「lnkcrm code
> `present-unconfirmed`」）已对齐 lnkcrm code=`complete` 基线（company.yaml
> code_root=/opt/code/lnkcrm，O5-lnkcrm-code 路线 A ratify；对账记录 §6.1 登记的
> 缺口就此闭合）。其余冻结线未变：lnkgateway ontology=unresolved
> （ontology_entry=null）；lnkwebsite prd-only / ontology not-applicable。
> O4 门禁测试、resolver 生产代码、company.yaml、30-products/**、产品代码、
> product-registry.yaml 零改动。授权来源为本轮用户会话明确授权；**独立 owner
> 签署记录未记录**（同口径）。执行记录见
> `references/adapter-capability-owner-decision-r1-readme-freeze-prose-2026-10-04.md`。
> 本状态回写不改变 registry 数据区、authority 或产品事实。

> **RESIDUAL-CLEANUP-R2 状态注记（2026-10-04 状态回写，文案/fixture/follow_up 残留
> 批量闭合）**：B4 注记登记的三处相邻残留、lnkcrm-freeze-reconcile §6.4 登记的
> fixture 旧 reason、B3 执行记录 §6.1 登记的 O3 follow_up 补记缺口，经用户会话
> 授权（RESIDUAL-CLEANUP-R2，一次性批量、不延续 MECH-BATCH-STANDING）批量闭合，
> 子项 A/B/C 全部 completed：**A** —— registry 头部规则 8 末句「本表与代码解析
> 保持同步」与规则 10(c)「（含注册入口、规则 6 与 _paths 的路径同步对）」、
> `_paths.py` :40/:44/:319 描述性 registry 指针，均对齐现行事实（路径与 authority
> 来源 = company.yaml/resolver；`_PRODUCT_CANONICAL_DIR` = 代码侧目录别名/映射
> 实现细节、非台账来源、需补时仍维护；registry = 迁移期兼容元数据/历史镜像；
> 注册入口 = onboard.sh product + company.yaml products），仅注释/docstring；
> **B** —— `tests/test_product_authority_fixtures.py` 判定为当前基线镜像（非历史
> 负例），lnkcrm code fixture 改 resolved + authority_ref=/opt/code/lnkcrm +
> revision=4323b8c9f6f195dd82083348dd6e854e7360afa3（source=company.yaml 走注释），
> unresolved 断言移除 lnkcrm/code 项并补三条正向断言，其余 unresolved reason
> 检查未弱化；**C** —— O3 follow_up 缺失 B3 条目实证成立，追加一条简洁状态指针
> （历史条目零改动）。验证（R2 会话实测）：prd-gen 169 passed / 3 skipped（编辑前
> 基线同值）、shared 53 OK、check_docs_consistency.sh FAIL=0 / WARN=0 / PASS=33、
> git diff --check 通过、registry diff 纯注释（非注释变更行 = 0）且 8 产品键完整、
> 冻结快照原值（lnkcrm code_root=null/onboarding、lnkgateway ontology=null、
> lnkwebsite ontology=null）。授权来源为用户会话授权；**独立 owner 签署记录未
> 记录**，不得表述为已完成独立签署（同口径）。执行记录见
> `references/adapter-capability-owner-decision-residual-cleanup-r2-2026-10-04.md`。
> 本回写不改变 registry 数据区、authority 或产品事实；B4/B6/B7 已完成状态与
> O4-O11 冻结状态不变；R2 完成不构成 registry 删除或任何字段删除批准。

> **RESIDUAL-CLEANUP-R3 状态注记（2026-10-04 状态回写，文档/注释/状态指针残留
> 闭合）**：R2 执行记录 §6 登记的四类残留，经用户会话授权（RESIDUAL-CLEANUP-R3，
> 新的一次性授权，不延续 MECH-BATCH-STANDING 或 R2）逐项处置：**目标 1（completed）**
> —— `_paths.py` `_legacy_fallback_enabled` docstring（R2 时代 :159，执行时 :161-163）
> 描述性 product-registry 引用更新：保留 docs 侧 `product-registry-feedback.yaml`
> 历史证据指针并明确其与 skill 侧 registry 为两文件，补「当前产品与路径事实来源 =
> company.yaml / resolver（resolver-first）；skill 侧 product-registry.yaml 仅为
> 迁移期兼容元数据/历史镜像」，仅 docstring，行为零改动；**目标 2（completed）**——
> `tests/test_product_authority_fixtures.py` lnkcrm ontology 行注释由「draft v0.1 /
> no accepted version yet」更新为现行基线（ontology accepted v1.0，SEM-CRM-OPS-001，
> OPC 2026-10-02，规则 9；resolver complete / revision v1.0；code complete per
> O5-lnkcrm-code 对账），fixture 数据与断言零改动；**目标 3（verified-no-change）**——
> registry 规则 8 末句经核对已是 R2 完成的 B4 对齐文案，全文件无残留路径同步短语，
> 本轮对该文件零写入；**目标 4（completed）**—— O3 follow_up 核对无 B4/B5/B6/B7
> 条目（缺失实证成立），末尾纯追加 4 条状态指针（既有 7 条零改动，计数 7→11），
> 各含会话授权事实、独立 owner 签署未记录、执行记录路径、不构成 registry 删除
> 批准四要素；B7 条目末句附记 B1-B7 全部解除。验证（R3 会话实测）：prd-gen
> 169 passed / 3 skipped、shared 53 OK、check_docs_consistency.sh FAIL=0 / WARN=0 /
> PASS=33、git diff --check 通过、目标行均位于既有 hunk 间未变区域（无
> blocked-by-worktree-overlap）。授权来源为用户会话授权；**独立 owner 签署记录未
> 记录**，不得表述为已完成独立签署（同口径）。执行记录见
> `references/adapter-capability-owner-decision-residual-cleanup-r3-2026-10-04.md`。
> 本回写不改变 registry 数据区、authority 或产品事实；registry 删除、O4 字段删除、
> O5 其余子项、O6-O11 仍需独立授权。

> **RESIDUAL-CLEANUP-R4 状态注记（2026-10-04 状态回写，规则 8 首句对齐 + prose
> 残留族关闭宣告）**：R3 §6.1 登记的唯一残留——registry 头部规则 8 首句
> 「以本表登记为准」（:30 本体行，lnkvision canonical 登记事实的权威源表述）——
> 经用户会话授权（RESIDUAL-CLEANUP-R4，新的一次性授权，不延续 MECH-BATCH-STANDING/
> R2/R3）对齐为「现行事实来源 = company.yaml / 治理 README / resolver，本表仅为
> 迁移期兼容元数据/历史镜像」；lnkvision 既有事实（无 ontology.yaml、canonical
> 本体为域知识.md、2026-09-26 修复 + tests/test_paths.py 回归闸）与规则 6 / 规则 8
> 其余句子 / 规则 9 / 规则 10 全部原样；YAML 数据区零改动（编辑前后
> yaml.safe_load 双 dump 逐字节一致，8 产品键完整、冻结快照值不变）。授权关键词
> 有界复扫（仅该文件）：6 命中全部 intended（规则 6/10(b)/10(c) 撤销表述）或
> 关键词语义外（规则 7「双源不并存」指 out/prd 生成区 vs canonical 晋升机制），
> **0 新残留、0 needs-separate-authorization**。**「迁移期 prose 残留族」（把本表
> 表述为权威源/双源同步义务来源的注释措辞族）就此关闭**；registry 删除、
> adapter_status 删除、O4 字段删除、O5 其余子项、O6-O11 维持冻结（不因宣告解冻）。
> 验证（R4 会话实测）：prd-gen 169 passed / 3 skipped、shared 53 OK、
> check_docs_consistency.sh FAIL=0 / WARN=0 / PASS=33、git diff --check 通过。
> 授权来源为用户会话授权；**独立 owner 签署记录未记录**，不得表述为已完成独立
> 签署（同口径）。执行记录见
> `references/adapter-capability-owner-decision-residual-cleanup-r4-2026-10-04.md`。
> 本回写不改变 registry 数据区、authority 或产品事实。

> **收官注记（D1，2026-10-04）——B 系列审计闭卷**：owner（OPC）批准独立删除动作
> （决策记录 `references/adapter-capability-owner-decision-d1-registry-retire-2026-10-04.md`，
> status=approved，OWNER SIGN-OFF: RECORDED (OPC)），本审计对象
> `skills/business/product-prd-generator/references/product-registry.yaml` 已物理退役
> （git rm，2026-10-04）。B1-B7 删除阻塞项此前已全部解除并落库（b171b28），本轮起
> B 系列审计闭卷；§1-§3 的消费方/字段/对齐矩阵自此为**历史快照**（对账退役前状态，
> 不再更新）。产品与路径事实 = company.yaml + shared.product_context resolver；
> adapter capability 权威源 = 各消费 skill 的 references/adapter-capabilities.yaml。
> 执行记录见 `references/adapter-capability-owner-decision-d1-execution-2026-10-04.md`。
> adapter_status 字段退役为 D2 独立动作（另见 D2 决策/执行记录），不在本注记范围内。

## 5. 本轮已落的迁移兼容说明（approved_changes 3）

| 文件 | 更新内容 |
|---|---|
| `skills/business/product-prd-generator/references/product-registry.yaml` | 头部规则 10 改写：capability 权威源指向 `references/adapter-capabilities.yaml`；本表 adapter_status 冻结为兼容快照（含 lnkgateway/lnkwebsite 枚举性差异说明）；删除本表 = 独立 owner 批准 + 阻塞项指针。**YAML 数据区零改动** |
| `references/product-semantic-baseline.md` §3 | 迁移期注记：adapter_status 的 per-consumer 权威源迁移至 capability 文件；本表字段冻结；指针至本审计 |
| `references/product-governance/README.md` | 迁移期注记一句（英文，随该文档语言）：capability authority 落位、registry 冻结快照、审计指针 |

## 6. 未做事项（与 O3 forbidden_changes 对账）

- 未删除 / 未修改 product-registry.yaml 任何字段（仅头部注释）；
- 未建立公共 adapter capability registry（skill 仓 / docs 均未新增中心文件）；
- 未修改 resolver（`shared/product_context/**` 零改动）；
- 未修改 company.yaml；未修改 `30-products/**`（docs 仓零改动）；未触碰产品代码仓；
- 未执行 O4 实际迁移（adapter_status 字段级迁移实施冻结，「兼容保留 + 禁止新增依赖」维持）；
- 未执行 O5-O11；
- 未提交、未推送；
- 未回退 / 未覆盖两仓其他会话的既有未提交修改。

## 7. 维护

- 本报告是 2026-10-04 快照；新增 registry 消费方、字段变更或阻塞项解除时更新 §1/§2/§4。
- 阻塞项状态变化（B1-B7 逐项解除）应同步反映到 O3 决策记录 follow_up 与本 §4。
