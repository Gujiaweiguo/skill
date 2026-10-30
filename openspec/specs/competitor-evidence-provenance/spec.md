# competitor-evidence-provenance Specification

## Purpose
Defines the provenance contract that keeps competitor claims from being laundered into verified capabilities along the conversion → analysis → capability-model → PRD handoff chain. On the conversion side it binds material-importer PPT handling: a per-slide `text-sparse` review signal judged only from that slide's own extraction and images (advisory, never implying recognition, never auto-triggering OCR), and tri-state detection outcomes that distinguish success-with-findings, success-without-findings, and undetermined, so that a failed detection is never rendered as a clean result. On the analysis side it binds competitor-product-analyzer evidence governance: claim type, evidence state, lineage, and scope stay distinct from confidence; same-origin evidence chains are counted once without deleting ledger entries; unknown independence is not treated as independent, duplicate, verified, or falsified; each source type carries an epistemic ceiling on what it can prove; missing provenance fields fail closed to pending verification instead of being synthesized; evidence-state upgrades record what the new evidence proves and must match its scope; capability summaries, merges, mappings, and PRD handoffs preserve the source claim's evidence state rather than laundering it; and competitor observations do not by themselves authorize or constitute a PRD requirement.

## Requirements

### Requirement: PPT conversion SHALL emit a per-slide text-sparse review signal

material-importer 的 PPT 转换 SHALL 为每张 slide 产出 `text-sparse` 复核信号，判定 SHALL 且仅 SHALL 基于同一 slide 的文本提取结果与该 slide 的图片存在情况，SHALL NOT 基于整份 PPT 的文本总量或其他 slide 的内容。该信号 SHALL 只表示"建议回看原件该页"，SHALL NOT 声称已识别图示、流程、箭头或业务含义，SHALL NOT 自动触发 OCR。

#### Scenario: Image-heavy text-light slide is flagged for review

- **WHEN** 某张 slide 的文本提取结果低于阈值且该 slide 存在图片
- **THEN** 转换产物 SHALL 针对该 slide（含页码）输出 text-sparse 复核提示

#### Scenario: Slides are judged independently of document-wide volume

- **WHEN** 整份 PPT 文本总量偏少但某张 slide 自身文本充足
- **THEN** 该 slide SHALL NOT 被标记 text-sparse；同文档内正常文本页不受整体文本量影响

#### Scenario: Normal sparse pages recorded as false-positive candidates

- **WHEN** 封面、目录或章节分隔页等正常稀疏页被标记 text-sparse
- **THEN** 信号 SHALL 保持"复核提示"语义（不判定内容缺失、不阻断流程），且验收记录 SHALL 观察并记录该类误报表现

#### Scenario: Extraction failure is not reported as text-sparse

- **WHEN** 某张 slide 的文本提取或图片枚举自身失败、无法完成判定
- **THEN** 该 slide SHALL 进入未判定（undetermined）状态，SHALL NOT 被标记为 text-sparse

#### Scenario: Signal does not imply recognition and does not trigger OCR

- **WHEN** 任意 slide 被标记 text-sparse
- **THEN** 系统 SHALL NOT 声称已识别该页图示/流程/业务含义，SHALL NOT 自动运行 OCR；是否 OCR 由人工决定

### Requirement: Conversion detection outcomes SHALL distinguish success-with-findings, success-without-findings, and undetermined

convert_doc.py 对 pptx 的全部检测信号（表格 suspects 与 text-sparse）SHALL 区分三种语义：检测成功且有发现、检测成功且无发现、检测失败无法判断。检测失败 SHALL 显式标记 undetermined（含原因），SHALL NOT 渲染为"无发现"；既有产物行格式 SHALL 保持向后兼容，`pptx_suspects: none` 仅表示检测成功且无发现。

#### Scenario: Detection failure is distinct from a clean result

- **WHEN** 表格守卫 detect 或 slide 扫描子进程失败、返回码非 0 或输出不可解析
- **THEN** 对应信号 SHALL 输出 undetermined 标记（含失败原因），SHALL NOT 输出 `none`

