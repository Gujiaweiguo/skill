# Owner Decision —— O10（report + vision）：叙事资产建设启动，skill 起草 / OPC 批注制

decision_id: O10（覆盖 D-O10-report 与 D-O10-vision 两个表单块）
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决：启动 + 选定工作方式「让 skill 从 PRD 起草，OPC 只改批注」
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: approved
decision: start-with-draft-review（两子项均启动；草稿由 skill 基于 canonical PRD/功能清单起草，
         OPC 批注定稿后才入库——两阶段制）

company_ids: [lanlnk]
product_ids: [lnkreport, lnkvision]
consumer_ids: [company-intro-generator]

stage_1_draft（本轮）:
  - skill 依据 30-products/lnkreport/prd/ 与 30-products/lnkvision/prd/ canonical 证据起草两份叙事文档
    （一句话定位 / 目标客户与场景 / 核心能力卖点（每条挂 文件:行 出处）/ 差异化（lnkreport 用竞品对比
    canonical，vision 用其 PRD）/ 客户价值 / 与其他产品边界）；
  - O10-vision 的前置定位（目标客户 / 与 lnkreport 边界）在草稿中以「定位假设（待 OPC 批注）」
    章节呈现，由 PRD 证据推导，不虚构；
  - 草稿落 skill 仓（生成区，不直接入 docs materials）；
  - 所有推断性表述集中列入「待 OPC 批注清单」；
  - capability：company-intro×lnkreport / ×lnkvision unsupported → onboarding（草稿阶段语义；
    schema 钉线同批，报前后值）。

stage_2_promote（OPC 批注后另行执行）:
  - OPC 批注定稿 → orchestrator 走 docs 侧流程入 materials/03-products/（material-importer
    validate）→ capability onboarding → implemented（以入库事实为 evidence）。

forbidden_changes:
  - 用其他产品叙事顶替（表单草案 :304 禁令）
  - 未经 OPC 批注直接写入 docs 仓 materials（两阶段制的意义所在）
  - capability 直接升 implemented（入库前禁止）
  - 改 resolver / shared / company.yaml / 30-products/**（只读）/ docs 仓任何文件
  - git add -A、提交、推送

evidence: 盘点报告 §3.8/§3.9（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:192-225）；表单草案 D-O10-report/D-O10-vision（references/adapter-capability-owner-decision-draft-2026-10.md:289-329）；设计包 §3.3.E（:244-245「materials grep 无专属叙事命中」）；建议包 §3.10（:271-272「可启动」/「先确认定位」）；capability 现值 unsupported 实测（company-intro yaml :51-66）；O7-vision 面客定判（定位依据已就绪）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。

本记录仅覆盖 O10 两子项的 Stage-1；Stage-2 入库与 capability implemented 升级待 OPC 批注后另批。
