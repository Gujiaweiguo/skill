# Owner 决策记录 —— adapter capability 治理（草案 / 待签署）

```text
STATUS: DRAFT
NOT AN APPROVAL RECORD
OWNER SIGN-OFF REQUIRED
```

## 填写规则

1. 本文件是**待签署表单草案**，不是批准记录，不放入正式治理 registry。
2. 允许的 `status` 值：`pending` | `approved` | `rejected` | `deferred`。
3. **未填写的字段不得解释为批准**；空字段 = 未决。
4. 任何 `approved` 只作用于该决策块 `approved_batch` / `approved_changes` 明确列出的
   范围；`forbidden_changes` 列出的动作即使在该决策 approved 后仍然禁止。
5. 批准不自动传导：O1 不自动批准 O4；O4 不自动批准 O5；O5 不自动批准任何业务基线
   （O6-O11 各自独立签署）。
6. owner 签署方式：逐块填写 `decision_date` / `owner` / `status` / `decision` /
   `approved_batch` / `approved_changes`。签署后由 owner 指定方式转为正式决策记录。
7. 批次定义见建议包 §4.1：Batch 1 = 首版 capability 文件；Batch 2 = registry/resolver
   迁移；Batch 3 = 业务基线执行；Batch 4 = lnkcrm 晋升实施。

## 全局字段

```yaml
schema_version: adapter-capability-decision-draft/v1
generated_at: 2026-10-04
owner:                                # 待填（opc）
company_ids: [lanlnk]
basis:
  - references/adapter-capability-decision-2026-10.md      # 设计包（O1-O11 定义）
  - references/adapter-capability-owner-recommendation-2026-10.md  # 建议包（本表单依据）
lnkcrm_freeze_line:                   # 签署任何决策块前均维持
  company_yaml_code_root: null
  layers_code_root: null
  authority_code_status: present-unconfirmed
```

---

## D-O1 方案 B（capability 消费方自声明）

```yaml
decision_id: O1
decision_date:
owner:
status: pending
scope: 批准方案 B 设计（含状态语义与 schema 草案）+ Batch 1 首版 capability 文件
company_ids: [lanlnk]
product_ids: [lnkcre, lnkcrm, lnkchat, lnkchatbi, lnkreport, lnkvision, lnkgateway, lnkwebsite]
consumer_ids: [product-prd-generator, requirement-evaluator, pricing-generator, competitor-product-analyzer, company-intro-generator, strategy-brief-generator]
decision:                             # owner 填写：批准 / 修改 / 拒绝
approved_batch:                       # 如：Batch 1（schema 定稿 + 六消费方首版文件）
approved_changes:                     # owner 明确列出批准的变更范围
forbidden_changes:
  - 在 capability 文件中出现产品事实字段（docs_root/code_root/ontology_path/prd_root/revision）
  - 建立新的中心产品注册表
  - 修改 company.yaml / resolver authority 语义
schema_version: 1
evidence: 设计包 §5/§6/§2.2/附录A；建议包 §3.1
follow_up: Batch 1 实施（六消费方首版 adapter-capabilities.yaml + 聚合校验脚本）
```

## D-O2 48 格矩阵现状判定（可随 O1 一并确认，或单独审议）

```yaml
decision_id: O2
decision_date:
owner:
status: pending
scope: 设计包 §3 六消费方×八产品矩阵首版值（含 3 处 ★ 改判：prd-gen×lnkwebsite、pricing×lnkgateway、company-intro×lnkgateway → not-applicable）
company_ids: [lanlnk]
product_ids: [全部 8 产品]
consumer_ids: [全部 6 消费方]
decision:
approved_batch:                       # 如：随 Batch 1 一并生效
approved_changes:
forbidden_changes:
  - 将矩阵值写入 resolver 或 company.yaml
  - 矩阵 recommended 值在 owner 确认前生效
schema_version: 1
evidence: 设计包 §3.2/§3.3
follow_up: 首版 capability 文件以本矩阵为内容源
```

## D-O3 方案 C 豁免（条件性：仅当 owner 拒 B 选 C 时填写）

```yaml
decision_id: O3
decision_date:
owner:
status: pending                       # B 方案被批准则本块保持 pending 且不触发
scope: 明示豁免「不建第二套中心注册表」惯例 + 中心 capability 文件位置与所有权
company_ids: [lanlnk]
product_ids: []
consumer_ids: []
decision:
approved_batch:
approved_changes:
forbidden_changes:
  - 未经本块批准采用方案 C
schema_version: 1
evidence: 设计包 §5 方案 C 分析
follow_up: 若触发，另出 C 方案落位设计
```

## D-O4 resolver adapter_status 迁移（过渡期）

