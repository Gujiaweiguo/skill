# Owner Decision —— LNKRETAIL-PARTIAL：product-prd-generator×lnkretail onboarding→partial；lnkmember 维持 onboarding

decision_id: LNKRETAIL-PARTIAL
decision_date: 2026-11-27
owner: OPC（本治理域决策 owner）
origin: OPC 会话裁决「1.升级」——对 skill 会话 2026-11-27 提交的两条草稿整体批准：
       ① lnkretail 升 partial 并按现状重写 evidence；② lnkmember 保持 onboarding、evidence 补重生成事实
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: decided
decision: lnkretail-partial（product-prd-generator×lnkretail：onboarding → partial）
         lnkmember-stays-onboarding（product-prd-generator×lnkmember：维持 onboarding，仅刷新 evidence）

company_ids: [lanlnk]
product_ids: [lnkretail, lnkmember]
consumer_ids: [product-prd-generator]

approved_changes:
  - product-prd-generator/references/adapter-capabilities.yaml lnkretail 条目：onboarding → partial
    + evidence 重写（31 能力族；代码仓 36 个提交 / 15 个 scope / 11 个已归档 change；
    多版 PRD 评审记录 v0.2 至 v0.17；最近一次对账 48 项 = 37 present-unconfirmed + 11 partial）
    + verified_at 2026-11-21 → 2026-11-27
    + notes（partial 口径：37/48 能力未被归档证据覆盖，全部波次完成并复核前不得升 implemented）
  - 同文件 lnkmember 条目：status 不变（onboarding），evidence 第 3 条与 notes 按 2026-11-27 事实刷新
  - shared schema 钉线同批：EXPECTED_MATRIX 一格（onboarding → partial）+ EXPECTED_DISTRIBUTION
    （partial 13→14 / onboarding 13→12）+ 该格 verified_at 钉（2026-11-21 → 2026-11-27）
  - docs 侧登记注记：30-products/lnkretail/ontology/README.md「skill 侧」一行仍写
    「status onboarding」与「以上 skill 侧改动截至 2026-11-23 未提交」，两句均已过时——
    由 docs 会话按 skill 会话给出的提示词落盘（docs 仓不由 skill 会话写）

forbidden_changes:
  - 其余消费者的任何 capability 状态
  - resolver 生产代码 / company.yaml 结构字段（capability 文件不进运行时，方案 B 红线不变）
  - lnkretail 记 implemented（37/48 能力尚未被归档证据覆盖，后续波次未完成）
  - lnkmember 升 partial 或 implemented（仅单次规划型生成、候选未晋升、代码仓为空）

evidence:
  - 真实运行先例：docs 仓 30-products/lnkretail/reconciliation/ 下 PRD 评审记录 5 份
    （prd-v0.2 至 prd-v0.17，2026-11-22 至 11-27）；canonical PRD 在位（prd/baseline/产品PRD.md）
  - 代码基线：代码仓 36 个提交（HEAD 2026-11-27）、15 个 OpenSpec scope、
    11 个已归档 change（2026-11-23 至 11-26）；规则文件启用归档证据驱动的能力状态
  - 能力对账：docs 仓 raw/prd-lnkretail/parsed/capability-reconciliation.json（2026-11-27 08:07）
    48 项 = 37 present-unconfirmed + 11 partial
  - 能力地图：30-products/lnkretail/ontology/target-capability-map.md 31 能力族（旧 evidence 写 28，已过时）
  - 规则口径：AGENTS.md「capability implemented 红线」（授权 ≠ 运行证据；升 implemented 需真实运行先例）
  - lnkmember：代码仓 0 个提交；首版生成区候选已产出、重生成并提交到 docs 仓，未晋升 canonical

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
override: OPC 可改裁 lnkretail 维持 onboarding 或升 implemented、lnkmember 升 partial——届时另落记录并同批改钉线。

本记录仅覆盖上述两格的状态与 evidence；不构成任何其余消费者、其余产品或定价事项的批准。
