# 业务 skill adapter capability —— Owner 决策建议包（2026-10-04）

> **STATUS: RECOMMENDATION ONLY — OWNER APPROVAL REQUIRED**
>
> 本包是**建议**，不是批准。未发生、也不构成本文所列任何决策项的 owner 批准。
> 所有实施动作（Batch 1/2/3/4）在 owner 正式签署前**全部冻结**。
>
> - 依据一（设计文档）：`references/adapter-capability-decision-2026-10.md`（下称「设计包」，含
>   O1-O11 编号、方案 A/B/C 比较、§2 状态语义、§3 六消费方×八产品矩阵、附录 A schema 草案）
> - 依据二（上一轮报告）：「Owner 决策等待与批准记录接入」报告（O1-O11 等待框架与批次结构）
> - 依据三（实测复核）：2026-10-04 resolver `--all` 只读复核 + lnkcrm checkout 只读观察（§1）
> - 决策表单草案：`references/adapter-capability-owner-decision-draft-2026-10.md`
>   （**DRAFT / NOT AN APPROVAL RECORD / OWNER SIGN-OFF REQUIRED**）
> - 本包归属：skill 仓 `references/` 审计位置。**不放入正式治理 registry**；owner 签署后
>   才可转为正式决策记录，转换方式由 owner 指定。

---

## 0. 结论速览

| 决策项 | 主题 | 建议 | 推荐阶段 |
|---|---|---|---|
| O1 | 方案 B（capability 消费方自声明） | **建议批准**（范围限 Batch 1：设计 + 首版 capability 文件） | 第一阶段 |
| O2 | 48 格矩阵现状判定 | 并入 O1 Batch 1 批准范围（首版文件即矩阵落地；可单独审议，见表单） | 第一阶段（随 O1） |
| O3 | 方案 C 豁免（仅拒 B 选 C 时） | B 方案下**不触发**；表单保留条件性占位 | — |
| O4 | resolver `adapter_status` 废弃 | **建议批准迁移**，带过渡期；本阶段**不删除字段** | 第一阶段 |
| O5 | lnkcrm code authority 晋升 | **deferred / conditional approval**（暂缓，见 §3.5） | 第三阶段前置确认 |
| O6 | 正祥 CRM 定价追认 | **暂不追认**；先登记 customer-specific / historical evidence | 第三阶段 |
| O7-chat | lnkchat 报价基线 | pending positioning（先确认独立报价 vs AI Skills 打包） | 第三阶段 |
| O7-report | lnkreport 报价基线 | onboarding（建独立功能与价格基线） | 第三阶段 |
| O7-vision | lnkvision 报价基线 | positioning decision required（先确认定位与是否面客） | 第三阶段 |
| O8 | LnkChatBI 标准定价 | **建议批准**建设独立报价基线（4 项前置条件 + owner 确认后落盘） | 第三阶段 |
| O9 | lnkgateway 定位 | 暂不作为独立面客产品；暂定平台基础设施 / 集成网关 / 内部能力 | 第三阶段 |
| O10-report | lnkreport 叙事资产 | 可启动叙事资产建设 | 第三阶段 |
| O10-vision | lnkvision 叙事资产 | 先确认定位、目标客户、与 lnkreport 边界 | 第三阶段 |
| O11 | lnkgateway ontology | 短期保持 unresolved；不从代码反推；长期 owner 三选一 | 第三阶段 |

---

## 1. 当前事实（2026-10-04 只读复核）

### 1.1 八产品 authority 实测（resolver `resolve_context.py --all`）

| product | ontology | prd | code | code revision | 备注 |
|---|---|---|---|---|---|
| lnkcre | complete | complete | complete | 8e74a3b7 | configured `/opt/code/lnkcre` |
| lnkcrm | complete | complete | **present-unconfirmed** | **1d5ebb6b**（漂移，见 1.2） | configured null；observed `/opt/code/lnkcrm` |
| lnkchat | complete | complete | complete | 662123c9 | |
| lnkchatbi | complete | complete | complete | 72e96a71 | |
| lnkreport | complete | complete | complete | 86d5fefc | |
| lnkvision | complete | complete | complete | fa5050f4 | |
| lnkgateway | **unresolved** | **unresolved** | complete | 2659233a | O9/O11 事实基础 |
| lnkwebsite | not-applicable | complete | complete | 5c3f7bf7 | prd-only（owner 2026-09-27 裁定） |

### 1.2 lnkcrm observed revision 漂移（O5 暂缓的直接证据）