```yaml
decision_id: O4
decision_date:
owner:
status: pending
scope: 批准五步迁移策略（本阶段不删除字段）；步骤 5（删除 resolver.adapter_status）建议要求再次签署
company_ids: [lanlnk]
product_ids: [全部 8 产品]
consumer_ids: [全部 6 消费方]          # 读取方迁移面
decision:
approved_batch:                       # 如：Batch 2（前置：Batch 1 完成）
approved_changes:
forbidden_changes:
  - 在读取方迁移完成前删除 adapter_status 字段
  - 新增任何 adapter_status 消费逻辑
  - 本轮（建议阶段）修改 resolver
schema_version: 1
evidence: 设计包 §1.1/§9-O4/§7-S4；建议包 §1.3/§3.4（8 产品全输出 unsupported 实测）
follow_up: ①建 capability 声明 → ②迁移读取方 → ③兼容告警 → ④停止新增依赖 → ⑤owner 确认后删除
```

## D-O5 lnkcrm code authority 晋升（deferred / conditional）

```yaml
decision_id: O5
decision_date:
owner:
status: pending                       # 建议值：deferred（条件性确认后再 approved）
scope: lnkcrm code authority 是否正式晋升（Batch 4 是否启动）
company_ids: [lanlnk]
product_ids: [lnkcrm]
consumer_ids: [requirement-evaluator, strategy-brief-generator, product-prd-generator]   # 建议验证最小集，owner 可改
decision:
approved_batch:
approved_changes:
forbidden_changes:                    # 正式批准前（五问未答齐）禁止
  - 修改 company.yaml（code_root: null → /opt/code/lnkcrm）
  - 修改 30-products/lnkcrm/INDEX.md
  - 修改 30-products/lnkcrm/code/README.md
  - 修改 reconciliation 台账
  - 升级 authority.code.status（present-unconfirmed → complete）
  - 启动 Batch 4
schema_version: 1
evidence: 设计包 §12；建议包 §1.2/§3.5（revision 漂移 ad6f0c0b→1d5ebb6b 实证）
follow_up: owner 五问 —— ①正式 authority？②允许改 company.yaml？③生效 revision？
  ④27 个 OpenSpec scope 是否纳入基线？⑤INDEX/code README/reconciliation 更新范围与验证 adapter 集？
```

## D-O6 正祥 CRM 定价归属（historical evidence 登记）

```yaml
decision_id: O6
decision_date:
owner:
status: pending                       # 建议值：暂不追认为正式基线，先登记 historical evidence
scope: pricing-generator CRM_DATA（正祥交付物受管副本）是否追认为 lnkcrm 报价基线
company_ids: [lanlnk]
product_ids: [lnkcrm]
consumer_ids: [pricing-generator]
decision:
approved_batch:                       # 如：Batch 3（仅 evidence 归属登记动作）
approved_changes:
forbidden_changes:
  - 将正祥定价直接当作 lnkcrm 标准定价使用（未确认前）
  - 从 lnkcre 复制价格顶替
schema_version: 1
evidence: 设计包 §3.3.C/§9-O6；建议包 §3.6
follow_up: 转正式 baseline 前必须确认：适用产品 / 适用版本 / 价格有效期 / 标准与定制边界 /
  owner / 是否可对外使用
```

## D-O7-chat lnkchat 报价定位

```yaml
decision_id: O7-chat
decision_date:
owner:
status: pending                       # 建议值：pending positioning
scope: lnkchat 独立产品报价 vs AI 岗位 Skill 服务打包售卖
company_ids: [lanlnk]
product_ids: [lnkchat]
consumer_ids: [pricing-generator]
decision:
approved_batch:
approved_changes:
forbidden_changes:
  - 定位未确认前建立 lnkchat 报价基线
  - 从 lnkcre 或其他产品复制价格
schema_version: 1
evidence: 设计包 §3.3.C/§13.1；建议包 §3.7
follow_up: owner 确认定位后决定是否建基线
```

## D-O7-report lnkreport 报价基线

```yaml
decision_id: O7-report
decision_date:
owner:
status: pending                       # 建议值：onboarding（建独立功能与价格基线）
scope: lnkreport 独立产品功能与报价基线建设
company_ids: [lanlnk]
product_ids: [lnkreport]
consumer_ids: [pricing-generator]
decision:
approved_batch:
approved_changes:
forbidden_changes:
  - 从 lnkcre 或其他产品复制价格
schema_version: 1
evidence: 设计包 §3.3.C；建议包 §3.7
follow_up: 功能清单 → 定价 → pricing-basis.yaml 登记（各步 owner 确认）
```

## D-O7-vision lnkvision 报价定位

