# 冻结 backlog 决策包：O5 其余子项与 O6-O11 只读盘点（2026-10-04）

```text
STATUS: INVENTORY-ONLY（只读盘点报告，非批准记录）
OWNER SIGN-OFF: NOT RECORDED
SCOPE: O5 其余子项 + O6/O7-chat/O7-report/O7-vision/O8/O9/O10-report/O10-vision/O11 盘点；
       含 D1/D2 零消费方只读核对（不执行）。不含任何文件修改、不含 D1/D2 执行。
```

> **记录性质（必读）**：本文件是**只读盘点报告**，由盘点会话落盘。授权来源为本轮
> 用户会话明确批准的「O5/O6-O11 只读盘点（ONLY-READ-INVENTORY）」。它**不是**、
> 也**不得被引用为**任何 owner 批准记录。本报告的产出**不构成** D1、D2、O5 任何
> 子项、O6-O11 任何一项的批准；全部上述动作维持冻结，各自需独立 owner 签署。
> 与 B1-B7 / lnkcrm-freeze-reconcile / R1-R4 执行记录族同口径：OWNER SIGN-OFF:
> NOT RECORDED。

---

## 1. 授权与盘点范围

- **授权来源**：本轮用户会话明确批准的只读盘点授权（含逐条允许/禁止边界、盘点
  字段、交叉核对清单、验证与最终报告格式）。
- **OWNER SIGN-OFF: NOT RECORDED**：不存在独立签署记录。盘点结果用于向 owner
  申请逐项决策。
- **盘点对象**：O5 其余子项（O5 中 lnkcrm-code 已完成，其余未界定）、O6、O7-chat、
  O7-report、O7-vision、O8、O9、O10-report、O10-vision、O11。
- **零修改承诺的验证**：见 §6（git status 实证，除本文件新增外与执行前一致）。

## 2. 与文档编号/命名的差异记录（授权 §二要求，以文档为准）

| # | 授权 prompt 中的编号/命名 | 文档中的实际表述 | 差异处理 |
|---|---|---|---|
| 1 | **D1**（删除 product-registry.yaml） | 全部决策/审计文档中**无「D1」编号**。对应动作在文档中表述为「删除 registry = 独立 owner 批准动作」（迁移审计 §4:115；O3 记录 O3 禁止第 1 条；R4 宣告 :137「registry 删除……维持冻结」） | 本报告沿用授权标签 D1 作行内速记，但**首次出现处均标注文档实际表述**；不自行把 D1 写回任何决策文档 |
| 2 | **D2**（删除 adapter_status / O4 步骤⑤） | 文档中**无「D2」编号**。对应动作 = O4 五步迁移的**步骤⑤**「owner 确认无消费方后另行批准删除字段」（决策记录 D-O4 :185 批准范围明确不含步骤⑤；门禁测试 docstring :6；表单草案 D-O4 follow_up :127「⑤owner 确认后删除」） | 同上：D2 为授权标签；文档权威表述 = 「adapter_status 删除 / O4 字段删除（步骤⑤）」 |
| 3 | O5「其余子项」 | 文档中 O5 原为**单一决策项**（lnkcrm code authority 晋升，设计包 §9:413）。2026-10-04 对账记录（lnkcrm-freeze-reconcile）将其中 code 维度冻结线对账拆出为已完成子项 **O5-lnkcrm-code**（decision_id 见该记录 :23），并用「O5 其余子项（五问其余项：deep 读码评估 / 实现级评估解锁等）」（:83、:153）指代剩余部分。**文档未给其余子项分配独立编号**（无 O5-openspec / O5-adapter 之类 ID） | 本报告按设计包 §12.2 五连问结构拆列为 O5-Q4 / O5-Q5 两个盘点行（§3.1），**显式标注「文档未分配独立子编号，拆列仅为盘点可裁决性，不构成编号定义」** |
| 4 | O7 拆三子项 / O10 拆两子项 | 与文档一致（建议包 §3.7 :231-241、§3.10 :267-272；表单草案 D-O7-chat/report/vision、D-O10-report/vision） | 无差异 ✅ |
| 5 | 授权清单未列 Batch 4 | 文档中 Batch 4 =「lnkcrm code authority 晋升实施（company.yaml/INDEX/code README/reconciliation）」（建议包 §4.1:298），是 O5 正式批准后的实施批。其 company.yaml / INDEX / code README / reconciliation 部分已随 docs 提交 c41a978 + O5-lnkcrm-code 路线 A ratify 覆盖（见 §5.3）；剩余内容即 O5 其余子项（§3.1） | 在 O5-Q5 盘点行的事实面中并入说明，不单列 |

## 3. 逐项盘点表（授权 §四字段）

### 3.1 O5 其余子项（lnkcrm code authority 晋升的五问剩余项）

**背景（已完成的 O5-lnkcrm-code，盘点范围外）**：code 维度冻结线经用户会话授权完成
对账（路线 A，ratify docs 提交 c41a978）：company.yaml code_root=/opt/code/lnkcrm、
code authority=complete、门禁/断言三处更新。五问中 **Q1（正式 authority）/ Q2（允许改
company.yaml）/ Q3（生效 revision=4323b8c…，语义改为「不钉具体值、测试只钉非空」）**
已随该对账落地。执行记录
`references/adapter-capability-owner-decision-lnkcrm-freeze-reconcile-2026-10-04.md`。

> 注：设计包 §12.2 五问（:470-485）与建议包 §3.5 五问（:207-215）内容略有差异——
> 前者 Q3 =「是否同步更新 INDEX/code README/reconciliation」，后者 Q3 =「生效
> revision 是哪个 commit」。表单草案 D-O5 follow_up（:153-154）采用后者口径
> （①authority ②company.yaml ③revision ④OpenSpec 基线 ⑤INDEX/README/reconciliation
> + 验证 adapter 集）。本盘点按表单草案口径拆列。

#### 盘点行 O5-Q4（27 个 OpenSpec scope 是否纳入产品实现基线）

