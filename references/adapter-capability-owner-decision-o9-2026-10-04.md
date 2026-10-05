# Owner Decision —— O9（lnkgateway 产品定位）：暂不独立面客，预改判转定判

decision_id: O9
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决「B」（维持不面客，确认预判；经三态口径澄清后明确选边）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: decided
decision: not-independently-customer-facing（暂不独立面客——暂定平台基础设施 / 集成网关 / 内部能力；预改判转定判，可复议）

company_ids: [lanlnk]
product_ids: [lnkgateway]
consumer_ids: [pricing-generator, company-intro-generator]

approved_changes:
  - pricing-generator / company-intro-generator 两份 capability 文件 lnkgateway 条目：
    evidence 补正式裁定依据（O9 定判 2026-10-04，替代「预改判」状态；现值 not-applicable 保持不变）
  - backlog 盘点报告状态注记（frozen → decided-B / 定判）
  - 执行记录落盘

revisability:
  - 本裁决为「暂不」而非「永不」——OPC 可随时改裁 A 路线（未来面客重建矩阵条目），
    届时回改两格 not-applicable 值 + 钉线同批 + 重建叙事/报价输入清单，另落记录

unchanged（本裁决不触动的相邻事实）:
  - lnkgateway 在 company.yaml 产品台账的登记身份（产品名单不变——O9 裁的是「是否独立面客」，非「是否产品」）
  - O11 冻结线：lnkgateway ontology=unresolved、ontology_entry=null、禁止跨产品 fallback（门禁钉死，独立裁决项）
  - D-O9 禁令继续有效：ontology/PRD unresolved 期间不得建立 lnkgateway 独立报价 / 竞品能力 / 公司介绍基线

forbidden_changes:
  - 改动两份 capability 文件 lnkgateway 条目的 status 值（not-applicable 保持）
  - 改 registry 数据区、resolver、company.yaml、30-products/**、shared 生产代码与门禁
  - 建立 lnkgateway 任何面客基线（报价/竞品/公司介绍）
  - 执行 O7-vision / O10-* / O11、删除动作、lnkreport 定价

evidence: 盘点报告 §3.7（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:175-190）；表单草案 D-O9（references/adapter-capability-owner-decision-draft-2026-10.md:268-287，scope :275「是否永不独立面客」）；建议包 §3.9（references/adapter-capability-owner-recommendation-2026-10.md:255-265，:257「暂定定位」）；设计包 §13.2（references/adapter-capability-decision-2026-10.md:517-524）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
override: OPC 可改裁 A（未来面客重建）或 C（永不面客落死）；届时另落记录。

本记录仅覆盖 O9；不构成 O7-vision / O10-* / O11、删除动作或 lnkreport 定价的批准。