```yaml
decision_id: O7-vision
decision_date:
owner:
status: pending                       # 建议值：positioning decision required
scope: lnkvision 产品定位与是否面客，再决定报价
company_ids: [lanlnk]
product_ids: [lnkvision]
consumer_ids: [pricing-generator]
decision:
approved_batch:
approved_changes:
forbidden_changes:
  - 定位未确认前建立报价基线
  - 从 lnkcre 或其他产品复制价格
schema_version: 1
evidence: 设计包 §3.3.C；建议包 §3.7
follow_up: 与 D-O10-vision、D-O9 定位问题联动审议
```

## D-O8 LnkChatBI 标准定价基线

```yaml
decision_id: O8
decision_date:
owner:
status: pending                       # 建议值：可批准建设（前置条件齐 + owner 确认落盘）
scope: lnkchatbi 标准定价登记入 pricing-basis.yaml（替换 env 默认 0）
company_ids: [lanlnk]
product_ids: [lnkchatbi]
consumer_ids: [pricing-generator]
decision:
approved_batch:                       # 如：Batch 3
approved_changes:
forbidden_changes:
  - 套用 lnkchat 或 lnkcre 价格
  - 前置条件未齐时写 pricing-basis.yaml
schema_version: 1
evidence: 设计包 §3.3.C/§9-O8；建议包 §3.8
follow_up: 前置 4 条件 —— 标准功能清单来源 / 标准版与定制版边界 / 定价生效日期 /
  pricing-basis.yaml 写入范围（owner 确认）
```

## D-O9 lnkgateway 产品定位

```yaml
decision_id: O9
decision_date:
owner:
status: pending                       # 建议值：暂不独立面客（平台基础设施 / 集成网关 / 内部能力）
scope: lnkgateway 是否永不独立面客（影响 pricing/company-intro 的 not-applicable 落地）
company_ids: [lanlnk]
product_ids: [lnkgateway]
consumer_ids: [pricing-generator, company-intro-generator]
decision:
approved_batch:
approved_changes:
forbidden_changes:
  - 在 ontology/PRD unresolved 期间建立独立报价 / 竞品能力 / 公司介绍基线
schema_version: 1
evidence: 设计包 §3.3.C/§3.3.E/§13.2；建议包 §3.9
follow_up: 与 D-O11 联动；若裁定 not-applicable 随 Batch 1 矩阵 ★ 改判落地
```

## D-O10-report lnkreport 叙事资产

```yaml
decision_id: O10-report
decision_date:
owner:
status: pending                       # 建议值：可启动叙事资产建设
scope: company-intro 面的 lnkreport 产品叙事资产
company_ids: [lanlnk]
product_ids: [lnkreport]
consumer_ids: [company-intro-generator]
decision:
approved_batch:
approved_changes:
forbidden_changes:
  - 用其他产品叙事顶替
schema_version: 1
evidence: 设计包 §3.3.E/§9-O10；建议包 §3.10
follow_up: materials/03-products/ 新增 lnkreport 产品叙事（Batch 3）
```

## D-O10-vision lnkvision 叙事资产

```yaml
decision_id: O10-vision
decision_date:
owner:
status: pending                       # 建议值：先确认定位/目标客户/与 lnkreport 边界
scope: lnkvision 叙事资产前置定位确认
company_ids: [lanlnk]
product_ids: [lnkvision]
consumer_ids: [company-intro-generator]
decision:
approved_batch:
approved_changes:
forbidden_changes:
  - 定位未确认前建设叙事资产
schema_version: 1
evidence: 设计包 §3.3.E；建议包 §3.10
follow_up: 与 D-O7-vision、D-O9 联动审议
```

## D-O11 lnkgateway ontology 处置方向

```yaml
decision_id: O11
decision_date:
owner:
status: pending                       # 建议值：短期保持 unresolved，不从代码反推
scope: lnkgateway ontology 长期方向三选一
company_ids: [lanlnk]
product_ids: [lnkgateway]
consumer_ids: [product-prd-generator, competitor-product-analyzer]   # blocked 解除受益方
decision:                             # owner 三选一：1 独立产品 ontology / 2 平台基础能力 ontology / 3 集成层能力不建独立 ontology
approved_batch:
approved_changes:
forbidden_changes:
  - 从网关代码反推 ontology（owner 既有裁定维持）
  - 未经本块批准自动创建任一种 ontology
schema_version: 1
evidence: 设计包 §3.3.A/§3.3.D/§9-O11；建议包 §3.11
follow_up: 短期维持 unresolved；解除 prd-gen/competitor blocked 的唯一路径是本决策落地
```

---

## 签署区

```yaml
owner_signature:                      # 待填
signed_at:                            # 待填（YYYY-MM-DD HH:mm TZ）
signing_note:                         # 可选：签署范围备注（如"仅 O1+O4，其余维持 pending"）
record_conversion:                    # 签署后由 owner 指定：转正式决策记录的位置与方式
```

> 再次声明：本文件在签署前 **不构成任何批准**。所有 Batch（1/2/3/4）保持冻结。
