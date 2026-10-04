# 公共 product_context 消费方审计（2026-10-04）

> 阶段：公共 `shared.product_context` resolver 已完成八产品完整性验收并接入
> `openspec-practice` 与 `product-prd-generator` 之后，对其他消费公司/产品/代码路径/
> PRD/ontology/adapter 元数据的业务 skill 做全局审计与风险分层迁移。
>
> 前提契约：`company.yaml → shared.product_context → 业务 skill → 产品 PRD/报价/
> 需求评估/竞品分析/方案编排`，禁止第三套、第四套产品路径解析规则。
>
> 语义边界（本审计全程遵守）：
> - **authority status**（complete / partial / unresolved / not-found / planned /
>   present-unconfirmed / inaccessible / prd-only / not-applicable）= 产品三层事实，
>   权威源 company.yaml + 30-products 治理 README，经 resolver 解析。
> - **adapter capability status**（implemented / partial / onboarding / unsupported）
>   = 某业务 skill 对某产品的支持度，必须带消费方名称。二者不得混用。
> - 「八产品上下文解析完整」≠「某业务 skill 对八产品能力支持完整」。各 skill 的
>   adapter 支持面见 §4 迁移结果。

## 1. 审计方法

全仓 rg（排除 `__pycache__/output/.venv/node_modules`）：

```bash
rg -n "product-registry|code_root|docs_root|ontology_root|prd_root|/opt/code/|company\.yaml|LANLNK_BASE|COMPANY_BASE|lnkcre|lnkchat|lnkcrm|langchat" /opt/code/skill/skills
```

命中文件 130+（计数清单存 `/tmp/opencode/audit/grep_counts.txt`，审计当日快照）。
每条命中按 10 类分类：

| # | 类型 | 判定 |
|---|---|---|
| 1 | 产品路径事实解析 | 运行时决定 30-products/<pid> / code_root / prd_root 等路径 |
| 2 | 产品 ID/alias 解析 | MI/MI-CRE/langchat → canonical id 归一 |
| 3 | canonical ontology/PRD authority 解析 | 读治理 README/company.yaml 判定权威入口 |
| 4 | 代码仓路径解析 | 决定或引用 /opt/code/<产品> |
| 5 | OpenSpec 目标仓解析 | 目标项目仓 scope/revision |
| 6 | 产品功能元数据 | 功能清单/基线/模块描述 |
| 7 | adapter capability 元数据 | product-registry.yaml 的 adapter_status 等 |
| 8 | 历史 fixture/归档证据 | tests fixture、archive、历史记录 |
| 9 | 文档示例 | 使用示例中的演示路径 |
| 10 | 无关普通文本 | 叙事内容（如 slide 文案「langchat 岗位数字人」）、治理说明 |

## 2. 消费方矩阵

已迁移基准（前阶段完成，本审计复核通过）：

| skill | 文件 | 读取来源 | 读取内容 | 路径事实? | 需迁移 | 风险 | 处理 |
|---|---|---|---|---|---|---|---|
| openspec-practice | scripts/resolve_context.py、SKILL.md | shared.product_context | 全量 context（JSON 边界） | 是（公共层） | 已完成 | 低 | 基准实现 |
| product-prd-generator | product_prd_generator/_paths.py | shared.product_context（`_shared_product_context`，resolver-first + 显式降级） | layers/authority/code_root | 是 | 已完成 | 低 | 基准实现；`_PRODUCT_CODE_ROOTS` 等表仅作 resolver 失败后的错误引导，不再自动给路径（`resolve_code_root` 对 null/未配置一律报错要显式 --code-root） |

本阶段六个审计对象：