| 字段 | 内容 |
|---|---|
| ID | O5-Q4（**文档未分配独立子编号**，属「O5 其余子项/五问其余项」） |
| 名称 | lnkcrm OpenSpec（27 scope）基线纳入裁决 |
| 定义（出处） | 设计包 §12.2 Q4：`references/adapter-capability-decision-2026-10.md:479-481`；建议包 §3.5 Q4：`references/adapter-capability-owner-recommendation-2026-10.md:212`；表单草案 D-O5 follow_up ④：`references/adapter-capability-owner-decision-draft-2026-10.md:154`；冻结出处：对账记录 not_executed（:83「五问其余项：deep 读码评估 / 实现级评估解锁等」） |
| 当前状态 | **frozen**（正式决策记录 :324「全部 pending，全部冻结」；对账记录明确不构成 O5 其余子项批准） |
| 事实面 | 不改任何文件本身——裁决结果决定：requirement-evaluator Step 0 的代码 grep 面是否含 `/opt/code/lnkcrm` 的 27 个 scope、competitor-product-analyzer 的 status_vs_lanlnk 判定输入、openspec-practice 回写链路是否把 lnkcrm scope 纳入产品基线对照。若裁决「纳入」→ 相关 skill 的 SKILL.md/references 措辞与 capability 文件 evidence 更新 |
| 影响面 | requirement-evaluator（lnkcrm partial，实现级 blocked-by-code，设计包 :536）、competitor-product-analyzer（lnkcrm partial）、openspec-practice（lnkcrm scope 扫描）、六份 adapter-capabilities.yaml 中相关 evidence 措辞（不涉 status 语义） |
| 依赖 | 前置 O5-lnkcrm-code 已完成 ✅；与 O5-Q5 可同批签署但语义独立（建议包 §4.3「O5 批准不自动批准任何业务基线」；反之 Q4/Q5 各自独立） |
| 验证要求 | 若批准「纳入」：requirement-evaluator lnkcrm 场景跑一次实测（现无自动化测试钉 lnkcrm grep 面）；capability schema 测试（shared 53 套件）；不触门禁断言 |
| 风险 | 27 scope 活跃开发中（revision 持续前进），纳入基线 = 接受漂移面；不纳入 = requirement-evaluator 实现级评估持续 blocked-by-code，lnkcrm 功能清单 unknown 语义无法收敛 |
| 建议动作 | **待界定**（owner 二选一裁决：纳入 / 不纳入；无可机械化的中间态） |
| 建议优先级 | 高（lnkcrm 产品线唯一剩余阻塞；requirement-evaluator lnkcrm 链路卡在此） |
| 是否需独立 owner 签署 | **是**（默认；表单草案 D-O5 状态 pending） |

#### 盘点行 O5-Q5（晋升后验证 adapter 集启动：deep 读码评估 / 实现级评估解锁）

| 字段 | 内容 |
|---|---|
| ID | O5-Q5（**文档未分配独立子编号**，属「O5 其余子项/五问其余项」） |
| 名称 | code authority 晋升后的业务 skill 验证集启动（deep 读码评估 / 实现级评估解锁） |
| 定义（出处） | 设计包 §12.2 Q5 + 建议最小集：`references/adapter-capability-decision-2026-10.md:482-485`（requirement-evaluator 实现级评估解锁 + strategy-brief-generator 浅盘点→深盘点 + product-prd-generator --code-root 显式确认收敛为 configured）；表单草案 D-O5 consumer_ids/follow_up ⑤：`references/adapter-capability-owner-decision-draft-2026-10.md:140,154`；冻结出处：对账记录 :83 |
| 当前状态 | **frozen**（同上；注意：技术前置已消失——company.yaml 已配置 code_root，`resolve_code_root('lnkcrm')` 现已免显式覆盖直接解析（对账记录改写的 test_paths.py 断言），「prd-gen --code-root 收敛」事实面已随 O5-lnkcrm-code 自然达成，剩余为 skill 层验证行为启用） |
| 事实面 | 各 skill 行为层：requirement-evaluator 是否允许用配置 code root 做实现级代码验证（解除「不得自动用观察 checkout」限制，设计包 :494）；strategy-brief-generator lnkcrm 盘点深度标注从 unconfirmed 升级；相关 SKILL.md 措辞与 capability 文件 evidence（六份 `skills/business/*/references/adapter-capabilities.yaml` 中 lnkcrm 条目） |
| 影响面 | requirement-evaluator / strategy-brief-generator / product-prd-generator 三个 skill 的 SKILL.md + capability 文件 lnkcrm 条目；不改 resolver / company.yaml / 30-products（已就位） |
| 依赖 | 与 O5-Q4 联动（Q4 裁定「纳入」后 Q5 的 grep 面才有意义）但可独立签署；O5-lnkcrm-code 前置已完成 ✅ |
| 验证要求 | shared 套件（53 tests，含门禁三条冻结线）；prd-gen pytest（169 passed / 3 skipped 基线）；capability schema 测试；三 skill 各自测试套件（如 requirement-evaluator 新增用例） |
| 风险 | 实现级评估解锁后，lnkcrm 活跃开发的 revision 漂移会让评估结论快速过时（对账记录 §6.3 已登记该语义变化）；skill 层措辞改动需注意与 capability 文件六态语义不混用 |
| 建议动作 | **待界定**（owner 确认验证最小集范围后按 skill 分批执行） |
| 建议优先级 | 高（与 O5-Q4 同链路） |
| 是否需独立 owner 签署 | **是** |

### 3.2 O6 正祥 CRM 定价归属

