# Owner Decision —— O8（LnkChatBI 标准定价基线）：驳回登记，维持随单赠送/打包策略

decision_id: O8
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话指示「继续走『随单赠送/打包』策略而不设标准价」
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: decided
decision: rejected-registration（驳回标准价登记；lnkchatbi 不设标准价，维持随单赠送/打包）

company_ids: [lanlnk]
product_ids: [lnkchatbi]
consumer_ids: [pricing-generator]

strategy_semantics:
  - 不写 pricing-basis.yaml 任何 lnkchatbi 定价段（费率三键 devkit_rate/devkit_cost_basis/tax_rate_default 零改动）
  - generate_quote.py 的 LNKCHATBI_PRICE_Y1/Y2 默认 0 语义更新：「占位待定价」→「随单赠送策略语义（O8 裁决）」——仅注释/帮助/备注文本，env 覆盖逻辑与默认行为零改动
  - 报价路径：随单赠送 = 默认 0；打包/单独定价 = env 人工输入（现状机制即设计语义，非缺口）

prerequisites_disposition（原 4 前置条件，因驳回不适用）:
  - ① 标准功能清单来源：30-products/lnkchatbi/prd/功能清单.md（canonical 在位）——留档，打包定价时参考
  - ② 标准/定制边界：沿 O7-report G3 已核定读数（标准=existing 项；定制=二开 2000 元/人天）——留档同上
  - ③ 定价生效日期：无对象（不登记）
  - ④ pricing-basis.yaml 写入范围：无对象（不写入）

capability_update:
  - pricing-generator capability lnkchatbi 条目 notes/evidence 更新：授权（O8 已裁决、赠送策略、env 人工输入为设计语义）
  - status partial→implemented：可选——仅当该 yaml 自身语义支持（结构在位 + 默认 0 为设计语义 = 完整报价能力）时做，须同批更新 shared 钉线（EXPECTED_MATRIX + EXPECTED_DISTRIBUTION），报告前后值；无充分依据则保持 partial

forbidden_changes:
  - 套用 lnkchat 或 lnkcre 价格
  - 写 pricing-basis.yaml 任何产品定价段
  - 改 LNKCHATBI_PRICE_Y1/Y2 的 env 读取逻辑或默认值行为（本轮仅注释/文案）
  - 改 LNKCHATBI_DATA 结构、其他产品条目、resolver、company.yaml、30-products/**

evidence: 云泰荔园报价单 LnkChatBI 0/0 战略赠送实证（lanlnk/out/proposals/广州云泰荔园/报价单_MI+LnkChatBI+接口_SAAS_云泰park荔园_20260806.xlsx，「MI+BI+IF报价」Sheet 1.4 行 + 服务说明第 3 条「LnkChatBI、客流接口、车流接口为战略赠送，首年/次年均为 0」）；盘点报告 §3.6（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:158-173）；表单草案 D-O8（references/adapter-capability-owner-decision-draft-2026-10.md:245-266）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
override: OPC 可改回建设路线（届时另落记录，重新走 4 前置条件）。

本记录仅覆盖 O8；不构成 O6/O7-*/O9/O10-*/O11、删除动作或 lnkreport 定价挂起的批准。