| skill | 文件 | 当前读取来源 | 读取内容 | 是否路径事实 | 是否需迁移 | 风险 | 处理 |
|---|---|---|---|---|---|---|---|
| requirement-evaluator | SKILL.md（纯提示词） | SKILL.md 内硬编码契约：lnkcre baseline 路径表、lnkreport/lnkvision/lnkchatbi canonical+生成区映射表、Step 0 grep 默认 `/opt/code/lnkcre` | 类型 1（产品路径）+2（alias 表）+4（code 根默认）+6（功能清单定位） | 是 | **是（P0）** | 高：prompt 内维护产品-路径映射 + code 根默认值，正好命中禁止项「根据产品 ID 拼路径」「code_root null 自动猜」 | SKILL.md 契约改 resolver-first（resolve_context.py CLI），映射表降级为「生成区回退目录名」参考；Step 0 code 根改为 resolver context，present-unconfirmed 需显式确认 |
| pricing-generator | generate_quote.py | `_company_base.py`（公司级，合规）+ 硬编码 `30-products/lnkcre/prd/baseline/feature-baseline.yaml`；SKILL.md 路径契约同 requirement-evaluator | 类型 1（lnkcre baseline 路径）+6（功能基线统计） | 是（单产品） | **是（P0）** | 中：仅 lnkcre 单点硬编码，无跨产品回退；但属于运行时产品路径事实 | `_mi_feature_baseline_paths()` 改 resolver-first（prd_root 推导），原硬编码路径保留为 resolver 不可用时的兼容候选；加最小集成测试 |
| competitor-product-analyzer | SKILL.md（纯提示词） | SKILL.md：compatibility 引用 product-registry.yaml 为「产品注册表」；S1.2/S1.3 硬编码 ontology/baseline 路径；证据写入根硬编码 `30-products/lnkcre/evidence/...` | 类型 1+2+3（authority 入口）+7（registry 引用语义） | 是 | **是（P1）** | 中：prompt 编排，无需 Python；但把 registry 称作产品注册表违反「company.yaml 是唯一台账」 | 契约更新：路径事实指向 resolver；registry 降级为迁移期 adapter 元数据；lnkwebsite/lnkgateway 显式降级行为 |
| company-intro-generator | SKILL.md（V5 段）+ references/compile_v5_domain.py | V5 启动检查硬编码 `$LANLNK_BASE/30-products/lnkcre/ontology/architecture/domain-model/`（4 处）；compile 脚本仅公司级 env 展开 | 类型 3（lnkcre 本体层子路径） | 是（单产品单包） | **是（P1）** | 低-中：单产品单包路径，无产品列表、无 code 根 | V5 启动检查改 resolver-first（lnkcre ontology_root 推导 domain-model/），保留现路径为「当前值」说明；compile 脚本不动（公司级已合规） |
| strategy-brief-generator | SKILL.md + references/four-look-framework.md | company.yaml products（盘点台账）+ code_root 直接读 company.yaml | 类型 1（code_root 来源） | 部分（code_root 事实来源） | **是（P1，轻量）** | 低：多公司合规、无路径拼接；但 P4 盘点直接读 company.yaml code_root，未经 resolver 语义（present-unconfirmed/planned 状态缺失） | P4/源码类资料处理补 resolver 契约：code 状态经 resolver；code_root null（planned）不猜 /opt/code/<id> |
| material-importer | scripts/_company_base.py + 各脚本 | 公司基座（COMPANY_BASE ∥ LANLNK_BASE，无静默默认）+ incoming/raw/materials 三层；`batch_competitor_import.py` 的 `prd-商管系统` legacy raw 子目录（带目录存在性守卫 + 候选列出错） | 公司级路径 + 素材树约定 | **否**（不按产品 ID 决定 30-products canonical 目录） | **否（not-applicable）** | 低 | 不接入 product_context：其输入是文件与素材库，产品无关。`batch_competitor_import.py` 的 `prd-*` 是 raw 素材树历史命名（带守卫的兼容默认），不是 canonical 路径事实。若未来其按产品 ID 决定 canonical 目标目录再迁移 |

其他命中（非本阶段六对象，按发现处理）：

| skill | 命中分类 | 处理 |
|---|---|---|
| word-master / ppt-master / bid-doc-master（各 `_company_base.py` 副本 + SKILL.md 引用） | 公司级解析（类型 10 治理说明），无产品路径事实 | 不迁移；_company_base 副本协议与 resolver 的公司解析一致（COMPANIES.md §3） |
| bid-doc-master/src/main.py、word-master/src/renderer.py | 公司级 base 传参 | 不迁移 |
| project-proposal-generator SKILL.md | 素材库匹配（LANLNK_BASE/COMPANY_BASE 公司级 + 竞品对标 web 检索），无 30-products 路径事实 | 不迁移 |
| doc-generator / ops-manual-generator | USERGUIDE_BASE 从 COMPANY_BASE 派生（公司级）；ops-manual 的 `/opt/code/lnkcre` 为使用示例（类型 9） | 不迁移 |
| compound-learning SKILL.md | `30-products/<产品>/ontology/` 为治理说明（类型 10，复利写入指路） | 不迁移 |
| content-operations / case-operations / product-operations / comment-moderation / lead-operations / geo-operations / seo-audit / redirect-audit / site-health-operations | scope=lnkwebsite 的站点运营 contract skeleton，直接以 lnkwebsite 仓/表为契约目标，不做产品 ID→路径解析 | 不迁移 |
| product-prd-generator 各 tests / references（test_paths 等 15 文件） | 类型 7/8（registry 同步声明 + 回归 fixture） | 保留；registry 头部补 scope 说明（§5） |
| website-operations 各 contract-notes.md、crela-daily、winshang-crawler 等 | 类型 8/9/10 | 不迁移 |

## 3. 当前运行路由 vs 历史证据（不得混淆）

- **当前运行路由**（本阶段后）：产品路径事实只允许两个来源——resolver（company.yaml+
  治理 README）与各 skill 内经审计保留的兼容候选（pricing lnkcre baseline 回退候选、
  requirement-evaluator 生成区回退目录名）。
- **兼容 adapter**：`_PRODUCT_ALIASES`/`_PRODUCT_CANONICAL_DIR`（product-prd-generator，
  resolver 失败后的降级与 doc 扫描过滤）；pricing 的 `lnkcre_aliases` CLI 归一。