- 设计包 §12.1 记录（2026-10-04 早间快照）：`ad6f0c0b`（2026-10-03 18:10
  "chore(spec): archive points expiry and clearance"）
- 本次复核（2026-10-04）：`1d5ebb6b`（2026-10-04 09:18
  "feat(points): implement self-service review"）
- 结论：**observed revision 仍在变化，`/opt/code/lnkcrm` 处于活跃开发状态**，尚未形成
  稳定的产品 authority 基线。OpenSpec scope 数维持 27 个（实测确认）。
- 处置（按冻结线）：**只登记证据，不升级状态，不修改 canonical 配置，不启动 Batch 4**。

### 1.3 resolver `product.adapter_status` 字段现状（O4 依据）

- 实测：8 产品全部输出 `product.adapter_status = 'unsupported'`（缺省回落；company.yaml
  无一设置该字段），与 `product-registry.yaml` 的 lnkcre=implemented **直接矛盾**。
- 字段是单一 per-product 值，无法表达 per-consumer×per-product 语义——结构性缺陷，
  迁移废弃（O4）而非修补是正确方向。

### 1.4 capability 现状（设计包 §3，未变）

六消费方×八产品 48 格：implemented 12 / partial 15 / onboarding 5 / unsupported 9 /
not-applicable 4 / blocked 3。**「八产品可解析」≠「六 skill 已支持」**。

### 1.5 两仓 git 状态（保留其他会话修改）

- skill 仓：存在其他会话的未提交修改（消费方 SKILL.md、resolver 集成、openspec-practice
  references 等）与本包前置产物（设计包、消费方审计报告、`shared/`）。**本包不回退、
  不覆盖、不清理任何既有修改。**
- docs 仓：存在其他会话的未提交修改（lnkcre PRD 增量、reconciliation 文件、00-governance/
  等）。同样不触碰。

---

## 2. 当前冻结线（owner 批准前全部维持）

```yaml
# 文件面
adapter-capabilities.yaml: 不存在（任何 skill 目录下都不得创建）
resolver（shared/product_context）: 零修改
resolver.adapter_status 字段: 保留（只读现状，不改不删）
product-registry.yaml: 零修改
company.yaml: 零修改
30-products/**: 零修改（含 lnkcrm 全部 canonical 文档）
/opt/code/lnkcrm 及其他产品代码仓: 零修改
目标项目 OpenSpec / 代码 / 测试 / archive: 零修改

# lnkcrm 专项冻结
company.yaml code_root: null
layers.code_root: null
authority.code.status: present-unconfirmed

# 决策记录面
正式 owner decision record: 不存在（本包与表单草案均非批准记录）
git: 不提交、不推送、不 git add -A
```

若 observed revision 再次变化：只登记证据（记入本包或表单 follow_up），不升级状态，
不修改 canonical 配置，不启动 Batch 4。

---

## 3. O1-O11 逐项建议（RECOMMENDATION ONLY）

### 3.1 O1：方案 B —— 建议批准（范围限定 Batch 1）

**建议**：批准「每个业务 skill 自声明 adapter capability」的方案 B。

**落位**：`/opt/code/skill/skills/business/<skill>/references/adapter-capabilities.yaml`
（每 skill 一份；schema 依设计包附录 A，S1 定稿）。

**要求（capability 文件红线）**：

- capability 属于消费方，不是产品事实；
- 不复制产品 authority（不写 `docs_root` / `code_root` / `ontology_path` / `prd_root` /
  revision 等产品事实字段）；
- 不建立新的产品事实注册表（不触碰「company.yaml 是唯一产品台账」红线）；
- `product_id` 必须使用 company.yaml canonical ID；
- 每个 capability 状态必须带证据路径、验证时间（verified_at）、owner 和备注。

**建议批准范围**：Batch 1 —— 设计定稿（schema）+ 六消费方首版 capability 文件。

**适用消费方（6 个）**：product-prd-generator、requirement-evaluator、pricing-generator、
competitor-product-analyzer、company-intro-generator、strategy-brief-generator。

**理由**：

1. capability 属于消费方，不应成为产品事实——写在 skill 侧所有权才正确；
2. 避免继续扩张 product-registry.yaml（该文件已四重职责，设计包 §4）；
3. 不影响公共 resolver 的 authority 语义（resolver 不读 capability 文件）；
4. 每个 skill 可独立声明和维护自己的支持范围，变更与证据同 commit 原子化；
5. 能清楚区分「产品存在」（authority）与「该 skill 能否消费」（capability）——
   正是 §1.4 误读风险的解药。