| 字段 | 内容 |
|---|---|
| ID | O6 |
| 名称 | 正祥 CRM 定价是否追认为 lnkcrm 报价基线（pricing CRM_DATA 归属登记） |
| 定义（出处） | 设计包 §9-O6：`references/adapter-capability-decision-2026-10.md:414`；§3.3.C lnkcrm 行 :211；建议包 §3.6：`references/adapter-capability-owner-recommendation-2026-10.md:219-229`；表单草案 D-O6：`references/adapter-capability-owner-decision-draft-2026-10.md:157-178` |
| 当前状态 | **frozen**（决策记录 :324 全部 pending；无任何执行记录触碰） |
| 事实面 | `skills/business/pricing-generator/generate_quote.py:280` 的 `CRM_DATA`（正祥交付物受管副本 `materials/03-products/CRM功能清单.xlsx` 的结构化数据）；若登记 → pricing skill 内 evidence 注记 + capability 文件（pricing `references/adapter-capabilities.yaml` lnkcrm 条目，现 partial）evidence 更新 + 可选 `CRM_DATA` 归属注释；**不写 docs 仓**（pricing-basis.yaml 在 docs：`/opt/code/docs/lanlnk/config/pricing/pricing-basis.yaml`，追认为正式基线才涉及） |
| 影响面 | pricing-generator（lnkcrm partial，「历史 CRM 报价无主使用」，设计包 :537）；`30-products/lnkcrm/prd/功能清单.md` 是否接入报价链（现未接入） |
| 依赖 | 与 O5-Q4/Q5 无直接依赖；若追认为正式基线则需先答表单草案 D-O6 follow_up 六要素（适用产品/版本/有效期/标准与定制边界/owner/对外性，:176-177） |
| 验证要求 | pricing-generator pytest（6 tests 基线，B5-R5 记录）；capability schema 测试；如改 CRM_DATA 注释 → 生成一份 CRM 报价冒烟验证 |
| 风险 | 直接追认 = 「历史 CRM 报价无主顶替 lnkcrm 产品报价基线」（跨产品借用禁令同源风险，建议包 :228-229）；不裁决 = CRM_DATA 继续无主使用（drift 风险持续） |
| 建议动作 | **字段收敛（轻）**：先按建议包 §3.6 登记为 customer-specific / historical pricing evidence（Batch 3 轻动作），正式追认另案 |
| 建议优先级 | 中（pricing lnkcrm 链路 partial 已可用，属归属清晰化而非功能阻塞） |
| 是否需独立 owner 签署 | **是** |

### 3.3 O7-chat lnkchat 报价定位

| 字段 | 内容 |
|---|---|
| ID | O7-chat |
| 名称 | lnkchat 独立产品报价 vs AI 岗位 Skill 服务打包售卖 |
| 定义（出处） | 设计包 §9-O7 / §3.3.C lnkchat 行：`references/adapter-capability-decision-2026-10.md:212,415`；§13.1 pricing 行 :513；建议包 §3.7 表：`references/adapter-capability-owner-recommendation-2026-10.md:237`；表单草案 D-O7-chat：`references/adapter-capability-owner-decision-draft-2026-10.md:180-200` |
| 当前状态 | **frozen**（pending positioning，决策记录 :324） |
| 事实面 | 纯定位裁决，先于任何文件动作。若裁决「建独立基线」→ pricing-generator 新增 lnkchat 数据结构（类比 `LNKCHATBI_DATA`）+ pricing-basis.yaml 登记 + capability 文件（pricing lnkchat 条目现 unsupported）升级；若裁决「打包售卖不单列」→ capability 文件 lnkchat 改 not-applicable（pricing 面）+ evidence 注记 |
| 影响面 | pricing-generator（lnkchat unsupported）；capability 文件 pricing 份；不影响 resolver/company.yaml |
| 依赖 | 无技术前置；禁令：不得从 lnkcre 或其他产品复制价格（表单草案 :196，跨产品借用禁令） |
| 验证要求 | 裁决后按落地动作定：pricing pytest + capability schema 测试 |
| 风险 | 定位不清时建基线 = 语义误判（把跨产品编排的岗位服务错当单产品报价）；维持现状 = unsupported 持续 |
| 建议动作 | **待界定**（owner 定位二选一：独立报价 / 打包不单列） |
| 建议优先级 | 中 |
| 是否需独立 owner 签署 | **是** |

### 3.4 O7-report lnkreport 报价基线

| 字段 | 内容 |
|---|---|
| ID | O7-report |
| 名称 | lnkreport 独立产品功能清单与报价基线建设 |
| 定义（出处） | 设计包 §9-O7 / §3.3.C lnkreport 行：`references/adapter-capability-decision-2026-10.md:214,415`；建议包 §3.7 表：`references/adapter-capability-owner-recommendation-2026-10.md:238`（建议 onboarding）；表单草案 D-O7-report：`references/adapter-capability-owner-decision-draft-2026-10.md:202-221` |
| 当前状态 | **phase3-landed**（2026-10-04 O7-report Phase 1-3 已执行；金额待定价；执行记录见 `references/adapter-capability-owner-decision-o7-report-phase3-execution-2026-10-04.md`） |
| 事实面 | 分步链：功能清单（`30-products/lnkreport/prd/` 现有 canonical 基线）→ 定价 → `/opt/code/docs/lanlnk/config/pricing/pricing-basis.yaml` 登记（各步 owner 确认，表单草案 :220）→ pricing-generator 数据结构 + capability 文件（pricing lnkreport 现不支持）升级 |
| 影响面 | pricing-generator；pricing-basis.yaml（docs 仓，改动需 docs 侧流程）；capability 文件 pricing 份；`30-products/lnkreport/prd/`（若功能清单需刷新） |
| 依赖 | 无技术前置；硬禁令：不得复制 lnkcre 价格（表单草案 :217）；建议包建议值 = onboarding（三子项中唯一建议直接推进的） |
| 验证要求 | pricing pytest；capability schema 测试；pricing-basis.yaml 变更后跑一次 lnkreport 报价冒烟 |
| 风险 | 功能清单来源不明确时直接定价 = 基线无根；docs 仓改动需走 docs 侧授权 |
| 建议动作 | **待界定**（建议包已建议 onboarding，正式启动仍需 owner 签署 D-O7-report + 确认功能清单来源） |
| 建议优先级 | 中 |
| 是否需独立 owner 签署 | **是** |

### 3.5 O7-vision lnkvision 报价定位

