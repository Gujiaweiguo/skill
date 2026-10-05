# Owner Decision —— D2（adapter_status 字段退役 / O4 步骤⑤）：批准删除

decision_id: D2-adapter-status-retire（O4 步骤⑤：字段级删除；O4 记录明文要求独立 owner 批准 + 门禁测试同 change 更新）
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决「全做」（删除批两项均批）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: approved
decision: delete-field（删除 ProductContext.adapter_status 迁移期兼容字段，O4 五步收尾）

company_ids: [lanlnk]
product_ids: [全部 8 产品——字段级退役]
consumer_ids: [shared/product_context（字段宿主）；门禁测试（同批改写）]

evidence_basis:
  - O4 门禁（test_adapter_status_migration_gate.py）长期实证：白名单内零业务消费；
    8 产品 resolver 输出恒为默认回落 unsupported，无信息量
  - per-skill adapter capability 权威源 = 各 skill 私有 adapter-capabilities.yaml（O1/O2 方案 B，已全量落库）
  - O4 记录步骤⑤明文：「Removing the field requires an independent owner approval (O4 step 5)
    plus a same-change update to that gate test」——本记录即该批准，门禁改写为同批强制项

approved_changes:
  - shared/product_context：models/resolver 移除 adapter_status 字段与回落逻辑；README 对应段落改写
    （O4 垫片语义 → 已退役登记，引本记录）
  - 门禁测试 test_adapter_status_migration_gate.py 同批改写：从「钉字段语义 + 消费方白名单」改为
    「断言字段已不存在 + 全仓零 adapter_status 消费」；authority 三条冻结线断言保持不变（lnkcrm complete /
    lnkgateway unresolved+entry=null / lnkwebsite prd-only+not-applicable）
  - registry 侧对象：若 D1 已先行删除 product-registry.yaml 则自然消失；若仍在，删除其数据区
    8 个产品的 adapter_status 行（本记录专项授权数据区动刀）
  - 受影响测试基线同步更新（如 as_dict 形状断言、resolver 输出断言）；执行记录落盘

forbidden_changes:
  - 动 authority 冻结线语义（三条冻结线断言必须原样保绿）
  - 改 capability 文件（六份 adapter-capabilities.yaml 是权威源，非迁移垫片）
  - 改 company.yaml / 30-products/** / docs 仓
  - git add -A、提交、推送

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。

本记录仅覆盖 D2；与 D1 相互独立、顺序执行（建议 D1 先行）。
