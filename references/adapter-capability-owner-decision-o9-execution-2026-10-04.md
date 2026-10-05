# O9 执行记录 —— lnkgateway 预改判转定判（evidence 登记轮，status 值零变更）（2026-10-04 裁决 / 2026-10-05 执行）

```text
STATUS: COMPLETED（两份 capability 文件 lnkgateway 条目 evidence/notes 登记 O9 定判依据；
status 值 not-applicable 零变更；shared 53 tests OK 钉线零改动；pricing pytest 19 passed）
RESIDUAL: 无（O9 裁决内无遗留待授权项；可复议路径见 §6）
OWNER SIGN-OFF: RECORDED (OPC)（引用自决策记录 :38，非本文件自立）
AUTHORIZATION: references/adapter-capability-owner-decision-o9-2026-10-04.md
SCOPE: O9 only —— 不触 company.yaml / O11 冻结线 / D-O9 禁令 / shared / docs 仓；
不构成 O7-vision / O10-* / O11、删除动作、lnkreport 定价的批准
```

> **记录性质**：本文件是 O9 的执行记录，由执行会话落盘，验证结果均为本会话实测。
> 它不构成 O7-vision / O10-* / O11、任何删除动作或 lnkreport 定价的批准。

## 1. owner 决策记录核验（执行前，当前磁盘版本复核）

对象：`references/adapter-capability-owner-decision-o9-2026-10-04.md`。

| 核验项 | 要求 | 实测（文件:行） | 结果 |
|---|---|---|---|
| status | decided | `:8 status: decided` | ✅ |
| decision | not-independently-customer-facing | `:9 decision: not-independently-customer-facing（暂不独立面客——暂定平台基础设施 / 集成网关 / 内部能力；预改判转定判，可复议）` | ✅ |
| owner | OPC | `:5 owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）` | ✅ |
| OWNER SIGN-OFF | RECORDED (OPC) | `:38 OWNER SIGN-OFF: RECORDED (OPC)` | ✅ |
| 授权效力声明 | 存在 | `:39 授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署` | ✅ |
| forbidden_changes 含 status 值禁令 | 是 | `:31 改动两份 capability 文件 lnkgateway 条目的 status 值（not-applicable 保持）` | ✅ |
| approved_changes 覆盖本轮三项 | 是 | `:16-19`（两份 capability 条目 evidence 补正式裁定依据 + backlog 状态注记 + 执行记录落盘） | ✅ |

**核验结论：通过。** owner=OPC、记录齐全，按授权执行；未触发「仅当 owner 非 OPC 或记录缺失时停止」的中止条件。

## 2. 裁决内容（未扩大）

- O9 = 方案 B：lnkgateway **暂不独立面客**（平台基础设施 / 集成网关 / 内部能力）；预改判转定判，可复议。
- 本轮只把「预改判」（O2 首版矩阵 ★ 改判 not-applicable）升级为「O9 定判（2026-10-04）」的 evidence 依据——**两格 status 现值 not-applicable 保持不变**。
- 未触碰（决策记录 :25-28 unchanged）：company.yaml 产品登记身份；O11 冻结线（ontology=unresolved / ontology_entry=null / 禁跨产品 fallback）；D-O9 禁令（unresolved 期间不建 lnkgateway 独立报价/竞品/公司介绍基线）。

## 3. capability 条目前/后对比

### 3.1 pricing-generator（`skills/business/pricing-generator/references/adapter-capabilities.yaml`，lnkgateway 条目改前 :73-80 / 改后 :73-81）

| 字段 | 前 | 后 |
|---|---|---|
| status | `not-applicable`（:75） | `not-applicable`（:75）——**零变更** |
| evidence | 1 条：`"设计包 §3.3.C/§3.9：内部 AI 网关，无独立售卖场景证据"`（:77） | 2 条：原条目保留（:77）+ 追加 `"O9 decided-B（2026-10-04）：暂不独立面客，预改判转定判，可复议；引 references/adapter-capability-owner-decision-o9-2026-10-04.md"`（:78） |
| verified_at | `"2026-10-04"` | `"2026-10-04"`——零变更（shared schema 测试钉 AUDIT_DATE，本就不在授权清单） |
| owner | `opc` | `opc`——零变更 |
| notes | `"★ 改判 unsupported→not-applicable（O2 首版矩阵）；O9 定位裁决 pending——若未来裁定面客，须凭证据重评并补全套报价输入。"`（:80） | `"★ 改判 unsupported→not-applicable（O2 首版矩阵）；O9 decided-B（2026-10-04）：暂不独立面客，预改判转定判，可复议；引 references/adapter-capability-owner-decision-o9-2026-10-04.md——若未来改裁 A（面客），须凭证据重评并补全套报价输入。"`（:81） |

### 3.2 company-intro-generator（`skills/business/company-intro-generator/references/adapter-capabilities.yaml`，lnkgateway 条目改前 :67-74 / 改后 :67-75）