| 字段 | 内容 |
|---|---|
| ID | O7-vision |
| 名称 | lnkvision 产品定位与是否面客（报价前置） |
| 定义（出处） | 设计包 §3.3.C lnkvision 行（pricing unsupported）：`references/adapter-capability-decision-2026-10.md:215`；建议包 §3.7 表：`references/adapter-capability-owner-recommendation-2026-10.md:239`；表单草案 D-O7-vision：`references/adapter-capability-owner-decision-draft-2026-10.md:223-243` |
| 当前状态 | **frozen**（positioning decision required，决策记录 :324） |
| 事实面 | 纯定位裁决。落地路径与 O7-chat 同构（建基线 → pricing 数据+登记+capability 升级；不面客 → not-applicable） |
| 影响面 | pricing-generator（lnkvision unsupported）；capability 文件 pricing 份 |
| 依赖 | 与 O10-vision、O9 联动审议（表单草案 :242）——lnkvision 定位同时决定报价面与叙事面 |
| 验证要求 | 裁决后按落地动作定 |
| 风险 | 与 O10-vision 分开裁决会产生定位口径分裂（一个面客一个不面客） |
| 建议动作 | **待界定**（建议与 O10-vision、O9 同批联审，分别签署） |
| 建议优先级 | 低 |
| 是否需独立 owner 签署 | **是** |

### 3.6 O8 LnkChatBI 标准定价基线

| 字段 | 内容 |
|---|---|
| ID | O8 |
| 名称 | lnkchatbi 标准定价登记入 pricing-basis.yaml（替换 env 默认 0） |
| 定义（出处） | 设计包 §9-O8 / §3.3.C lnkchatbi 行：`references/adapter-capability-decision-2026-10.md:213,416`（「env 默认 0，每次人工输入」）；建议包 §3.8：`references/adapter-capability-owner-recommendation-2026-10.md:243-253`；表单草案 D-O8：`references/adapter-capability-owner-decision-draft-2026-10.md:245-266` |
| 当前状态 | **frozen**（建议包建议值 = 可批准建设，但正式决策记录 :324 仍 pending） |
| 事实面 | `/opt/code/docs/lanlnk/config/pricing/pricing-basis.yaml`（现只有费率无产品定价，设计包 :213）；`generate_quote.py:472-473`（`LNKCHATBI_PRICE_Y1/Y2` env，默认 0）；capability 文件 pricing 份 lnkchatbi 条目（现 partial）——「结构在位、缺正式定价」的典型（建议包 :252-253） |
| 影响面 | pricing-generator；pricing-basis.yaml（docs 仓）；capability 文件 pricing 份（partial→implemented 的路径） |
| 依赖 | **前置 4 条件**（表单草案 :264-265）：标准功能清单来源 / 标准版与定制版边界 / 定价生效日期 / pricing-basis.yaml 写入范围；硬禁令：不得套用 lnkchat 或 lnkcre 价格（:260） |
| 验证要求 | 落盘后跑 lnkchatbi 报价冒烟（不带 env 应出新默认价）；pricing pytest；capability schema 测试 |
| 风险 | 前置条件未齐时写 pricing-basis.yaml = 违禁（表单草案 :261）；生效日期缺失会让历史报价口径漂移 |
| 建议动作 | **待界定**（建议包已「建议批准建设」，正式批准需 owner 签署 D-O8 + 4 条件齐） |
| 建议优先级 | 高（48 格中 partial→implemented 唯一接近完成项；当前每次报价人工输入是实际运营摩擦） |
| 是否需独立 owner 签署 | **是** |

### 3.7 O9 lnkgateway 产品定位

| 字段 | 内容 |
|---|---|
| ID | O9 |
| 名称 | lnkgateway 是否永不独立面客（平台基础设施 / 集成网关 / 内部能力） |
| 定义（出处） | 设计包 §9-O9 / §3.3.C lnkgateway 行 / §13.2：`references/adapter-capability-decision-2026-10.md:216-217,517-524`；建议包 §3.9：`references/adapter-capability-owner-recommendation-2026-10.md:255-265`；表单草案 D-O9：`references/adapter-capability-owner-decision-draft-2026-10.md:268-287` |
| 当前状态 | **frozen**（决策记录 :324）。**注意矩阵侧现状**：O2 批准的 48 格矩阵首版已含 ★ 预改判——pricing×lnkgateway 与 company-intro×lnkgateway 现为 `not-applicable`（实测两份 capability 文件，本会话 grep；迁移审计 §3:105 lnkgateway=blocked 指 prd-gen/competitor 面）。即「not-applicable 落地」的矩阵值已存在，**O9 剩余 = owner 正式确认「永不独立面客」的定位裁定本身**（把预改判转为定判） |
| 事实面 | 裁决落地时：capability 文件（pricing/company-intro 两份）lnkgateway 条目 evidence 更新（现值已正确，仅补正式裁定依据）；若裁定「未来可能面客」→ 回改矩阵值并重建报价/叙事输入清单 |
| 影响面 | pricing-generator / company-intro-generator 的 lnkgateway 条目；与 O11 联动（表单草案 :286） |
| 依赖 | 与 O11 联动但独立签署；冻结线 `lnkgateway ontology=unresolved / ontology_entry=null` 不受 O9 影响（门禁 :61 钉死） |
| 验证要求 | capability schema 测试；门禁冻结线断言（不应受影响，跑通即证） |
| 风险 | 语义误判风险：把「暂不面客」当「永不面客」落定评断 —— 建议包用词为「暂定定位」（:257），表单草案 scope 是「是否**永不**独立面客」（:275），签署时 owner 需明确选边 |
| 建议动作 | **待界定**（owner 三态裁决：永不面客落定 / 暂不面客维持 / 未来面客重建） |
| 建议优先级 | 低（矩阵值已按 not-applicable 预改判落地，现状无运营摩擦） |
| 是否需独立 owner 签署 | **是** |

### 3.8 O10-report lnkreport 叙事资产