- **历史 fixture**：product-prd-generator 各 tests 的 8 产品路径断言（真实 docs 树回归闸）。
- **归档证据**：openspec/changes/archive、90-legacy（只读）。
- **示例**：ops-manual-generator 使用示例、domain-slide-config-schema.yaml 的 base_ppt 示例。
- **文档说明**：compound-learning/AGENTS.md 的 30-products 惯例说明。

## 4. 迁移结果与 adapter 支持面（防「全部产品已支持」笼统表述）

| skill | 实际迁移文件 | resolver 消费面 | adapter 支持的产品（skill 自身能力，非 resolver 能力） |
|---|---|---|---|
| requirement-evaluator | SKILL.md（产品功能清单定位、Step 0/P2.5 code 根、compatibility） | 路径契约层（prompt 消费 resolve_context.py 输出） | 评估基准产品依赖功能清单位置：lnkcre（baseline）+ lnkreport/lnkvision/lnkchatbi（功能清单.md，canonical/生成区）+ CRM/AI Skills（materials 文档）；其余产品（lnkchat/lnkgateway/lnkwebsite/lnkcrm）**未登记评估基线清单**，评估前需先由 product-prd-generator 产出功能清单 |
| pricing-generator | generate_quote.py（resolver-first baseline 候选）+ 新增 tests/test_product_context_integration.py | lnkcre 的 prd 层（功能基线统计，仅此一处产品路径事实） | 报价产品：MI/lnkcre、CRM、AI（岗位 Skill）、LNKCHATBI（硬编码定价数据）；其余产品无报价数据（adapter 不支持，与 resolver 无关） |
| competitor-product-analyzer | SKILL.md（compatibility、产品代号与竞品证据隔离、S1.2/S1.3、配置读取表） | 路径契约层 | 能力对照基线：lnkcre（ontology+baseline）；CRM/AI（materials 文档）；其余产品对照前需先建基线；lnkwebsite 明确不进 ontology-change-set 契约 |
| company-intro-generator | SKILL.md（V5 领域包启动检查） | lnkcre 的 ontology 层（V5 前置检查） | V5 仅 lnkcre（MI 工程领域架构包）；V1-V4 不消费产品路径事实 |
| strategy-brief-generator | SKILL.md（P4 自身能力盘点 + 源码类资料处理） | 路径契约层（code 状态语义） | 盘点面=company.yaml 全部产品（台账驱动），但 code 级盘点仅 code authority complete 的产品 |
| material-importer | 无（not-applicable） | 不消费 | 不适用（素材库与产品路径解耦） |

## 5. product-registry.yaml 迁移期定位（语义收敛）

- company.yaml 是唯一公司/产品事实台账（resolver 的数据源）。
- `product-prd-generator/references/product-registry.yaml` 在迁移期定位为 **adapter
  元数据**：其 `adapter_status` 描述 product-prd-generator（及未来显式登记的消费方）
  对该产品的 adapter 支持度，**不是** ontology/PRD/code authority 状态，**不是**公司/
  产品事实台账。
- 公共 resolver 禁止读取该文件（shared/product_context/README.md 已声明；本阶段在
  registry 头部补第 10 条规则显式化）。
- 业务 skill 禁止把该表字段解释为 authority 状态（requirement-evaluator /
  competitor-product-analyzer 的 SKILL.md 引用语义本阶段已同步改写）。
- **后续迁移项（owner 决策，不在本阶段做）**：建立 per-consumer
  `adapter_capabilities`（如 `product-prd-generator: {lnkcre: implemented, ...}`），
  或把 adapter 维度并入 company.yaml；在此之前不复制出第二套注册表。

## 6. lnkcrm present-unconfirmed 处理（各消费方）

| 消费方 | 行为 |
|---|---|
| resolver | code_root: null + 观察 checkout `/opt/code/lnkcrm` → code authority = present-unconfirmed（path/revision 仅证据），layers.code_root = null（回归闸 test_lnkcrm_code_stays_present_unconfirmed） |
| requirement-evaluator | Step 0/P2.5 代码验证不得自动用观察 checkout；需用户显式 `--code-root /opt/code/lnkcrm` 等价确认 |
| pricing-generator | 不消费 code 层（无影响）；功能基线缺失时警告降级，不跨产品 |
| competitor-product-analyzer | code_root 仅作只读证据定位；不自动当 configured authority |
| company-intro-generator | 不消费 code 层（无影响） |
| strategy-brief-generator | code_root null（planned）→ P4 盘点降级为 materials 资料路径，不猜 /opt/code/lnkcrm |
| product-prd-generator | resolve_code_root 对未配置/非 complete 一律 MissingProductDataError（要显式 --code-root） |

## 7. 未迁移项与理由

见 §2 矩阵「处理」列。核心：material-importer not-applicable（素材树与产品路径解耦）；
word/ppt/bid-doc/project-proposal/doc/ops-manual/compound-learning/website-operations 系
公司级或示例/说明类命中，无产品路径事实消费。

## 8. 维护

- 本报告是 2026-10-04 快照；新增 skill 或新增产品路径消费时更新矩阵。
- 路由残留检查命令与通过标准见最终报告（每阶段收尾必跑）。