| 字段 | 前 | 后 |
|---|---|---|
| status | `not-applicable`（:69） | `not-applicable`（:69）——**零变更** |
| evidence | 1 条：`"设计包 §3.3.E/§3.9：无叙事资产；内部基础设施无面客叙事场景证据"`（:71） | 2 条：原条目保留（:71）+ 追加 `"O9 decided-B（2026-10-04）：暂不独立面客，预改判转定判，可复议；引 references/adapter-capability-owner-decision-o9-2026-10-04.md"`（:72） |
| verified_at | `"2026-10-04"` | `"2026-10-04"`——零变更 |
| owner | `opc` | `opc`——零变更 |
| notes | `"★ 改判 unsupported→not-applicable（O2 首版矩阵）；O9 定位裁决 pending——若未来裁定面客，须凭证据重评。"`（:74） | `"★ 改判 unsupported→not-applicable（O2 首版矩阵）；O9 decided-B（2026-10-04）：暂不独立面客，预改判转定判，可复议；引 references/adapter-capability-owner-decision-o9-2026-10-04.md——若未来改裁 A（面客），须凭证据重评。"`（:75） |

### 3.3 notes 更新方式说明（审计口径）

授权文「evidence/notes **追加** O9 定判依据」。evidence 按字面追加新条目；notes 中的
「O9 定位裁决 pending」为陈旧预判状态，与本轮「预改判**转定判**」的裁决语义直接矛盾——
按裁决核心语义原位升级为 decided-B 定判文（授权括号内原文照录），保留 ★ 改判历史句与
「若未来改裁 A 须凭证据重评」复议路径句。status / verified_at / owner / 键集均零触碰；
diff 实证见 §5.3（两份 yaml 的 diff 不含 status 行）。

## 4. 其余两处允许清单落地

- **执行记录**：本文件（允许清单 2）。
- **backlog 盘点报告末尾注记**：`references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md`
  新增 §13「状态更新（2026-10-05 O9 执行后追加）」——O9 frozen → decided-B / 定判最小注记，
  §3.7 行「当前状态 frozen」注明为落盘时快照（允许清单 3，沿用 §10-§12 惯例）。

## 5. 验证实测（本会话）

### 5.1 钉线与测试（零改动即绿）

```bash
cd /opt/code/skill/shared/product_context && uv run python -m unittest discover -s tests
# Ran 53 tests ... OK（钉线零改动；矩阵 not-applicable 分布 7 不变）

cd /opt/code/skill/skills/business/pricing-generator && uv run pytest -q
# 19 passed（含 test_lnkreport_data.py lnkgateway=not-applicable 钉值）

cd /opt/code/skill && bash references/scripts/check_docs_consistency.sh
# FAIL: 0 / WARN: 0 / PASS: 33 → RESULT: PASS
```

### 5.2 yaml.safe_load 复核（两格仍为 not-applicable）

```text
skills/business/pricing-generator/references/adapter-capabilities.yaml
  -> lnkgateway: status='not-applicable', evidence=2 条, verified_at='2026-10-04', owner='opc',
     keys=['consumer_id', 'evidence', 'notes', 'owner', 'product_id', 'status', 'verified_at']
skills/business/company-intro-generator/references/adapter-capabilities.yaml
  -> lnkgateway: status='not-applicable', evidence=2 条, verified_at='2026-10-04', owner='opc',
     keys=['consumer_id', 'evidence', 'notes', 'owner', 'product_id', 'status', 'verified_at']
```

（键集与 shared schema 测试 REQUIRED_UNIT_KEYS 逐键一致——无新增键。）

### 5.3 status 零变更实证

- 两份 yaml 的 `git diff` 增量行经 `grep -E '^[+-].*status'` 机械过滤：**零命中**（rc=1）；
  `status: not-applicable` 仅以上下文行出现（无 +/- 前缀）；
- 每文件恰 1 个 hunk，全部落在 lnkgateway 条目内（evidence +1 行、notes 行替换）；
  同文件其余 7 个产品条目零改动。

### 5.4 git 面实测

```text
git diff --check   # 无输出，rc=0
git status --short
 M references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md
 M skills/business/company-intro-generator/references/adapter-capabilities.yaml
 M skills/business/pricing-generator/references/adapter-capabilities.yaml
?? references/adapter-capability-owner-decision-o9-2026-10-04.md      # 执行前已存在的决策记录，非本轮创建
?? references/adapter-capability-owner-decision-o9-execution-2026-10-04.md  # 允许清单 2
git diff --name-only   # 恰为上述 3 个 M 文件
```

## 6. 冻结面确认（本轮未触碰、维持冻结）

- **status 值**：两格 not-applicable 保持；shared 钉线测试 / resolver / registry / company.yaml /
  30-products/** / docs 仓：零改动。
- **未建任何 lnkgateway 面客基线**（D-O9 禁令继续有效：报价/竞品/公司介绍基线均未建立）。
- **O11 冻结线**：ontology=unresolved / ontology_entry=null / 禁跨产品 fallback，未触碰。
- **仍冻结**：O7-vision / O10-* / O11、删除动作、lnkreport 定价（挂起）。
- 未执行 git add / commit / push（OPC 随后统一安排提交批）；未回退/覆盖/清理任何既有未提交修改。

## 7. 复议路径（决策记录 :21-23、:41，登记备查）

本裁决为「暂不」而非「永不」。OPC 可改裁 A（未来面客：回改两格 not-applicable 值 + 钉线同批 +
重建叙事/报价输入清单，另落记录）或 C（永不面客落死）；届时另落记录。

## 8. 结论

- **O9 完成（decided-B 落地）**：预改判转定判，两份 capability 文件 lnkgateway 条目 evidence/notes
  登记定判依据；status 值与 O11 冻结线零变动；钉线测试零改动即绿（shared 53 OK / pricing 19 passed /
  consistency 0/0/33）。
- 其余项维持冻结（O7-vision / O10-* / O11、删除动作、lnkreport 定价）；未提交、未推送。