| 字段 | 内容 |
|---|---|
| ID | O10-report |
| 名称 | company-intro 面的 lnkreport 产品叙事资产建设 |
| 定义（出处） | 设计包 §3.3.E lnkreport 行：`references/adapter-capability-decision-2026-10.md:244`（「materials grep 无专属叙事命中」）；建议包 §3.10：`references/adapter-capability-owner-recommendation-2026-10.md:271`（建议「可启动」）；表单草案 D-O10-report：`references/adapter-capability-owner-decision-draft-2026-10.md:289-308` |
| 当前状态 | **frozen**（决策记录 :324） |
| 事实面 | `/opt/code/docs/lanlnk/materials/03-products/` 新增 lnkreport 产品叙事文档（表单草案 :307，Batch 3）；capability 文件 company-intro 份 lnkreport 条目（现 unsupported）升级 |
| 影响面 | company-intro-generator；materials 素材库（docs 仓，走 docs 侧流程/material-importer）；capability 文件 company-intro 份 |
| 依赖 | 无技术前置；禁令：不得用其他产品叙事顶替（表单草案 :304） |
| 验证要求 | 素材入库走 material-importer validate；capability schema 测试 |
| 风险 | 低（纯增量资产建设，无回退面） |
| 建议动作 | **待界定**（建议包已建议「可启动」，正式启动需签署 D-O10-report） |
| 建议优先级 | 低 |
| 是否需独立 owner 签署 | **是** |

### 3.9 O10-vision lnkvision 叙事资产

| 字段 | 内容 |
|---|---|
| ID | O10-vision |
| 名称 | lnkvision 叙事资产前置定位确认（目标客户 / 与 lnkreport 边界） |
| 定义（出处） | 设计包 §3.3.E lnkvision 行：`references/adapter-capability-decision-2026-10.md:245`（「MallSenseAI/LnkVision 更名前后均无命中」）；建议包 §3.10：`references/adapter-capability-owner-recommendation-2026-10.md:272`；表单草案 D-O10-vision：`references/adapter-capability-owner-decision-draft-2026-10.md:310-329` |
| 当前状态 | **frozen**（决策记录 :324） |
| 事实面 | 先定位裁决后资产建设；落地路径与 O10-report 同构（materials 新增叙事 + capability 文件 company-intro 份 lnkvision 条目升级，现 unsupported） |
| 影响面 | company-intro-generator；materials 素材库；capability 文件 company-intro 份 |
| 依赖 | 与 O7-vision、O9 联动审议（表单草案 :328）——同一产品定位三面（报价/叙事/网关边界参照）一次理清 |
| 验证要求 | 同 O10-report |
| 风险 | 与 O7-vision 分开裁决产生定位口径分裂 |
| 建议动作 | **待界定**（建议与 O7-vision 同批联审） |
| 建议优先级 | 低 |
| 是否需独立 owner 签署 | **是** |

### 3.10 O11 lnkgateway ontology 处置方向

| 字段 | 内容 |
|---|---|
| ID | O11 |
| 名称 | lnkgateway ontology 长期方向三选一（独立产品 / 平台基础能力 / 不建独立 ontology） |
| 定义（出处） | 设计包 §9-O11 / §13.2：`references/adapter-capability-decision-2026-10.md:419,521,523`；建议包 §3.11：`references/adapter-capability-owner-recommendation-2026-10.md:274-285`；表单草案 D-O11：`references/adapter-capability-owner-decision-draft-2026-10.md:331-351` |
| 当前状态 | **frozen**（短期保持 unresolved；决策记录 :324） |
| 事实面 | 裁决三选一：① 独立产品 ontology → 建 `30-products/lnkgateway/ontology/` + company.yaml 补记；② 平台基础能力 ontology → 同上但语义不同；③ 集成层能力不建 → 裁定 not-applicable 并解除 blocked 的替代路径说明。现状钉死：`company.yaml lnkgateway prd_ready=false`（ontology/PRD unresolved）、门禁冻结线 `ontology=unresolved / ontology_entry=null / 无跨产品 fallback`（门禁 :61、:250-260） |
| 影响面 | product-prd-generator 与 competitor-product-analyzer 的 lnkgateway 链路（capability 现均为 **blocked**，迁移审计 §3:105）——「解除 blocked 的唯一路径是本决策落地」（设计包 :419）；company.yaml（docs 仓）；30-products/lnkgateway/；门禁测试 lnkgateway 冻结线断言（若裁决①②需同 commit 更新门禁） |
| 依赖 | 与 O9 联动但独立签署（建议包 :285）；硬禁令：不得从网关代码反推 ontology（owner 既有裁定维持，表单草案 :346）；不得未经批准自动创建任一种（:347） |
| 验证要求 | 若裁决①②：shared 套件（门禁 lnkgateway 断言同 commit 更新）+ prd-gen/competitor 相关测试 + lnkgateway resolver 实测（ontology_entry 非 null）；若裁决③：capability 文件两份 blocked→not-applicable + schema 测试 |
| 风险 | 风险最高的单项之一：裁决①②直接改 authority 冻结线，须与门禁测试原子化；「从代码反推 ontology」是 owner 既有明令禁止（语义误判+跨域污染闸门） |
| 建议动作 | **待界定**（owner 三选一；短期维持 unresolved 是建议包建议值，无文件动作） |
| 建议优先级 | 低（短期维持无摩擦；仅当 lnkgateway 需要进 prd-gen/competitor 链路时才升为高） |
| 是否需独立 owner 签署 | **是** |

### 3.11 undefined-in-source 检查结论

对授权清单 11 个盘点对象逐一检索后：**O6、O7-chat、O7-report、O7-vision、O8、O9、
O10-report、O10-vision、O11 九项在设计包 §9 / 建议包 §3 / 表单草案 D-块三层均有
权威定义，无 undefined-in-source 项**。唯一部分界定的是 O5 其余子项：定义存在
（五问框架 + 「五问其余项」措辞），但**文档未给剩余部分分配独立子编号**（§2 差异
记录 #3），本报告按表单草案五问口径拆为 O5-Q4 / O5-Q5 两行，不构成编号定义。

## 4. 交叉核对结论（授权 §五，全部只读实测）

### 4.1 零消费方证据（为 D1/D2 决策服务，仅核对）

**product-registry.yaml 程序化消费方 = 0（本会话实测）**：