**影响范围**：6 个业务 skill 各新增 1 个 `references/adapter-capabilities.yaml`（纯新增，
不接生产路径）+ 1 个只读聚合校验脚本（S5）+ SKILL.md 引用句（轻改）。docs 仓零改动。

**风险与缓解**：

- 声明与实际行为漂移 → evidence 强制指针 + verified_at + 聚合脚本与测试交叉；
- 被误读为产品事实 → schema 禁 path/revision 字段 + 聚合脚本 cross-check hard-fail；
- 回滚：单文件 git revert，无数据损失。

### 3.2 O2：48 格矩阵现状判定 —— 并入 O1 Batch 1

首版 capability 文件的内容即设计包 §3 矩阵（含 3 处 ★ 改判建议：prd-gen×lnkwebsite、
pricing×lnkgateway、company-intro×lnkgateway 改 not-applicable）。owner 批准 O1 Batch 1
即同时确认矩阵首版值。若 owner 希望单独审议矩阵，可在表单 D-O2 单独勾选，不阻塞 O1。

### 3.3 O3：方案 C 豁免 —— 条件性，B 方案下不触发

O3 仅当 owner 拒 B 选 C 时需要（明示豁免「不建第二套中心注册表」惯例 + 定文件位置与
所有权）。本包推荐 B，故 O3 不触发；表单保留占位，status 保持 pending 仅供条件性启用。

### 3.4 O4：resolver `adapter_status` 迁移 —— 建议批准（带过渡期）

**建议**：批准迁移，但**保留过渡兼容期，本阶段不删除字段**。

**迁移顺序（五步，顺序不可倒置）**：

1. 建立各消费方 capability 声明（Batch 1，依赖 O1）；
2. 迁移所有读取方（prose 与程序化引用改指 capability 文件）；
3. 增加兼容告警（resolver 对 `adapter_status` 输出 deprecation 提示或文档钉死）；
4. 停止新增 `adapter_status` 依赖（禁令入契约）；
5. owner 确认无消费方后，删除 `resolver.adapter_status`（单独批准动作）。

**理由**：字段结构性缺陷（单一 per-product 值，§1.3）已实证；但**已有调用方和测试可能
依赖它**——立即删除会破坏 resolver 测试面与潜在消费方，故必须过渡期而非一刀切。

**影响范围**：`shared/product_context`（models/resolver/tests，API 变更）+ 消费方 prose。

**风险与缓解**：迁移期双源并存（registry capability 维度 + capability 文件）→ 步骤 2
完成前 registry 维度不收敛；删除动作（步骤 5）单独批准、单独 commit，可独立 revert。

**门禁**：O1 批准**不自动**批准 O4；两者是独立决策项（可同批签署，语义独立）。

### 3.5 O5：lnkcrm code authority 晋升 —— deferred / conditional approval

**建议**：暂缓，不建议现在批准晋升。

**原因**：

- `/opt/code/lnkcrm` 仍处于活跃开发状态：observed revision 已从 `ad6f0c0b` 前进到
  `1d5ebb6b`（§1.2 实证）；
- 代码仓、OpenSpec（27 scope）和实现都存在，但 revision 仍在变化 = **还不是稳定的
  产品 authority 基线**；
- owner 尚未确认正式 authority（docs 侧三处仍声明「无代码仓」）。

**当前允许的仅是（conditional 部分）**：继续观察；记录 revision；准备晋升方案；
保持 `code_root: null`；保持 `present-unconfirmed`。

**不得修改**：company.yaml、`30-products/lnkcrm/INDEX.md`、
`30-products/lnkcrm/code/README.md`、reconciliation 台账。

**正式晋升前 owner 必答（对应设计包 §12.2 五连问）**：

1. 是否正式指定 `/opt/code/lnkcrm` 为 lnkcrm 的 code authority？
2. 若是，是否允许修改 company.yaml（`code_root: null` → `/opt/code/lnkcrm`）？
3. 生效 revision 是哪个 commit？（活跃开发中，必须钉死基线点）
4. 27 个 OpenSpec scope 是否纳入产品实现基线（参与评估/对照/回写）？
5. 是否同步更新 INDEX.md、code/README.md、reconciliation，以及哪些业务 skill adapter
   纳入验证（建议最小集：requirement-evaluator + strategy-brief-generator +
   product-prd-generator）？

**门禁**：O4 批准不自动批准 O5；O5 批准不自动批准任何业务基线（O6-O11）。

