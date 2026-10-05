# Owner Decision —— D1（product-registry.yaml 退役）：批准删除

decision_id: D1-registry-retire（D1 为会话标签；权威动作 = 「删除 skill 侧 product-registry.yaml」独立 owner 批准动作，O3 记录 follow_up 登记）
decision_date: 2026-10-04
owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）
origin: OPC 会话裁决「全做」（删除批两项均批）
recorded_by: orchestrator 按 OPC 明确指示落盘（transcription）
status: approved
decision: delete（删除 skills/business/product-prd-generator/references/product-registry.yaml，迁移期兼容使命终结）

company_ids: [lanlnk]
product_ids: [全部 8 产品——文件级退役，非产品级动作]
consumer_ids: [product-prd-generator]

evidence_basis（零消费方证据链，全部已落库）:
  - 盘点报告交叉核对：生产代码零 yaml.safe_load 该文件；resolver 明确不读（shared README 明文）
  - B1-B7/R1-R4 全部解除并落库（b171b28）；B4 已撤销双源同步义务；规则 10(c) 定位为迁移期兼容元数据/历史镜像
  - 产品与路径事实权威源 = company.yaml + shared.product_context resolver；注册入口 = docs 仓 onboard.sh

approved_changes:
  - 删除该 YAML 文件（含全部注释规则段与数据区快照）
  - 清扫 skill 仓残留引用（仅 prose/测试文档级）：_paths.py 注释、SKILL.md/references 提及、
    check_docs_consistency.sh 若有引用、存在性/内容断言测试（如有）——逐处 grep 实证后最小修改
  - 迁移审计追加收官注记：B 系列审计闭卷（registry 物理退役，2026-10-04）
  - 执行记录落盘

forbidden_changes:
  - 删除/修改 docs 仓任何文件（含 lanlnk 侧 product-registry-feedback.yaml 历史证据——不删）
  - 改 resolver / shared 包 / company.yaml / 30-products/** / capability 文件
  - 删除 adapter_status 字段（那是 D2，独立执行）
  - git add -A、提交、推送（OPC 另安排提交批）

OWNER SIGN-OFF: RECORDED (OPC)
授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署。
身份依据: 本会话用户自述「我是 opc，我授权了就可以执行，不用别人授权」。
irreversibility_note: 删除动作经 git 可恢复（历史提交保留全部版本）；本轮不推送。

本记录仅覆盖 D1；不构成 D2 或任何其他项的批准。