| 检查 | 结果 |
|---|---|
| 生产代码 `yaml.safe_load`/`yaml.load` 加载 registry | **0 处**（`rg "safe_load\|yaml.load" shared skills -g '*.py' \| rg -i registry` 空输出） |
| `_paths.py` 中 "product-registry" 命中 | 5 处（:41,:48,:163-164,:166,:327），逐行核验**全部为 docstring/注释**（R2/R3 对齐后的迁移期说明文案） |
| 测试文件命中（governance/semantic/authority-fixtures/schema 四文件） | 8 处，逐行核验**全部为注释**（「B1 迁移（2026-10-04）：断言来源自 product-registry.yaml 改为…」类说明）；B1 执行后无任何 `yaml.safe_load` 读 registry |
| `check_docs_consistency.sh` | 仅 :216-217 注释（B2 迁移说明）；Check 4 对账面已改 company.yaml products |
| **结论** | **零运行时消费方成立**。且审计 §4 删除阻塞项 **B1-B7 已全部解除**（B1/B2/B3/B4/B5/B6/B7 注记 + O3 follow_up 11 条状态指针 + R3 记录「B1-B7 全部解除」）——registry 删除（D1）的阻塞清单已清空，剩余前置仅为独立 owner 批准本身 + 删除时同步处置 8 处测试注释与 5 处 _paths 注释（随删除 commit 清理） |

**adapter_status 程序化消费方 = 白名单内零业务消费（本会话实测）**：

| 检查 | 结果 |
|---|---|
| 全仓 `.py/.sh` 命中计数 vs 门禁白名单 | `models.py`=2 ✅、`resolver.py`=2 ✅、`test_adapter_capabilities_schema.py`=7 ✅、`test_product_governance_contracts.py`=0 ✅——与 `ALLOWED_ADAPTER_STATUS_SOURCES` 精确一致 |
| 白名单外命中 | 仅门禁测试自身（自指豁免，:48） |
| resolver 输出面 | 兼容透传保留：company.yaml products 块**无** adapter_status 键 → 全部产品回落 `unsupported`（本会话 live 抽测 lnkcrm/lnkgateway/lnkwebsite 三产品输出均为 unsupported，非 capability 声明） |
| **结论** | **零业务逻辑分支消费成立**（仅定义+赋值+序列化透传+测试自检）。O4 步骤⑤（D2）的证据前提「确认无消费方」在程序化消费面上已满足；删除时须同 commit 更新门禁测试（dataclass 字段断言 :104-109 会失败即设计如此） |

### 4.2 门禁现状（`shared/product_context/tests/test_adapter_status_migration_gate.py`）

- **O4 白名单**（:40-45）：4 文件精确计数（值=允许命中行数上限，精确相等防夹带）；
  models.py=2（定义+序列化）、resolver.py=2（透传+构造）、schema 测试=7（键级禁令
  自检）、governance contracts=0（B1 清零基线，防回流）。扩充白名单需 owner 批准。
- **三条 authority 冻结线**（:59-63，live 断言非 fixture）：
  - `lnkcrm: {code: complete}`（2026-10-04 O5-lnkcrm-code 路线 A 对账更新，ratify docs c41a978）
  - `lnkgateway: {ontology: unresolved}`（ontology_entry=null，无跨产品 fallback）
  - `lnkwebsite: {ontology: not-applicable}`（product_status=prd-only）
- **附加门禁**：resolver 不读 capability 文件（方案 B 红线）；capability 专有状态
  `blocked` 不得泄入 authority；放宽/移除断言 = 违反 O4 禁令需 owner 独立批准。
- **D2 原子化边界证据**：删除 adapter_status 字段必须同 commit 更新本门禁
  （`test_dataclass_field_not_removed_or_renamed` :104-109 + 白名单 models/resolver
  计数归零），单 commit 可 revert。

### 4.3 台账一致性核对（company.yaml ↔ 30-products 治理面 ↔ resolver live）

| 核对项 | 结果 |
|---|---|
| company.yaml products | 8 产品全登记（lnkcre/lnkcrm/lnkchat/lnkchatbi/lnkreport/lnkvision/lnkgateway/lnkwebsite），`# --- products-end ---` marker 在位 |
| lnkcrm code 基线 | ✅ 一致三层：company.yaml `code_root: /opt/code/lnkcrm`（prd_ready 保持 false）↔ 30-products/lnkcrm/INDEX.md「代码仓 /opt/code/lnkcrm（revision 4323b8c9…）」+ code/README.md「external-confirmed」+ reconciliation 对账行「代码仓验收快照 42/105/0」↔ live resolver `code_auth=complete`（revision 非空） |
| lnkgateway 基线 | ✅ 一致：company.yaml `prd_ready: false`（ontology/PRD unresolved 注记）↔ live resolver `ontology_auth=unresolved / ontology_entry=None / 无跨产品 fallback` ↔ 门禁冻结线一致 |
| lnkwebsite 基线 | ✅ 一致：live resolver `product_status=prd-only / ontology_auth=not-applicable` ↔ 门禁冻结线一致 |
| capability 权威源 | 六份 `skills/business/*/references/adapter-capabilities.yaml` 全在位；关键值实测：lnkgateway = prd-gen/competitor `blocked`、pricing/company-intro `not-applicable`（O2 ★ 预改判）；lnkwebsite = not-applicable（pricing 份）——与迁移审计 §3 矩阵一致 |
| **结论** | **台账一致，无 drift**。现行基线与授权 §五.3 所述完全吻合（lnkcrm code=complete、lnkgateway unresolved/无 fallback、lnkwebsite prd-only/not-applicable） |

## 5. 补充事实（对 D1/D2 决策有用的现状快照）

1. **B1-B7 全部解除**（各执行记录 + 审计 §4 注记 + O3 follow_up）；R4 已宣告
   product-registry.yaml「迁移期 prose 残留族」关闭（0 新残留）。
2. **registry 现性质**：迁移期兼容元数据/历史镜像（头部规则 6/8/10 已全部对齐该
   口径）；YAML 数据区冻结快照（8 产品键完整；lnkgateway=unsupported /
   lnkwebsite=unsupported 与 capability 权威源存在**已登记的枚举性差异**，非漂移）。
