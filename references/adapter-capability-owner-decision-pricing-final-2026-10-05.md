# Owner Decision —— lnkreport / lnkvision 定价终裁：不单独售卖（无独立标准价）

decision_id: PRICING-FINAL（终裁 O7-report 与 O7-vision 两决策记录的 deferred「定价数值」项 + backlog 定价挂起项）
decision_date: 2026-10-05
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决「不单独售卖」（对「定价填数」待办的改判关闭）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: decided
decision: not-sold-independently（两产品均不单独售卖、不设独立标准价；对外输出仅随组合/打包方案出现）

company_ids: [lanlnk]
product_ids: [lnkreport, lnkvision]
consumer_ids: [pricing-generator]

resolves（本记录终结的挂起项）:
  - O7-report 决策记录 deferred「定价具体数值」→ 终结为「不设独立定价」
  - O7-vision 决策记录 deferred「lnkvision 定价数值」→ 同上
  - backlog「lnkreport / lnkvision 定价填数」待办 → 关闭（改判）

approved_changes:
  - pricing capability 两格：lnkreport / lnkvision onboarding → not-applicable
    + evidence/notes（不单独售卖终裁 2026-10-05；沿 O7-chat「打包售卖不单列 → not-applicable」
    权威先例；LNKREPORT_DATA / LNKVISION_DATA 结构保留——其无价拒单行为即本策略的机械执行：
    单产品与组合报价均写盘前拒绝）
  - shared schema 钉线同批：EXPECTED_MATRIX 两格 + EXPECTED_DISTRIBUTION（读现值调整，报前后值）
  - generate_quote.py / 相关测试中「待定价」措辞的注释性更新（可选，仅注释/帮助/备注文本，
    行为零改动）：「待定价」→「不单独售卖（终裁 2026-10-05），无独立标准价」
  - backlog 终态注记（定价挂起项 → decided-not-sold-independently / 关闭）+ 执行记录落盘

bundle_semantics:
  - 组合/打包场景：两产品以并入或赠送姿态出现在组合方案中，金额由商务在主产品报价内处理；
    未来若需组合内独立行项定价（env 人工输入机制），另行授权（沿 LnkChatBI LNKCHATBI_PRICE 先例）

forbidden_changes:
  - 填任何独立单价/金额（Y1/Y2 永不登记）；写 pricing-basis.yaml；
  - 改 LNKREPORT_DATA / LNKVISION_DATA 结构、拒单行为、RATIFIED_ZEROS 白名单（注释性更新除外）；
  - 从 lnkcre/lnkchat/其他产品复制价格；
  - 改 resolver / shared 生产代码（钉线除外）/ company.yaml / 30-products/** / docs 仓；
  - git add -A、提交、推送（随后统一提交批 + 终推）

evidence: O7-chat 权威先例（盘点 §3.3 事实面 :115「打包售卖不单列 → capability 改 not-applicable + evidence 注记」）；O7-report 决策记录 deferred 段；O7-vision 决策记录 deferred 段；LNKREPORT_DATA/LNKVISION_DATA 拒单行为实测（两产品单卖与组合均 sys.exit 拒绝，O7-report Phase 3 / O7-vision 执行记录）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
override: OPC 可改裁独立售卖路线（届时提供 Y1/Y2 数值 + 走 O7-report Phase 2/3 登记流程，另落记录）。

本记录仅覆盖两产品的定价终裁；不构成其他事项批准。
