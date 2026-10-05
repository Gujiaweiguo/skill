# Owner Decision —— O6（正祥 CRM 定价归属）：不追认，登记为 historical evidence

decision_id: O6
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决「A」（不追认为正式基线，仅登记 customer-specific / historical pricing evidence）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: decided
decision: register-as-historical-evidence（方案 A；不追认 lnkcrm 正式报价基线）

company_ids: [lanlnk]
product_ids: [lnkcrm]
consumer_ids: [pricing-generator]

approved_changes:
  - generate_quote.py CRM_DATA（:280 附近）归属注释登记：正祥单一客户历史成交证据（materials/03-products/CRM功能清单.xlsx 受管副本的结构化数据），可作参考 / 客户特定报价生成依据，不是 lnkcrm 标准价——仅注释，数据/结构/数值零改动
  - pricing capability lnkcrm 条目 evidence/notes 更新：「历史 CRM 报价无主使用」→ 已登记归属（customer-specific / historical evidence，2026-10-04）；正式基线未建，未来若建走 B 路线六要素另案
  - backlog 盘点报告状态注记（frozen → decided-A / evidence-registered）
  - 执行记录落盘

capability_status:
  - pricing×lnkcrm 保持 partial（结构在位 + historical evidence 已登记；正式标准定价未建，partial 语义准确，不升级）

forbidden_changes:
  - 将正祥定价直接当作 lnkcrm 标准定价使用或标注
  - 从 lnkcre 复制价格顶替
  - 写 docs 仓任何文件（pricing-basis.yaml 不涉及；冒烟输出不得落入 docs 仓）
  - CRM_DATA 数据结构 / 数值 / env 逻辑 / 生成行为改动（本轮仅注释与登记措辞）

route_B_prerequisites（转正式基线的六要素，留档另案）:
  适用产品 / 适用版本 / 价格有效期 / 标准与定制边界 / owner / 对外性
  （表单草案 D-O6 follow_up，references/adapter-capability-owner-decision-draft-2026-10.md:176-177）

evidence: 盘点报告 §3.2（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:90-105）；表单草案 D-O6（references/adapter-capability-owner-decision-draft-2026-10.md:157-178）；建议包 §3.6（references/adapter-capability-owner-recommendation-2026-10.md:219-229）；设计包 §9-O6 / §3.3.C lnkcrm 行（references/adapter-capability-decision-2026-10.md:414,211,537）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
override: OPC 可改裁 B（追认正式基线，须答六要素）或撤销登记；届时另落记录。

本记录仅覆盖 O6；不构成 O7-*/O9/O10-*/O11、删除动作、lnkreport 定价或 B 路线的批准。
