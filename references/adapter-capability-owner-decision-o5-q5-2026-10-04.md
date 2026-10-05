# Owner Decision —— O5-Q5（code authority 晋升后的验证 adapter 集启动 / 实现级评估解锁）

decision_id: O5-Q5（文档未分配独立子编号；本 ID 为盘点报告 §3.1 拆列口径，不构成编号定义）
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: O5-Q4 收口后按既定顺序推进（orchestrator 建议 + OPC 索要下一步提示词）
recorded_by: orchestrator 按 OPC 治理流程落盘（transcription；OPC 可覆盖）
status: approved
decision: unlock（最小验证集启动：实现级评估解锁）

scope: lnkcrm code authority=complete（O5-lnkcrm-code）+ scope 基线纳入（O5-Q4）之后，三个业务 skill 的行为层启用
company_ids: [lanlnk]
product_ids: [lnkcrm]
consumer_ids: [requirement-evaluator, strategy-brief-generator, product-prd-generator]

unlocked:
  - requirement-evaluator：实现级评估解锁——允许用 company.yaml 配置的 code root（/opt/code/lnkcrm）做实现级代码验证；解除「不得自动用观察 checkout」限制（设计包 :494 冻结线，该限制属 present-unconfirmed 时代语义，configured 即 authority）；lnkcrm 按 lnkcre 同等实现级评估口径处理；功能清单 implementation_status unknown 语义可开始收敛（承诺级→实现级）
  - strategy-brief-generator：lnkcrm 盘点深度标注 unconfirmed → 深盘点可用
  - product-prd-generator：--code-root 显式确认收敛为 configured（事实已随 O5-lnkcrm-code 自然达成，本轮为 skill 层措辞/验证行为登记）
  - O5-Q4 落地的「待 O5-Q5」边界注记同步更新为已解锁（预期接续，非重写）

anti_drift_constraints:
  - 实现级评估结论必须记录评估时点 revision（git -C /opt/code/lnkcrm rev-parse HEAD）并注明漂移警示（活跃开发会让结论过时）
  - 实现级评估适用面 = code authority complete 的产品（当前 lnkcre、lnkcrm）；其余产品维持原禁令

capability_files:
  - lnkcrm 条目 evidence/notes 更新：授权
  - status 值变更：允许但须同批更新 shared 钉线（pin + EXPECTED_DISTRIBUTION），报告前后值供 OPC 复核；无充分语义依据则保持现值

explicitly_not_authorized（维持冻结）:
  - O6-O11 全部、registry/adapter_status 删除动作、O4⑤字段删除、lnkreport 定价数值（挂起）
  - resolver / company.yaml / 30-products/** / product-registry.yaml / adapter_status / shared 生产代码（钉线测试除外）
  - Q4 已落地 grep 面/判定输入/回写对照内容的语义重写（仅允许边界注记接续更新）

risk_accepted:
  - lnkcrm 活跃开发 revision 持续漂移，实现级评估结论会快速过时（缓解：结论钉 revision + 漂移警示）

evidence: 设计包 §12.2 Q5 + 建议最小集（references/adapter-capability-decision-2026-10.md:482-485）、§12.3 冻结线（:488-500，含 :494 观察禁令）；建议包 §3.5 五问（references/adapter-capability-owner-recommendation-2026-10.md:213-215）；表单草案 D-O5 follow_up ⑤（references/adapter-capability-owner-decision-draft-2026-10.md:154）；盘点报告 §3.1 O5-Q5 行（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:73-85）；O5-Q4 执行记录（边界注记现状）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
override: OPC 可直接覆盖本裁决；覆盖时改本记录 + 受影响产物即可。

本记录仅覆盖 O5-Q5；不构成 O6-O11、删除动作、定价事项或 Q4 已落地内容重写的批准。
