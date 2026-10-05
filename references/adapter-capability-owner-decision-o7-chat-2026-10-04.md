# Owner Decision —— O7-chat（lnkchat 报价定位）：随 AI 岗位 Skill 打包售卖，不单列

decision_id: O7-chat
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决「打包不单列」（独立报价 / 打包二选一，明确选打包）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: decided
decision: bundled-not-listed（lnkchat 随 AI 岗位 Skill 服务打包售卖，不建独立产品报价，不在报价单单列）

company_ids: [lanlnk]
product_ids: [lnkchat]
consumer_ids: [pricing-generator]

approved_changes:
  - pricing capability lnkchat 条目：status unsupported → not-applicable（权威落地动作，盘点 §3.3 事实面明示）
    + evidence/notes 注记（O7-chat 定判 2026-10-04：打包售卖不单列；打包报价走 AI 岗位 Skill 套餐
    数据/模板——generate_quote.py 的 AI 岗位 Skill 产品线与 materials/references/报价模板_AI岗位Skill_SAAS.md；
    不建 lnkchat 独立报价数据结构）
  - shared 钉线同批：EXPECTED_MATRIX pricing×lnkchat + EXPECTED_DISTRIBUTION（unsupported −1 /
    not-applicable +1），报前后值
  - backlog 盘点报告状态注记（frozen → decided-B / bundled）
  - 执行记录落盘

unchanged:
  - lnkchat 在 company.yaml 产品台账身份（O7-chat 裁的是报价定位，非产品存废）
  - AI 岗位 Skill 套餐现有报价结构（本轮不改动套餐数据本身）
  - resolver / company.yaml / 30-products/** / registry / docs 仓

forbidden_changes:
  - 建立 lnkchat 独立报价基线 / 数据结构（本轮裁决即否决该路线）
  - 从 lnkcre 或其他产品复制价格
  - 写 pricing-basis.yaml（打包路线无独立单价登记对象）
  - 改 AI 岗位 Skill 套餐数据 / 其他产品 capability 条目

revisability: OPC 可改裁「独立报价」路线（届时另落记录，走 LNKCHATBI 式独立数据结构 + 定价流程）

evidence: 盘点报告 §3.3（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:107-123，事实面 :115「打包售卖不单列 → capability 改 not-applicable + evidence 注记」）；表单草案 D-O7-chat（references/adapter-capability-owner-decision-draft-2026-10.md:180-200）；设计包 §3.3.C/§13.1（references/adapter-capability-decision-2026-10.md:212,415,513）；建议包 §3.7 表 :237；pricing×lnkchat 现值 unsupported 实测（pricing adapter-capabilities.yaml :39-40）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。

本记录仅覆盖 O7-chat；不构成 O7-vision / O10-* / O11、删除动作或 lnkreport 定价的批准。
