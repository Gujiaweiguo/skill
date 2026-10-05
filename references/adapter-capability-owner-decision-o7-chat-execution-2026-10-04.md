# O7-chat 执行记录 —— lnkchat 随 AI 岗位 Skill 打包售卖不单列（unsupported→not-applicable）（2026-10-04 裁决 / 2026-10-05 执行）

```text
STATUS: COMPLETED（pricing capability lnkchat 条目 status unsupported→not-applicable + evidence/notes
更新；shared 钉线矩阵格与分布同批（unsupported 5→4 / not-applicable 7→8）+ pricing 本地八产品
全景钉同批；shared 53 tests OK；pricing pytest 19 passed；consistency 0/0/33）
RESIDUAL: 无（O7-chat 裁决内无遗留待授权项；改裁「独立报价」路径见 §7）
OWNER SIGN-OFF: RECORDED (OPC)（引用自决策记录 :40，非本文件自立）
AUTHORIZATION: references/adapter-capability-owner-decision-o7-chat-2026-10-04.md
SCOPE: O7-chat only —— 不触 company.yaml / resolver / 30-products/** / registry / docs 仓 /
pricing-basis.yaml / AI 岗位 Skill 套餐数据 / 其他产品条目；不构成 O7-vision / O10-* / O11、
删除动作、lnkreport 定价的批准
```

> **记录性质**：本文件是 O7-chat 的执行记录，由执行会话落盘，验证结果均为本会话实测。
> 它不构成 O7-vision / O10-* / O11、任何删除动作或 lnkreport 定价的批准。

## 1. owner 决策记录核验（执行前，当前磁盘版本复核）

对象：`references/adapter-capability-owner-decision-o7-chat-2026-10-04.md`。

| 核验项 | 要求 | 实测（文件:行） | 结果 |
|---|---|---|---|
| status | decided | `:8 status: decided` | ✅ |
| decision | bundled-not-listed | `:9 decision: bundled-not-listed（lnkchat 随 AI 岗位 Skill 服务打包售卖，不建独立产品报价，不在报价单单列）` | ✅ |
| owner | OPC | `:5 owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）` | ✅ |
| OWNER SIGN-OFF | RECORDED (OPC) | `:40 OWNER SIGN-OFF: RECORDED (OPC)` | ✅ |
| 授权效力声明 | 存在 | `:41-42 授权效力声明 / 身份依据` | ✅ |
| forbidden_changes 含独立报价基线禁令 | 是 | `:31 建立 lnkchat 独立报价基线 / 数据结构（本轮裁决即否决该路线）`、`:32 从 lnkcre 或其他产品复制价格`、`:33 写 pricing-basis.yaml`、`:34 改 AI 岗位 Skill 套餐数据 / 其他产品 capability 条目` | ✅ |
| approved_changes 覆盖本轮四项 | 是 | `:16-19 status 值变更 + evidence/notes 注记`、`:20-21 shared 钉线同批`、`:22 backlog 状态注记`、`:23 执行记录落盘` | ✅ |
| 边界声明 | 存在 | `:44 本记录仅覆盖 O7-chat；不构成 O7-vision / O10-* / O11、删除动作或 lnkreport 定价的批准` | ✅ |

**核验结论：通过。** 按 approved_changes 执行；核验失败即停止的中止条件未触发。

## 2. 裁决内容（未扩大）

- O7-chat = **bundled-not-listed**：lnkchat 随 AI 岗位 Skill 服务打包售卖，不建独立产品报价，
  不在报价单单列。
- 打包报价落点（决策记录 :17-19 指定，本轮只读取证，零改动）：
  - `generate_quote.py` AI 岗位 Skill 产品线：`AI_POSITION_SKILLS`（:529-542，6 岗位）+
    `build_ai_data(positions)`（:558-599；2 岗起卖、首年 positions × 10,000、次年固定 20,000），
    `product_name: "LnkAgent AI岗位Skill增强服务"`（:576）；
  - 素材模板 `materials/references/报价模板_AI岗位Skill_SAAS.md`（docs 仓，实测存在 5,726 字节，
    只读不动）。