### 3.6 O6：正祥 CRM 定价 —— 暂不追认

**建议**：暂不追认为正式 lnkcrm 标准定价。可先登记为
`customer-specific / historical pricing evidence`（pricing-generator `CRM_DATA` 的归属
注记，属 Batch 3 轻动作）。

**转正式 baseline 前必须确认**：适用产品（对应 lnkcrm 还是历史 CRM 交付）；适用版本；
价格有效期；标准价格与定制价格边界；owner；是否可对外使用。

**理由**：正祥定价是单客户历史交付物，直接追认会让「历史 CRM 报价」无主顶替
「lnkcrm 产品报价基线」（跨产品借用禁令同源风险）。

### 3.7 O7：lnkchat / lnkreport / lnkvision 报价 —— 拆分三个子决策

**不得打包审批**。三个子决策：

| 子项 | 建议 | 前置问题 |
|---|---|---|
| O7-chat | **pending positioning** | lnkchat 是独立报价，还是以「AI 岗位 Skill 服务」打包售卖（跨产品编排）？定位不清前不建基线 |
| O7-report | **onboarding** | 建立独立产品功能清单与报价基线（走 pricing-basis.yaml 登记流程） |
| O7-vision | **positioning decision required** | 先确认产品定位和是否面客，再决定报价 |

**硬禁令**：三产品均**不得从 lnkcre 或其他产品复制价格**（跨产品借用禁令）。

### 3.8 O8：LnkChatBI 标准定价 —— 建议批准建设，单独批准

**建议**：批准建立独立报价基线，但落盘（写 `pricing-basis.yaml`）前必须 owner 确认。

**前置条件（4 项）**：标准功能清单来源明确；标准版/定制版边界明确；定价生效日期明确；
owner 确认 `pricing-basis.yaml` 的写入范围。

**硬禁令**：不得套用 lnkchat 或 lnkcre 的价格。

**理由**：LNKCHATBI_DATA 结构在位但标准定价未登记（env 默认 0，每次报价人工输入），
是 48 格中「结构在位、缺正式定价」的典型——补齐后 pricing×lnkchatbi 可 partial→implemented。

### 3.9 O9：lnkgateway 定位 —— 暂不作为独立面客产品

**建议**：暂定定位为**平台基础设施 / 集成网关 / 产品内部能力**。

**原因**：ontology unresolved（owner-confirmed）；PRD unresolved；当前代码存在不能证明
其独立产品定位（cross-repo-governance「代码 checkout 存在 ≠ configured authority」同源）；
无独立售卖场景证据。

**影响**：在 ontology 和 PRD 仍 unresolved 的情况下，不建立独立报价、竞品能力或公司
介绍基线（pricing×lnkgateway 与 company-intro×lnkgateway 维持现状或按 ★ 改判
not-applicable，随 O1 Batch 1 矩阵落地）。

### 3.10 O10：lnkreport / lnkvision 叙事资产 —— 拆分两个子决策

| 子项 | 建议 |
|---|---|
| O10-report | **可启动**叙事资产整理（company-intro 面的 lnkreport 产品叙事） |
| O10-vision | **先确认**产品定位、目标客户、与 lnkreport 的边界，再建设叙事资产 |

### 3.11 O11：lnkgateway ontology —— 短期保持 unresolved

**建议**：短期保持 unresolved；**不从代码反推 ontology**（owner 既有裁定维持）。

**长期方向由 owner 三选一**：

1. 独立产品 ontology；
2. 平台基础能力 ontology；
3. 集成层能力，不建立独立产品 ontology。

当前**不建议自动创建任何一种**。解除 prd-gen/competitor 的 blocked 状态的唯一路径是
本决策落地（与 O9 联动但独立签署）。

---

## 4. 推荐批准顺序与批次约定

### 4.1 批次编号约定（与设计包 §7 S 阶段的映射，避免歧义）

| 批次 | 内容 | 对应设计包阶段 | 触发决策 | 当前状态 |
|---|---|---|---|---|
| Batch 1 | schema 定稿 + 六消费方首版 capability 文件 + 聚合校验脚本 | S1+S2(+S5) | O1（含 O2 矩阵首版值） | **冻结** |
| Batch 2 | registry capability 维度收敛 + resolver `adapter_status` 迁移（过渡期五步） | S3+S4(+S6) | O4（依赖 Batch 1 完成） | **冻结** |
| Batch 3 | 各业务基线执行（O6 evidence 登记 / O7-report / O8 定价 / O10-report 叙事） | 设计包 §10/§13 | 对应子项各自批准 | **冻结** |
| Batch 4 | lnkcrm code authority 晋升实施（company.yaml/INDEX/code README/reconciliation） | 设计包 §12 | O5 正式批准（五问齐答） | **冻结** |

