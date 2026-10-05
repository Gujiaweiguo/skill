# Owner Decision —— O5-Q4（lnkcrm OpenSpec 27 scope 纳入产品实现基线）

decision_id: O5-Q4（文档未分配独立子编号；本 ID 为盘点报告 §3.1 拆列口径，不构成编号定义）
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: 本会话 OPC 点名执行 O5-Q4（OpenSpec 27 scope 基线纳入）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: approved
decision: include（27 个 OpenSpec scope 纳入产品实现基线，参与评估/对照/回写）

scope: /opt/code/lnkcrm/openspec 的 spec scope 集合（member-*/coupon-*/points-*/merchant-*/platform-*/tenancy 等；设计包 2026-10-03 观察值 27 个，2026-10-04 本记录落盘时实测 28 个——基线锚定 scope 集合本身，允许随活跃开发增长，不钉数量）作为 lnkcrm 产品实现基线参与后续评估
company_ids: [lanlnk]
product_ids: [lnkcrm]
consumer_ids: [requirement-evaluator, competitor-product-analyzer, openspec-practice]

approved_changes:
  - requirement-evaluator：Step 0 代码 grep 面纳入 /opt/code/lnkcrm（27 scope）
  - competitor-product-analyzer：status_vs_lanlnk 判定输入纳入 lnkcrm scope 基线
  - openspec-practice：回写链路把 lnkcrm scope 纳入产品基线对照
  - 上述 skill 的 SKILL.md/references 措辞，及 adapter-capabilities.yaml 中 lnkcrm 条目的 evidence 措辞（不涉 status 值变更）

explicitly_not_authorized（维持冻结，需另行签署）:
  - O5-Q5 全部内容：requirement-evaluator 实现级评估解锁（deep 读码）、strategy-brief-generator 浅→深盘点升级、行为层启用——Q4 纳入不自动解锁 Q5
  - capability status 值变更（lnkcrm 各条目保持现值；requirement-evaluator 实现级保持 blocked-by-code 语义至 Q5）
  - resolver / company.yaml / 30-products/** / product-registry.yaml / adapter_status / 门禁测试 / docs 仓

risk_accepted:
  - 27 scope 活跃开发、revision 持续漂移；纳入基线即接受漂移面（基线锚定 scope 集合，不钉具体 revision，沿 O5-lnkcrm-code Q3 口径）
  - requirement-evaluator 实现级评估在 Q5 签署前仍 blocked-by-code

evidence: 设计包 §12.2 Q4（references/adapter-capability-decision-2026-10.md:479-481）；建议包 §3.5 Q4（references/adapter-capability-owner-recommendation-2026-10.md:212）；表单草案 D-O5 follow_up ④（references/adapter-capability-owner-decision-draft-2026-10.md:154）；盘点报告 §3.1 O5-Q4 行（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:56-71）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
override: OPC 可直接覆盖本裁决（含改为「不纳入」）；覆盖时改本记录 + 受影响产物即可。

本记录仅覆盖 O5-Q4；不构成 O5-Q5、O6-O11、删除动作或任何定价事项的批准。
