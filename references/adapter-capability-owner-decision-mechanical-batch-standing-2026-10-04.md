# 机械类 registry 迁移阻塞项一次性批量放行 Standing Authorization（2026-10-04）

```text
STATUS: APPROVED
OWNER SIGN-OFF: NOT RECORDED
AUTHORIZATION TYPE: session_consent（用户会话授权）
SCOPE: B4、B6、B7 only（机械类 registry 迁移阻塞项一次性批量放行）
```

> **记录性质（必读）**：本文件由执行会话按用户授权提示词落盘，登记的是**用户在本轮
> 会话中明确给出的「一次性批量放行」授权**（会话同意）。它**不是**、也**不得被引用为**
> 一份独立签署的 owner 批准记录——与 B1/B2/B5/B3/lnkcrm-freeze-reconcile 执行记录族
> 同口径：owner 身份依据本仓治理约定（AGENTS.md 一人公司，owner = opc），但独立 owner
> 签署记录不存在，故 `OWNER SIGN-OFF: NOT RECORDED`。除非发现真实、可引用的独立签署
> 证据，本状态不得改写。

## 1. 登记字段

```yaml
decision_id: MECH-BATCH-STANDING
decision_date: "2026-10-04"
record_date: "2026-10-04"
owner: "opc"
status: approved
authorization_type: session_consent
scope: "B4、B6、B7 机械类 registry 迁移阻塞项的一次性批量放行"
covered_items:
  - B4
  - B6
  - B7
owner_signoff: not_recorded
authorization_source: |
  本轮用户会话明确授权提示词（含「一次性批量放行」定义、standing authorization
  落盘要求、B4/B6/B7 逐项允许/禁止边界、独立状态记录要求、验证与最终报告格式）。
  提示词明文：「除非发现真实、可引用的独立签署证据，否则必须保持
  OWNER SIGN-OFF: NOT RECORDED」。
```

## 2. 授权效果（必须整段成立）

- 本授权**免除 B4/B6/B7 之间逐项重新请求用户触发口令**——三个 item 在本轮会话内
  依既定边界连续执行，不需中间再次请示。
- 本授权**不免除**每个 item 的**范围核对、工作区检查、测试、执行记录和审计回写**——
  每个 item 仍独立过门禁、独立验证、独立记录，状态互不覆盖。
- **B3 已单独完成**（2026-10-04 另行授权，见
  `references/adapter-capability-owner-decision-b3-execution-2026-10-04.md`），
  **不纳入本次 standing authorization**，本轮不重复执行。
- **B4/B6/B7 完成不构成 product-registry.yaml 删除批准**（registry 删除 = 独立
  owner 批准动作，阻塞项全部解除亦不自动触发）。
- **B4/B6/B7 完成不构成 adapter_status 删除批准**（O4 字段级实际删除仍冻结）。
- **O4 字段删除、O5 其他子项、O6-O11 仍需独立授权**，本轮全部不执行。
- **任一 item 触碰下方排除范围时，立即停止该 item**，记录 stopped-out-of-scope，
  不得自行扩权，不影响其余不重叠 item 按各自边界继续。

## 3. 排除范围（硬边界，任一命中即停）

- 删除 product-registry.yaml；
- 删除、重命名或修改 product-registry.yaml 字段（YAML 数据区禁改）；
- 修改 product-registry.yaml YAML 数据区；
- 删除 adapter_status；
- 修改 resolver 生产逻辑（`shared/product_context/**` 生产代码）；
- 修改 company.yaml；
- 修改 30-products/**（B7 目标文件除外——仅限授权清单内两文件的指定段落）；
- 修改产品代码仓；
- 执行 O4 字段级实际删除；
- 执行 O5 其他子项；
- 执行 O6-O11；
- 任何不可逆或破坏性动作（含回退/覆盖/清理既有未提交修改、git add -A）。

## 4. 工作区纪律（对既有未提交修改）

当前两仓工作区存在未确认归属的既有未提交修改。本轮执行必须：保留全部既有修改、
不回退、不覆盖、不清理、不使用整文件重写、只应用最小补丁、不使用 git add -A、
不提交、不推送。

## 5. 执行回写要求

- B4/B6/B7 各自独立执行记录：
  - `references/adapter-capability-owner-decision-b4-execution-2026-10-04.md`
  - `references/adapter-capability-owner-decision-b6-execution-2026-10-04.md`
  - `references/adapter-capability-owner-decision-b7-execution-2026-10-04.md`
- `references/product-registry-迁移审计-2026-10-04.md` §4 追加三个最小状态注记
  （授权来源 = MECH-BATCH-STANDING 用户会话授权；独立 owner 签署是否存在；实际修改
  文件；验证结果；未触碰的冻结范围；是否完成或仍阻塞）。
- 仅当对应 item 的实际修改和验证均完成时，才允许在审计注记中标记该 item 已解除。

## 6. 防误引

| 命题 | 状态 |
|---|---|
| 用户在本轮会话中明确给出 B4/B6/B7 一次性批量放行授权（含逐项边界） | 成立（本记录即其落盘） |
| 存在独立签署的 owner 批准记录（verbatim 签署块 / SIGN-OFF: RECORDED） | 不成立，不得声称 |

后续引用只能表述为「B4/B6/B7 经 MECH-BATCH-STANDING 用户会话授权执行（2026-10-04，
见本记录）」，不得表述为「经 owner 独立签署批准」。本授权完成不构成 registry 删除、
adapter_status 删除、O4 全部、O5 全部或 O6-O11 的批准。