- 未触碰（决策记录 :25-28 unchanged）：lnkchat 在 company.yaml 产品台账身份；AI 岗位 Skill 套餐
  现有报价结构；resolver / company.yaml / 30-products/** / registry / docs 仓。

## 3. 落地前/后对比

### 3.1 pricing capability lnkchat 条目（`skills/business/pricing-generator/references/adapter-capabilities.yaml`，改前 :38-45 / 改后 :38-47）

| 字段 | 前 | 后 |
|---|---|---|
| status | `unsupported`（:40） | `not-applicable`（:40）——**status 值变更（本裁决授权的权威动作）** |
| evidence | 1 条：`"设计包 §3.3.C：generate_quote.py 无 lnkchat 报价数据；功能清单未接入"`（:41） | 3 条：原条目保留（:42）+ 追加 O7-chat 定判条目（:43）+ 打包落点条目（:44，含 product_name「LnkAgent AI岗位Skill增强服务」与模板相对路径） |
| verified_at | `"2026-10-04"` | `"2026-10-04"`——零变更（shared schema 测试钉 AUDIT_DATE） |
| owner | `opc` | `opc`——零变更 |
| notes | `"缺定价资料（missing-pricing）；当前以「AI 岗位 Skill 服务」打包售卖，是否单列产品报价待 O7-chat（pending）。"` | `"O7-chat 已定判（2026-10-04 decided / bundled-not-listed）：打包售卖不单列。打包报价走 AI 岗位 Skill 套餐数据/模板，不建 lnkchat 独立报价数据结构（forbidden——独立报价路线被本轮裁决否决）；OPC 可改裁「独立报价」路线（届时另落记录，走 LNKCHATBI 式独立数据结构 + 定价流程）。"` |

notes 更新口径：原「待 O7-chat（pending）」为陈旧预判状态，与「已定判」语义直接矛盾，按裁决核心
语义原位升级（沿用 O9 执行记录 §3.3 审计口径）；status / verified_at / owner / 键集均为授权内变更或零触碰。

### 3.2 shared 钉线（`shared/product_context/tests/test_adapter_capabilities_schema.py`）

| 钉点 | 前 | 后 |
|---|---|---|
| EXPECTED_MATRIX pricing-generator×lnkchat | `"unsupported"`（:118） | `"not-applicable"`（:122） |
| EXPECTED_DISTRIBUTION unsupported | `5`（:161） | `4`（:165） |
| EXPECTED_DISTRIBUTION not-applicable | `7`（:162） | `8`（:166） |
| 修订注释 | O2★ / O5-Q5 / O8 三条 | +O7-chat 第四条（:94-97，引决策记录） |

分布总和 48 不变（implemented 14 / partial 13 / onboarding 6 / unsupported 4 / not-applicable 8 / blocked 3）。

### 3.3 pricing 本地八产品全景钉（`skills/business/pricing-generator/tests/test_lnkreport_data.py`）

| 钉点 | 前 | 后 |
|---|---|---|
| `test_capability_other_products_untouched` 全景 dict lnkchat | `"unsupported"`（:221） | `"not-applicable"`（:224） |
| 该测试 docstring | 仅 O8 修订注记 | + O7-chat 同批修订注记（引决策记录；注明 shared 钉线同 commit） |

**同批必要性说明（审计口径）**：该测试加载真实 capability yaml 钉八产品全景，且该文件 :186 段注释
明文契约「capability 条目（与 yaml 修改同批原子化）」；O8 先例（backlog §11）同样把「pricing 本地
八产品全景钉」纳入钉线同批。本轮验证门「pricing pytest 19 passed」在不更新本地钉时机械不可满足，
故本地钉属 2b「钉线同批」的必要组成，非允许清单外扩。

## 4. 其余允许清单落地

- **执行记录**：本文件（允许清单 c）。
- **backlog 盘点报告末尾注记**：`references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md`
  新增 §14「状态更新（2026-10-05 O7-chat 执行后追加）」——O7-chat frozen → decided-B / bundled
  最小注记，§3.3 行「当前状态 frozen」注明为落盘时快照（允许清单 d，沿用 §10-§13 惯例）。

## 5. 验证实测（本会话）

### 5.1 钉线与测试

```bash
cd /opt/code/skill/shared/product_context && uv run pytest -q
# 53 passed（钉线更新后矩阵格/分布与 yaml 实测一致）

cd /opt/code/skill/skills/business/pricing-generator && uv run pytest -q
# 19 passed（含 test_capability_other_products_untouched 八产品全景钉新值）

cd /opt/code/skill && bash references/scripts/check_docs_consistency.sh
# FAIL: 0 / WARN: 0 / PASS: 33 → RESULT: PASS
```

### 5.2 git 面实测

```text
git diff --check   # 无输出，rc=0
git status --porcelain
 M references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md
 M shared/product_context/tests/test_adapter_capabilities_schema.py
 M skills/business/pricing-generator/references/adapter-capabilities.yaml
 M skills/business/pricing-generator/tests/test_lnkreport_data.py
?? references/adapter-capability-owner-decision-o7-chat-2026-10-04.md        # 决策记录（Phase 1 前已存在）
?? references/adapter-capability-owner-decision-o7-chat-execution-2026-10-04.md  # 本文件
```

增量恰为允许清单 a（yaml）/ b（shared 钉线 + 本地钉）/ c（本文件）/ d（backlog）+ Phase 1 后既存的
o7-chat 决策记录；允许清单外零改动。

### 5.3 允许清单外零改动实证

- pricing yaml 同文件其余 7 个产品条目零改动（diff 单 hunk 落在 lnkchat 条目内）；
- company-intro-generator / 其他四个 consumer 的 capability 文件零改动（不在 git status）；
- generate_quote.py / pricing-basis.yaml（不存在）/ resolver / company.yaml / 30-products/** /
  registry / docs 仓：零改动（不在 git status）。

## 6. 冻结面确认（本轮未触碰、维持冻结）

- **未建任何 lnkchat 独立报价基线/数据结构**（forbidden :31——裁决即否决该路线；无 LNKCHAT 式
  新数据结构、无 pricing-basis.yaml 写入）。
- **AI 岗位 Skill 套餐数据与其他产品条目**：零改动（forbidden :34；generate_quote.py 只读取证）。
- **未从 lnkcre 或其他产品复制价格**（forbidden :32；零价格数值动作）。
- **resolver / company.yaml / 30-products/** / registry / docs 仓**：零改动（unchanged :28）。
- **仍冻结**：O7-vision / O10-* / O11、删除动作、lnkreport 定价（挂起）。
- 未执行 git add / commit / push（Phase 2 不 commit；OPC 批准了提交 Phase 1 批，未批准推送）。

## 7. 复议路径（决策记录 :36，登记备查）

OPC 可改裁「独立报价」路线（届时另落记录，走 LNKCHATBI 式独立数据结构 + 定价流程——含
pricing-basis.yaml 登记与 capability 升级，status 值回改 + shared/本地钉线同批）。

## 8. 结论

- **O7-chat 完成（bundled-not-listed 落地）**：pricing capability lnkchat unsupported→not-applicable，
  evidence/notes 登记定判依据与打包落点；shared 钉线（矩阵格 + 分布 unsupported 5→4 /
  not-applicable 7→8）与 pricing 本地八产品全景钉同批；shared 53 OK / pricing 19 passed /
  consistency 0/0/33。
- 其余项维持冻结（O7-vision / O10-* / O11、删除动作、lnkreport 定价）；未提交（Phase 2）、未推送。
