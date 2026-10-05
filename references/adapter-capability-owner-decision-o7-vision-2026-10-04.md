# Owner Decision —— O7-vision（lnkvision 报价定位）：面客，启动基线建设（结构先行，定价挂起）

decision_id: O7-vision
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决「面客」（独立产品对外，启动报价基线建设）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: decided
decision: customer-facing（lnkvision 为独立面客产品；启动 pricing 报价基线建设——结构先行、金额留空、定价数值挂起，完全复用 O7-report 已核定模式）

company_ids: [lanlnk]
product_ids: [lnkvision]
consumer_ids: [pricing-generator]

approved_changes:
  - pricing capability lnkvision 条目：status unsupported → onboarding（结构建设启动；定价数值未登记前不升 implemented）
    + evidence/notes（O7-vision 面客定判 2026-10-04；结构沿 LNKREPORT_DATA 模式；金额留空待定价）
  - shared 钉线同批：EXPECTED_MATRIX pricing×lnkvision + EXPECTED_DISTRIBUTION（unsupported −1 / onboarding +1），报前后值
  - generate_quote.py：新增 LNKVISION_DATA（对齐 LNKREPORT_DATA 模式：四段结构、八列行结构、
    金额一律留空/None + 「待定价」标记、RATIFIED_ZEROS 白名单外零值、无数值时显式拒绝）
    + CLI 接线 + 配套最小测试（结构完整性 / 金额纪律 / 拒绝行为 / capability 条目）
  - 模块分组：依据 30-products/lnkvision/prd/功能清单.md（canonical）提出报价模块分组草案，
    落执行记录待 OPC 复核（沿 O7-report G4 模式）
  - backlog 盘点报告状态注记（frozen → decided / customer-facing，基线建设中）
  - 执行记录落盘

deferred（挂起，同 lnkreport 模式）:
  - lnkvision 定价数值（待 OPC 提供；提供前金额一律留空，不编造）
  - pricing-basis.yaml 登记（docs 仓；金额留空无登记对象）

narrative_linkage:
  - 本「面客」定判同时作为 O10-vision（叙事资产）的定位依据——lnkvision 叙事面按面客口径建设；
    O10-vision 的启动与素材建设仍为独立签署项，本记录不构成其批准

forbidden_changes:
  - 填任何具体单价/金额（pricing-basis.yaml 费率引用除外）；从 lnkcre/lnkchat/其他产品复制价格
  - 建 lnkchat 式「打包不单列」登记（本裁决已明确独立面客路线）
  - 改 resolver / company.yaml / 30-products/**（只读）/ registry / shared 生产代码（钉线除外）/ docs 仓
  - 执行 O10-report / O10-vision / O11、删除动作、lnkreport 定价

evidence: 盘点报告 §3.5（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:141-157，事实面 :149「落地路径与 O7-chat 同构：建基线 → pricing 数据+登记+capability 升级」）；表单草案 D-O7-vision（references/adapter-capability-owner-decision-draft-2026-10.md:223-243）；设计包 §3.3.C lnkvision 行（references/adapter-capability-decision-2026-10.md:215）；建议包 §3.7 表 :239 + §1 产品三层表 :51（lnkvision complete/complete/complete fa5050f4）；lnkreport 先例（O7-report Phase 1-3 + 3fcb00a/d9c5352 已落库模式）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
override: OPC 可改裁「不面客」（届时 capability 回改 not-applicable + 拆除独立结构，另落记录）。

本记录仅覆盖 O7-vision；不构成 O10-* / O11、删除动作或 lnkreport 定价的批准。
