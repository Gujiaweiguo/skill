# Owner Decision —— O7-report（lnkreport 功能清单确认 + 报价基线口径）

decision_id: O7-report
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: 本会话 OPC 明确指示；非 agent 推断
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: approved
approved_phase: phase-1 + phase-2-caliber + phase-3-landing

scope: lnkreport 独立产品功能与报价基线建设 —— Phase 1「功能清单确认」+ Phase 2「报价基线口径（结构）」
company_ids: [lanlnk]
product_ids: [lnkreport]
consumer_ids: [pricing-generator]

decision: approved-phase1-3

approved_changes:
  - 只读核对 /opt/code/docs/lanlnk/30-products/lnkreport/prd/ 现有 canonical 功能清单的完整性与可报价性
  - 产出缺口清单与 Phase 2 前置需求（不补写、不定价）
  - 允许新增 1 个状态报告文件 references/adapter-capability-owner-decision-o7-report-phase1-report-2026-10-04.md
  - Phase 2：按既有标准报价口径（现有报价模板结构 + config/pricing/pricing-basis.yaml 费率）建设 lnkreport 报价基线结构；不复制其他产品具体单价，不编造具体数值
  - Phase 3：pricing-generator LNKREPORT_DATA 结构升级（G4 已核定模块分组；金额一律留空/待定价标记）+ 配套 pytest
  - Phase 3：pricing-generator references/adapter-capabilities.yaml lnkreport 条目 unsupported → onboarding（evidence + verified_at + 校验测试同批原子化）
  - Phase 3 补充（守卫对齐）：shared/product_context/tests/test_adapter_capabilities_schema.py 同批更新——pricing lnkreport 钉值 unsupported → onboarding（:113 附近）+ EXPECTED_DISTRIBUTION onboarding 5→6 / unsupported 6→5（:153 附近）。依据：该测试自身契约要求 capability 变更同 commit 更新钉线；本补充不改变 capability 语义，仅解除与已批准 Phase 3 变更的矛盾

deferred:
  - 定价具体数值（待 OPC 提供；提供前 LNKREPORT_DATA 金额一律留空/待定价）
  - pricing-basis.yaml：本轮无需改动（费率已在仓为唯一权威源；金额留空无登记对象），未来填数值时另开授权
  - G5-G7 登记性修复（30-products/**，docs 仓）—— 需 docs 侧独立步骤

pricing_caliber:
  decision: OPC 指示「定价数值口径按照以前的就行」（2026-10-04）
  resolved: 沿用既有标准报价口径 = 现有报价模板结构（如 materials/references/报价模板_SAAS.md）+ config/pricing/pricing-basis.yaml 费率口径
  constraint: 仍不得复制 lnkcre 或其他产品的具体单价数值；无固定数值来源时，金额按模板惯例（销售/标准填写）留待确认，不编造
  verification: 见 盘点报告 §3.4（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:124-139）

phase2_decisions:
  basis: OPC 指示「按以前的就行」→ 沿用既有产品（MI/CRM）标准口径，逐项落实 Phase 1 报告 G1-G4
  G1_version_split: SAAS + 私有化（与 MI/CRM 一致）
  G2_metering: 按模块年租用 + 实施费 + 售后（对齐 SAAS 模板；不引入按报表数/数据量计量）
  G3_std_custom_boundary: 标准 = 功能清单内 existing 126 项；定制 = partial/not-do 项 + 新需求（走二开 2000 元/人天）
  G4_module_grouping: 由 skill 依据 30-products/lnkreport/prd/功能清单.md 6 节提出报价模块分组草案，待 OPC 复核
  note: 上述为 OPC「按以前的」指示的实施读数；如与本意不符，OPC 可直接覆盖，无需重新授权

phase3_ratification:
  date: 2026-10-04
  basis: OPC 指示「继续」+「如需授权我授权」
  G4_module_grouping: 按 Phase 2 报告 §3 草案默认核定（1.1/1.2/1.3 必选；1.4/1.5/1.6 可选；2.x 可选对接）
  review_items: 报告 §5 八项复核全部按草案默认（实施人天留空；售后首年赠送按模板惯例；2.1 话术边界标待定）
  override: OPC 保留逐项覆盖权；覆盖时改本记录 + 受影响产物即可，无需重新授权

forbidden_changes:
  - 从 lnkcre 或其他产品复制价格
  - 修改 30-products/** 任何文件（只读）
  - 修改 product-registry.yaml、adapter_status、resolver、_paths.py、审计/决策记录（例外：Phase 3 明确授权的 pricing-generator tests、其 capability 文件 lnkreport 条目、以及「Phase 3 补充」明确授权的 shared 守卫测试两处钉线）

schema_version: 1
evidence: 设计包 §9-O7 / §3.3.C（references/adapter-capability-decision-2026-10.md:214,415）；建议包 §3.7（references/adapter-capability-owner-recommendation-2026-10.md:238）；表单草案 D-O7-report（references/adapter-capability-owner-decision-draft-2026-10.md:202-221）；盘点报告 §3.4（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:124-139）
follow_up: 功能清单 → 定价 → pricing-basis.yaml 登记（各步 owner 确认）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户 2026-10-04 自述「我是 opc，我授权了就可以执行，不用别人授权」。

本记录覆盖 O7-report Phase 1-3（功能清单确认 + 报价基线口径 + skill 侧落地）；不构成具体定价数值、
pricing-basis.yaml 变更、G5-G7 修复或任何其他 O5/O6/O7/O8-O11 项的批准。
