# Owner Decision —— O11（lnkgateway ontology 处置）：③ 集成层能力不建独立 ontology，not-applicable 收口

decision_id: O11
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决「A」（经权威三选项口径核对：A = ③ 集成层能力不建独立 ontology；
       ① 独立产品 / ② 平台基础能力 ontology 均为"建"路线，非本裁决）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: decided
decision: no-standalone-ontology（lnkgateway 定位集成层能力/平台基础设施，不建独立 ontology；
         prd-gen/competitor 两格 blocked 经 not-applicable 替代路径解除）

company_ids: [lanlnk]
product_ids: [lnkgateway]
consumer_ids: [product-prd-generator, competitor-product-analyzer]

approved_changes:
  - prd-gen / competitor 两份 capability 文件 lnkgateway 条目：blocked → not-applicable
    + evidence/notes（O11-③ 定判 2026-10-04：集成层能力不建独立 ontology，与 O9 暂不独立面客定判同口径；
    blocked 解除的替代路径 = 本 not-applicable 登记）
  - shared schema 钉线同批：EXPECTED_MATRIX 两格 + EXPECTED_DISTRIBUTION（blocked −2 / not-applicable +2），
    报前后值
  - docs 侧登记注记（30-products/lnkgateway/ontology/README.md 与 INDEX.md 的裁决说明行）——
    **具体措辞与单元语义待 skill 取证 lnkwebsite not-applicable 先例机制后按提案执行**（docs 仓由
    orchestrator 会话落盘）；若取证证明该注记会翻转 resolver 的 ontology authority 状态
    （unresolved → not-applicable），则门禁冻结线断言须与 docs 变更原子化联动（另行同批），
    本轮先停止报告
  - backlog 状态注记 + 执行记录

hard_prohibitions（owner 既有明令，维持不变）:
  - 不得从网关代码反推 ontology（语义误判 + 跨域污染闸门）
  - 不得未经批准创建任何一种 ontology（①② 路线本轮明确不启动）

forbidden_changes:
  - 建 30-products/lnkgateway/ontology/ 任何内容本体
  - 改 resolver 生产代码 / company.yaml 结构字段（注释性措辞更新须经取证提案后由 docs 侧执行）
  - prd 层处置（lnkgateway PRD 仍 unresolved，不在本记录范围）
  - 执行 O10-*、删除动作、lnkreport/lnkvision 定价

evidence: 盘点报告 §3.10（references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md:226-242，事实面 :234 三选一、验证要求 :237 裁决③口径）；表单草案 D-O11（references/adapter-capability-owner-decision-draft-2026-10.md:331-351，decision 三选一注释 + 禁令 :346-347）；设计包 §9-O11/§13.2（references/adapter-capability-decision-2026-10.md:419,521,523）；建议包 §3.11；O9 定判（references/adapter-capability-owner-decision-o9-2026-10-04.md）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
override: OPC 可改裁 ①（独立产品 ontology）或 ②（平台基础能力 ontology）——届时走建设路线另落记录。

本记录仅覆盖 O11 裁决③；不构成 O10-*、删除动作或任何定价事项的批准。