#### Scenario: Existing clean-result marker stays backward compatible

- **WHEN** 检测成功且无任何发现
- **THEN** 产物 SHALL 保持既有 `pptx_suspects: none` 语义不变；新增 text-sparse 信号采用同构的 none / undetermined / 发现 三值

#### Scenario: Advisory failure does not block conversion output

- **WHEN** 检测失败但文本转换与溯源信息本身成功
- **THEN** 转换产物 SHALL 照常写出，失败仅在信号行与 stderr 中显式呈现

### Requirement: Evidence records SHALL keep claim type, evidence state, lineage, and scope distinct from confidence

competitor-product-analyzer 的证据台账 SHALL 在既有 Evidence 对象上区分原始资料主张（claim_type）、验证状态（evidence_state）、来源谱系（lineage）与适用范围（产品/客户/版本/时间/环境），SHALL NOT 将证据维度压缩为单一 confidence 数字；confidence SHALL 继续遵循台账决策树并受 lineage 与适用范围约束。

#### Scenario: Confidence cannot substitute for state or scope

- **WHEN** 任一 evidence 条目判定 confidence
- **THEN** 其 claim_type、evidence_state、lineage 与适用范围 SHALL 保持独立字段/记录，SHALL NOT 被置信度取值隐含或覆盖

### Requirement: Same-origin evidence chains SHALL be counted once

Evidence 对象 SHALL 支持 source lineage：记录原始来源与锚点、复制/派生关系（derived_from）、以及来源的产品/客户/版本/时间与验证范围。同一原件派生的原文、转换文本、OCR 结果、能力模型条目、分析摘要与交接内容 SHALL 归入同一来源链，在独立性判定与互证计数中只计一次，SHALL NOT 当作多份独立证据重复计数。

#### Scenario: One PPT claim counts once across its derivations

- **WHEN** 同一 PPT 主张同时出现在转换文本、能力模型条目、分析结果与交接包中
- **THEN** 这些条目 SHALL 折叠为同一来源链，互证计数仍只计一个原始来源

#### Scenario: Chain counting does not delete ledger entries

- **WHEN** 同链条目按一条来源计数
- **THEN** 各条目 SHALL 保留各自 evidence_id 与原始锚点，仅计数语义合并，SHALL NOT 静默删除条目

### Requirement: Unknown independence SHALL NOT be treated as independent, duplicate, verified, or falsified

来源独立性无法判定时 SHALL 标记 unknown；unknown SHALL NOT 等同于独立（不得参与互证升级），SHALL NOT 等同于同链重复（不得据此合并或丢弃条目），SHALL NOT 等同于已验证或已证伪。

#### Scenario: Independence unknown blocks confidence elevation

- **WHEN** 两条证据描述同一能力但其独立性无法判定
- **THEN** 系统 SHALL NOT 因二者并存提升 confidence，SHALL NOT 将任一条按重复丢弃，SHALL 保持待核实语义

### Requirement: Evidence-state upgrades SHALL record what the new evidence proves and match its scope

证据状态或置信度升级 SHALL 满足：新增证据独立支持同一主张，且其产品、客户、版本、时间与验证范围与目标结论匹配。升级 SHALL 记录新增证据、升级理由及适用范围（沿用既有 pending-items 机制），SHALL NOT 静默升级或自动升级。

#### Scenario: Out-of-scope corroboration does not upgrade

- **WHEN** 新增证据与目标主张的产品版本、客户范围或验证范围不匹配
- **THEN** 系统 SHALL NOT 升级原证据状态或置信度，SHALL 记录不匹配原因待人工裁决

#### Scenario: Qualified upgrade leaves a traceable record

- **WHEN** 满足匹配条件的新证据支持升级
- **THEN** 升级记录 SHALL 含新增证据 ID、升级理由、适用范围，且可追溯到受影响的原 evidence ID

### Requirement: Source types SHALL carry epistemic ceilings on what they prove