### 4.2 推荐三阶段

**第一阶段（owner 决策，仅签署不实施）**：

- O1 批准方案 B（范围限 Batch 1 设计 + 首版 capability 文件）；
- O4 批准 adapter_status 迁移策略（过渡期，不删字段）。

**第二阶段（实施，O1/O4 签署后启动）**：

- Batch 1：建立六个业务 skill 的 capability 声明；
- product-registry 消费方迁移设计（Batch 2 前置）；
- authority 与 capability 隔离验证（聚合脚本 cross-check）。

**第三阶段（逐项决策 + 逐项实施）**：

- O5 lnkcrm 条件性晋升（先完成 owner 五问，再 Batch 4）；
- O8 lnkchatbi 定价（前置 4 条件齐后 Batch 3 落盘）；
- O7-chat / O7-report / O7-vision 分别处理；
- O6 CRM 历史定价是否晋升；
- O9 lnkgateway 定位；
- O10-report / O10-vision；
- O11 lnkgateway ontology。

### 4.3 批准门禁（显式）

- **O1 不自动批准 O4**；
- **O4 不自动批准 O5**；
- **O5 不自动批准任何业务基线**（O6-O11 各自独立）;
- **任何一个批准只作用于决策记录中明确列出的范围**（approved_batch / approved_changes）；
- 表单中未填写的字段**不得解释为批准**。

---

## 5. Owner 必须回答的问题（汇总）

1. **O1**：是否批准方案 B + 附录 A schema + Batch 1 范围（6 消费方首版文件）？
2. **O2**（可选单独审议）：48 格矩阵首版值（含 3 处 ★ 改判）是否随 O1 确认？
3. **O4**：是否批准五步迁移（本阶段不删字段）？步骤 5（删除）是否要求再次签署？
4. **O5 五连问**：见 §3.5 —— 正式 authority？允许改 company.yaml？生效 revision？
   OpenSpec 基线纳入范围？reconciliation 更新范围与验证 adapter 集？
5. **O6**：正祥 CRM 定价的适用产品/版本/有效期/边界/owner/对外性？
6. **O7-chat**：lnkchat 独立报价还是 AI Skills 打包？
7. **O7-vision**：lnkvision 产品定位与是否面客？
8. **O8**：LnkChatBI 标准功能清单来源？标准/定制边界？生效日期？pricing-basis.yaml
   写入范围？
9. **O9**：lnkgateway 是否永不独立面客（→ not-applicable 落地）？
10. **O10-vision**：lnkvision 目标客户与 lnkreport 边界？
11. **O11**：lnkgateway ontology 长期方向三选一（独立产品 / 平台基础能力 / 不建）？
12. **通用**：决策记录转正式后的归档位置（docs `00-governance/` 或 skill 仓）由谁定？

---

## 6. 决策表单草案位置

`/opt/code/skill/references/adapter-capability-owner-decision-draft-2026-10.md`

- 文件头标记：**STATUS: DRAFT / NOT AN APPROVAL RECORD / OWNER SIGN-OFF REQUIRED**；
- 含 14 个决策块（O1、O2、O3、O4、O5、O6、O7-chat、O7-report、O7-vision、O8、O9、
  O10-report、O10-vision、O11），全部 `status: pending`；
- 允许 status 枚举：`pending | approved | rejected | deferred`；
- **未填写的字段不得解释为批准**；
- **不放入正式治理 registry**；owner 签署后按 owner 指定方式转为正式决策记录。

---

## 7. 显式声明：建议不等于批准

本文件全部内容（含 §0 速览、§3 逐项建议、§4 顺序推荐）性质为 **RECOMMENDATION ONLY**。
本轮唯一产出是两份 Markdown（本建议包 + 表单草案），不构成对 O1-O11 任何一项的批准，
不触发 Batch 1/2/3/4 任何实施动作。所有实施等待 owner 正式签署。

## 附录：本轮门禁自检（未做的事）

未创建 adapter-capabilities.yaml；未修改 resolver / adapter_status 字段 /
product-registry.yaml / company.yaml / 30-products/** / 产品代码仓 / 目标项目 OpenSpec；
未创建正式 owner decision record；未伪造批准状态；未提交、未推送、未 git add -A；
未回退或覆盖两仓其他会话的既有修改。