3. **O1/O2/O4 已批准**（决策记录 2026-10-04：O1 方案 B :26-32、O2 矩阵首版
   :100-106、O4 五步迁移保留兼容期 :179-185）；O3 audit-only 已批准并执行
   （o3-batch2 记录）。**O5-O11 全部 pending/冻结**（决策记录 :324）。
4. **docs 侧 00-governance/registries/** 现有 document-registry.yaml /
   traceability.yaml，无 adapter capability 中心文件（方案 B 红线维持，O3 禁止第 2 条）。

## 6. 零修改实证（授权 §八）

```bash
cd /opt/code/skill
git status --short   # 执行前后对比：除新增本文件（untracked）外完全一致
git diff --name-only # 既有 M 文件清单与执行前快照逐一相同，无新增 diff
```

执行前基线快照（本会话开跑时捕获）：25 个 M 文件（AGENTS.md、check_docs_consistency.sh、
product-prd-generator 系列测试与 references、多个 SKILL.md 等）+ 既有 untracked 条目
（21 个决策/执行记录、shared/、六份 adapter-capabilities.yaml、pricing tests 等）。
执行后复核：**仅新增本报告文件，其余原样保留**（见下方最终核验输出）。未跑测试
套件（未改代码；测试结论引用既有基线记录：shared 53 OK / prd-gen 169 passed +
3 skipped / check_docs_consistency FAIL=0 WARN=0 PASS=33）。

## 7. Owner 逐项授权请求表（可复制填写）

> 填写说明：每行独立裁决；「批准」仅指该行 scope；未填 = 不构成批准（表单草案
> 口径）。D1/D2 行为授权标签速记，文档权威表述见 §2。

```yaml
owner: 
signed_at:                    # YYYY-MM-DD HH:mm TZ
signing_note: 

# ── 冻结 backlog（本报告 §3）──
O5-Q4:                        # pending | approved(纳入) | approved(不纳入) | rejected
O5-Q5:                        # 验证最小集：requirement-evaluator / strategy-brief / prd-gen
O6:                           # pending | approved(仅evidence登记) | approved(追认) | rejected
O7-chat:                      # pending | approved(独立报价) | approved(打包不单列) | rejected
O7-report:                    # pending | approved(onboarding) | rejected
O7-vision:                    # pending | approved(面客) | approved(不面客) | rejected
O8:                           # pending | approved(建设,4前置条件见D-O8) | rejected
O9:                           # pending | approved(永不面客) | approved(暂不,维持) | rejected
O10-report:                   # pending | approved(启动) | rejected
O10-vision:                   # pending | approved(与O7-vision联审后启动) | rejected
O11:                          # pending | approved(①独立产品) | approved(②平台基础) | approved(③不建) | rejected

# ── 冻结动作（本报告仅盘点，见 §2 差异记录）──
D1_registry_deletion:         # pending | approved | rejected   # 文档表述：删除 product-registry.yaml
D2_adapter_status_deletion:   # pending | approved | rejected   # 文档表述：O4 步骤⑤ adapter_status 字段删除
```

## 8. 显式声明

1. **授权来源**：会话只读盘点授权；OWNER SIGN-OFF: NOT RECORDED。
2. **本轮产出**：仅新增本盘点报告文件（untracked）；既有文件零修改（§6 实证）。
3. **本轮未执行**：D1、D2、O5 任何子项、O6-O11 任何一项的实际动作；未删除/重命名
   registry 或 adapter_status 字段；未改 resolver、company.yaml、30-products/**、
   capability 文件、产品代码、审计/决策记录；未使用 git add -A；未提交、未推送；
   未回退/覆盖/清理既有未提交修改。
4. **盘点完成不等于授权**：本报告不构成 D1/D2 或任何 O5/O6-O11 项的批准；全部
   上述动作维持冻结，各自需独立 owner 签署。

## 9. 状态更新（2026-10-04 O5-Q4 执行后追加）

- **O5-Q4：frozen → included/landed**。owner 决策 approved + include
  （`references/adapter-capability-owner-decision-o5-q4-2026-10-04.md`，OWNER SIGN-OFF:
  RECORDED (OPC)）；三消费面（requirement-evaluator / competitor-product-analyzer /
  openspec-practice）措辞与 capability evidence 已接线，执行记录见
  `references/adapter-capability-owner-decision-o5-q4-execution-2026-10-04.md`。
  §3.1 行「当前状态 frozen」为落盘时快照，以本注记为准。
- **O5-Q5 维持冻结**（Q4 纳入不自动解锁 Q5）：requirement-evaluator 实现级评估
  （deep 读码）保持 blocked-by-code；strategy-brief-generator 不升深盘点；
  prd-gen 行为层不动。

## 10. 状态更新（2026-10-04 O5-Q5 执行后追加）

- **O5-Q5：frozen → unlocked/landed**。owner 决策 approved + unlock
  （`references/adapter-capability-owner-decision-o5-q5-2026-10-04.md`，OWNER SIGN-OFF:
  RECORDED (OPC)）；三 skill（requirement-evaluator / strategy-brief-generator /
  product-prd-generator）行为层解锁——lnkcrm 实现级评估可用（结论钉评估时 revision +
  漂移警示；适用面 = code authority complete 产品），Q4「待 O5-Q5」边界注记已全部接续为
  已解锁。执行记录见 `references/adapter-capability-owner-decision-o5-q5-execution-2026-10-04.md`。
  §3.1 行与 §9 末条「O5-Q5 维持冻结」为落盘时快照，以本注记为准。
- **O5 五问全部闭合**（Q1-Q3 随 O5-lnkcrm-code 落地，Q4 include，Q5 unlock）。
- **其余维持冻结**：O6-O11、D1/D2 删除动作、O4⑤、lnkreport 定价（挂起）。

## 11. 状态更新（2026-10-04 O8 执行后追加）

- **O8：frozen → decided-rejected（rejected-registration 已落地）**。owner 决策驳回
  标准价登记（`references/adapter-capability-owner-decision-o8-2026-10-04.md`，
  OWNER SIGN-OFF: RECORDED (OPC)）：不写 pricing-basis.yaml 任何 lnkchatbi 定价段
  （费率三键零改动）；LNKCHATBI_PRICE_Y1/Y2 默认 0 语义对齐为随单赠送策略
  （仅注释/帮助/备注文案，env 读取逻辑与默认行为零改动）；pricing-generator
  capability lnkchatbi 条目 partial→implemented（赠送策略为设计语义，env 人工输入
  非缺口；shared 钉线与 pricing 本地八产品全景钉同批）。执行记录见
  `references/adapter-capability-owner-decision-o8-execution-2026-10-04.md`。
  §3.6 行「当前状态 frozen」与「O8（pending）批准后可 partial→implemented」为落盘时
  快照，以本注记为准。
- **其余维持冻结**：O6/O7-*/O9/O10-*/O11、删除动作、lnkreport 定价（挂起）。