证据台账 SHALL 按来源类型约束结论边界：操作手册存在只证明"文档记载"，SHALL NOT 自动证明功能已部署或普遍交付；Demo 可操作只证明被观察环境（URL/账号角色/时间）的行为，SHALL NOT 推断生产部署或所有客户；数据库/SQL 线索只证明数据结构存在，SHALL NOT 自动证明完整业务能力；PPT 方案描述/厂商宣称只支持"方案提出/厂商声称"，SHALL NOT 单独证明标准产品已交付；客户蓝图 SHALL NOT 自动泛化为标准产品能力。

#### Scenario: Manual alone stays at documented level

- **WHEN** 某能力仅有操作手册记载
- **THEN** 结论 SHALL 表达"文档记载"层级（可与其他独立来源相互印证），SHALL NOT 表达或升级为已部署/普遍交付

#### Scenario: Demo observation is scoped to the observed environment

- **WHEN** 某能力仅来自 demo 运行时观察
- **THEN** 结论 SHALL 限定被观察环境（URL、账号角色、探测时间），SHALL NOT 推断生产部署或所有客户

#### Scenario: Proposal claims remain vendor claims

- **WHEN** 某能力仅有 PPT 方案描述或厂商宣称
- **THEN** 该主张 SHALL 保持"方案提出/厂商声称"语义与弱证据置信上限，SHALL NOT 被表述为已交付的标准能力

#### Scenario: Customer blueprint is not generalized

- **WHEN** 证据来自特定客户蓝图
- **THEN** 适用范围 SHALL 保留客户限定，SHALL NOT 自动泛化为标准产品能力或提升置信度

#### Scenario: Data-dictionary hints do not prove full capability

- **WHEN** 仅有数据字典或 SQL 结构线索
- **THEN** 结论 SHALL 限定于数据结构层面，SHALL NOT 自动断言完整业务流程或业务能力

### Requirement: Missing provenance fields SHALL fail closed to pending verification

Evidence 条目缺少 SHA、页码/slide 锚点、evidence_id、状态、来源类型、来源版本或独立性信息时，SHALL 进入待核实/未知/弱解释处理（复用既有枚举：claim_type=假设、confidence 降级或共享契约 unassessed、强制进 pending-items），SHALL NOT 静默补齐缺失信息，SHALL NOT 自动设为 verified。

#### Scenario: Missing anchor or SHA fails closed

- **WHEN** 某证据条目缺少页码/slide 锚点或源 SHA
- **THEN** 该条目 SHALL 被标待核实并进 pending-items，SHALL NOT 获得更高置信度或被当作已验证

#### Scenario: Missing identifiers are not synthesized

- **WHEN** 交接或导出时发现 evidence_id / trace_id 缺失或断链
- **THEN** 系统 SHALL NOT 伪造或静默补齐 ID，对应观察 SHALL 显式标待核实

### Requirement: Capability summaries and PRD handoffs SHALL preserve source claim evidence state

capability 摘要、归并与目标产品映射 SHALL 可回溯到原始主张与来源证据，SHALL NOT 改变来源主张的证据状态或置信度。交接包中每项竞品观察 SHALL 保留 evidence_id、trace_id、原始来源锚点、证据状态与来源谱系关联；证据缺失或断链 SHALL 显式标待核实。竞品分析结果 SHALL NOT 构成 PRD 需求授权，是否采纳仍遵循既有产品决策流程。

#### Scenario: Summary, merge, and mapping cannot launder evidence state

- **WHEN** 能力摘要、多证据归并或 standard_term 目标产品映射发生
- **THEN** 各来源主张的原 evidence_state 与 confidence SHALL 原值保留，SHALL NOT 因归并或映射而升级

#### Scenario: Handoff observation keeps full provenance

- **WHEN** 竞品观察导出到共享 source-reference 或 PRD 交接包
- **THEN** 每条观察 SHALL 携带 evidence_id、trace_id、原始锚点、证据状态与谱系关联；缺失即显式待核实

#### Scenario: PRD consumption does not auto-verify observations

- **WHEN** product-prd-generator 消费竞品观察
- **THEN** 观察 SHALL 保持其证据状态，SHALL NOT 静默升级为已验证事实；采纳与否由既有 owner decision 流程决定