## 12. 状态更新（2026-10-04 O6 执行后追加）

- **O6：frozen → decided-A / evidence-registered（historical evidence 已登记）**。owner
  决策 register-as-historical-evidence 方案 A
  （`references/adapter-capability-owner-decision-o6-2026-10-04.md`，OWNER SIGN-OFF:
  RECORDED (OPC)）：不追认 lnkcrm 正式报价基线——generate_quote.py CRM_DATA（:280 附近）
  归属注释登记（正祥单一客户历史成交证据，仅注释，数据结构/数值/env 逻辑/生成行为零改动）；
  pricing capability lnkcrm 条目 evidence/notes 更新（历史无主使用 → 已登记归属），
  status 保持 partial（正式基线未建，partial 语义准确）；B 路线六要素留档另案（决策记录
  route_B_prerequisites）。执行记录见
  `references/adapter-capability-owner-decision-o6-execution-2026-10-04.md`。
  §3.2 行「当前状态 frozen」为落盘时快照，以本注记为准。
- **其余维持冻结**：O7-*/O9/O10-*/O11、删除动作、lnkreport 定价（挂起）。

## 13. 状态更新（2026-10-05 O9 执行后追加）

- **O9：frozen → decided-B / 定判（evidence 登记轮，status 值零变更）**。owner 决策
  not-independently-customer-facing（`references/adapter-capability-owner-decision-o9-2026-10-04.md`，
  OWNER SIGN-OFF: RECORDED (OPC)）：lnkgateway 暂不独立面客（平台基础设施 / 集成网关 /
  内部能力），预改判转定判，可复议；两份 capability 文件（pricing-generator /
  company-intro-generator）lnkgateway 条目 evidence/notes 登记定判依据，status 保持
  not-applicable（O11 冻结线不受影响，钉线测试零改动即绿）。执行记录见
  `references/adapter-capability-owner-decision-o9-execution-2026-10-04.md`。
  §3.7 行「当前状态 frozen」为落盘时快照，以本注记为准。
- **其余维持冻结**：O7-vision / O10-* / O11、删除动作、lnkreport 定价（挂起）。

## 14. 状态更新（2026-10-05 O7-chat 执行后追加）

- **O7-chat：frozen → decided-B / bundled（bundled-not-listed 已落地）**。owner 决策
  bundled-not-listed（`references/adapter-capability-owner-decision-o7-chat-2026-10-04.md`，
  OWNER SIGN-OFF: RECORDED (OPC)）：lnkchat 随 AI 岗位 Skill 服务打包售卖，不建独立
  产品报价、不在报价单单列；打包报价走 generate_quote.py AI 岗位 Skill 产品线
  （build_ai_data，product_name「LnkAgent AI岗位Skill增强服务」）与
  materials/references/报价模板_AI岗位Skill_SAAS.md（均零改动，只读取证）；pricing
  capability lnkchat 条目 unsupported→not-applicable（evidence/notes 同批更新；shared
  钉线 EXPECTED_MATRIX/EXPECTED_DISTRIBUTION 与 pricing 本地八产品全景钉同 commit）。
  执行记录见 `references/adapter-capability-owner-decision-o7-chat-execution-2026-10-04.md`。
  §3.3 行「当前状态 frozen」为落盘时快照，以本注记为准。
- **其余维持冻结**：O7-vision / O10-* / O11、删除动作、lnkreport 定价（挂起）。

## 15. 状态更新（2026-10-05 O7-vision 执行后追加）

- **O7-vision：frozen → decided / customer-facing（面客定判 + 报价基线结构落地，金额留空
  待定价）**。owner 决策 customer-facing
  （`references/adapter-capability-owner-decision-o7-vision-2026-10-04.md`，OWNER SIGN-OFF:
  RECORDED (OPC)）：lnkvision 为独立面客产品；generate_quote.py LNKVISION_DATA 落地（完全
  复用 LNKREPORT_DATA 已核定模式：四段八列、金额一律留空/None + 「待定价」标记、
  RATIFIED_ZEROS 白名单外零值、build_lnkvision_data 无数值时显式拒绝生成、组合报价含
  lnkvision 时写盘前拒绝；模块分组草案依据 30-products/lnkvision/prd/功能清单.md 落执行
  记录 §3 待 OPC 复核，existing 18 = 5+5+5+2+1 全 31 行分配闭合）；pricing capability
  lnkvision 条目 unsupported→onboarding（evidence/notes 同批更新；shared 钉线
  EXPECTED_MATRIX/EXPECTED_DISTRIBUTION（unsupported 4→3 / onboarding 6→7）与 pricing
  本地八产品全景钉同 commit）。执行记录见
  `references/adapter-capability-owner-decision-o7-vision-execution-2026-10-04.md`。
  §3.5 行「当前状态 frozen」为落盘时快照，以本注记为准。定价数值挂起（待 OPC 提供，
  提供前另开授权填数并升级 implemented）；「面客」定判同时构成 O10-vision 叙事面的定位
  依据，但 O10-vision 启动仍为独立签署项。
- **其余维持冻结**：O10-* / O11、删除动作、lnkreport / lnkvision 定价（挂起）。
