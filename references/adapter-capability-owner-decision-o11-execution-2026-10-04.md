# O11 执行记录 —— lnkgateway capability 解除 blocked（not-applicable 替代路径）+ 机制取证 + docs 措辞提案（2026-10-04 裁决 / 2026-10-05 执行）

```text
STATUS: COMPLETED（两格 capability blocked→not-applicable + evidence/notes 更新；shared 钉线
矩阵两格 + 分布两项同批（blocked 3→1 / not-applicable 8→10）；机制取证完成：resolver 的
ontology not-applicable 文本触发词 = prd-only 子串，「不建」类措辞不进入解析面（探针实证）；
docs 措辞提案就绪待 orchestrator 落盘；resolver/门禁/registry/company.yaml 零触碰）
RESIDUAL: docs 仓两文件注记待 orchestrator 会话按 §3 提案落盘；若未来要求 authority 层翻
not-applicable，需 Batch-2 门禁联动（§4.3，本轮不执行）
OWNER SIGN-OFF: RECORDED (OPC)（引用自决策记录 :42，非本文件自立）
AUTHORIZATION: references/adapter-capability-owner-decision-o11-2026-10-04.md
SCOPE: O11 Batch-1 only —— 不建 ontology 任何内容；不动 resolver 生产代码；PRD 层不处置
（仍 unresolved）；不执行 O10-*、删除动作、定价；不 git add -A、不提交、不推送
```

> **记录性质**：本文件是 O11 Batch-1 的执行记录，由执行会话落盘，验证结果均为本会话实测。
> 它不构成 O10-*、删除动作或任何定价事项的批准。

## 1. owner 决策记录核验（执行前，当前磁盘版本复核）

对象：`references/adapter-capability-owner-decision-o11-2026-10-04.md`。

| 核验项 | 要求 | 实测（文件:行） | 结果 |
|---|---|---|---|
| status | decided | `:9 status: decided` | ✅ |
| decision | no-standalone-ontology | `:10-11 decision: no-standalone-ontology（lnkgateway 定位集成层能力/平台基础设施，不建独立 ontology；prd-gen/competitor 两格 blocked 经 not-applicable 替代路径解除）` | ✅ |
| owner | OPC | `:5 owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）` | ✅ |
| OWNER SIGN-OFF | RECORDED (OPC) | `:42 OWNER SIGN-OFF: RECORDED (OPC)` | ✅ |
| 授权效力声明 | 存在 | `:43 授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署` | ✅ |
| hard_prohibitions | 含「不从网关代码反推」+「不创建任何 ontology」 | `:31 不得从网关代码反推 ontology`；`:32 不得未经批准创建任何一种 ontology（①② 路线本轮明确不启动）` | ✅ |
| approved_changes 含两格 capability | 是 | `:18-20 prd-gen / competitor 两份 capability 文件 lnkgateway 条目：blocked → not-applicable + evidence/notes` | ✅ |
| approved_changes 含钉线同批 | 是 | `:21-22 shared schema 钉线同批：EXPECTED_MATRIX 两格 + EXPECTED_DISTRIBUTION（blocked −2 / not-applicable +2），报前后值` | ✅ |
| docs 侧前置条件 | 取证后按提案执行 | `:23-27 docs 侧登记注记……待 skill 取证 lnkwebsite not-applicable 先例机制后按提案执行……若取证证明该注记会翻转 resolver 的 ontology authority 状态（unresolved → not-applicable），则门禁冻结线断言须与 docs 变更原子化联动（另行同批），本轮先停止报告` | ✅ |
| forbidden 含 PRD 层不处置 | 是 | `:37 prd 层处置（lnkgateway PRD 仍 unresolved，不在本记录范围）` | ✅ |
| 边界声明 | 存在 | `:47 本记录仅覆盖 O11 裁决③；不构成 O10-*、删除动作或任何定价事项的批准` | ✅ |

**核验结论：通过。** 按批准的变更执行；核验失败即停止的中止条件未触发。

## 2. 常规取证（盘点）

- **§3.10（backlog inventory :226-242）**：O11 三选一登记在案；验证要求 :237「若裁决③：capability
  文件两份 blocked→not-applicable + schema 测试」——本批执行项与该要求一致；影响面 :235 明示两格
  现值 **blocked**（迁移审计 §3:105）与「解除 blocked 的唯一路径是本决策落地」（设计包 :419）。
- **D-O11（表单草案 :331-351）**：三选一注释（:342）与禁令（:346-347 从网关代码反推 / 未经批准自动
  创建）与决策记录一致；follow_up :350「解除 prd-gen/competitor blocked 的唯一路径是本决策落地」——
  本批即为该落地。
- **两格 capability 现值（改前实测）**：
  - `skills/business/product-prd-generator/references/adapter-capabilities.yaml`：lnkgateway 单元
    `status: blocked`（evidence 两 条：迁移审计 §3 O11 pending 阻塞 + _paths.py 显式拒绝回落）。
  - `skills/business/competitor-product-analyzer/references/adapter-capabilities.yaml`：lnkgateway
    单元 `status: blocked`（evidence 一条：SKILL.md S1.2/S1.3 降级契约）。
- **对照组（本批不改）**：`requirement-evaluator` 的 lnkgateway 单元维持 `blocked`——其阻塞根因是
  **产品层 PRD unresolved**（无功能清单基线），O11 只裁 ontology 长期方向、明示 PRD 层不处置，故该格
  不在本批解除范围内。

## 3. 机制调查（本批核心增值；探针实证，只读）

### 3.1 (a) resolver 如何得出 lnkwebsite ontology=not-applicable

**解析链（shared/product_context/resolver.py）**：

1. `resolve_product` 读取 `30-products/<pid>/INDEX.md` 全文（`index_text`）与
   `30-products/<pid>/ontology/README.md` 全文（`ontology_text`）。
2. **`resolver.py:398-399`（最高优先级判定）**：
   `if "prd-only" in (index_text or "").lower() or "prd-only" in (ontology_text or "").lower(): ontology_status = "not-applicable"`
3. 其后才是 `_declared_authority`（README 表格指针行，`:355`）与 `_pointer_from_cell` 的
   mode/entry 判定（`:400-409`）。

**lnkwebsite 先例的精确触发面（实测读文件）**：

- `30-products/lnkwebsite/INDEX.md` 三层入口表：「`| 本体 | ontology/（见 README） | 不建（owner 裁定
  prd-only，2026-09-27） |`」——**「不建」本身是惰性文本，真正触发 not-applicable 的是括号内的
  `prd-only` 子串**（该词在 INDEX 另一处「已裁决事项：不建 ontology 层，prd-only」再次出现）。
- `30-products/lnkwebsite/ontology/README.md` 指针行「`| canonical 本体 | 未建立（建成后落本目录） |`」
  本身走 absent 前缀（`未建立` → mode=unresolved），**若无 INDEX 的 prd-only 子串，该产品会解析为
  unresolved 而非 not-applicable**。

**结论（token 家族）**：「不建」类单元 → not-applicable 的假设**不成立**。resolver 的 ontology
not-applicable 文本触发词家族 = **唯一成员：字面 ASCII 子串 `prd-only`**（大小写不敏感，
INDEX.md **或** ontology/README.md **任一全文**命中即翻转，先于一切 mode/entry 判定）。
lnkwebsite 的「不建」措辞只是人类可读叙事，不进入解析面。

### 3.2 (b) 「不建（owner 裁定…）」类措辞是否会翻转 lnkgateway 输出

**逐 cell 机制推演（`_pointer_from_cell` :176-198）**：cell `不建（owner 裁定 O11-③…）` 不以
`无`/`未建立`/`unresolved` 任一 absent 前缀开头 → 无 backtick/链接/目录 marker → mode=`""`
（无声明语义）→ entry 维持 None → `:404-405 ontology_entry is None` 分支 →
`ontology_status = "unresolved" if ontology_root.exists() else "not-found"` → ontology 目录存在
（README 在内）→ **unresolved**。

**探针实证矩阵**（脚本见附录 A；temp 基座 fixture，label cell 均保留）：

| 变体 | 措辞要点 | ontology | entry | 判定 |
|---|---|---|---|---|
| live lnkgateway（真实基座） | 现状 `无（unresolved）` | unresolved | null | 基线 = 门禁冻结线一致 |
| live lnkwebsite（真实基座） | INDEX 含 prd-only 子串 | not-applicable | null | 先例复现 |
| V0 fixture 现状逐字拷贝 | — | unresolved | null | fixture 保真度 ✅ |
| **V1 提案（无前缀 cell + 裁决说明段）** | §3.3 全量提案文本 | **unresolved** | **null** | **不翻 ✅** |
| **V1b 授权(b)原始假设（不建 前缀 cell）** | 仅 cell 改「不建（owner 裁定…）」 | **unresolved** | **null** | **不翻 ✅** |
| V2 负对照（cell 值含 prd-only 子串） | `不建（owner 裁定 prd-only，2026-10-04）` | **not-applicable** | null | **翻转实证** |
| V3 负对照（cell 值含 本目录 marker） | `不建（owner 裁定 O11-③，不落本目录）` | **complete** | **ontology 目录** | 第二危害实证 |

**结论（b）：不会翻。** 两种措辞（`无` 前缀保留 / `不建` 前缀）输出均为 unresolved/entry=null，
与门禁冻结线一致。`无` 前缀变体（V1，本提案采用）严格更稳：unresolved 由**显式缺席声明**得出，
不依赖 ontology 目录存在性；`不建` 前缀变体（V1b）走「无声明语义 + 目录存在」路径，若日后目录
被移走会退化为 not-found。

### 3.3 docs 措辞提案（逐行 旧→新；供 orchestrator 在 docs 仓执行）

**措辞硬约束（探针实证，违反即破坏门禁冻结线）**：

1. 两文件**全文**（含 prose/注释/表格）不得出现子串 `prd-only`（V2 实证：任一文件命中 → authority
   翻 not-applicable → 门禁 `unresolved` 断言 FAIL）。**注意**：机制说明文字本身也不能带该 token——
   「解释触发词」的元讨论写进 docs 文件同样触发（检查是全文子串级，不区分语义层级）。
2. `canonical ontology` 指针行**值 cell** 不得含 `本目录` / `已建立`（V3 实证：directory mode →
   complete + entry=ontology 目录 → 门禁两条断言双 FAIL）、不得含 backtick 路径或 markdown 链接
   （file mode → entry 解析；代码路径 `:187-195` 静态可证）。
3. 保留 `canonical ontology` label cell 原样（label 丢失会使声明行失效，缺席语义降级为目录存在性
   推断）。

**File A：`/opt/code/docs/lanlnk/30-products/lnkgateway/ontology/README.md`**

改动 1（权威指针表）：

```diff
- | canonical ontology | 无（unresolved） |
+ | canonical ontology | 无（owner 裁定 O11-③，2026-10-04：集成层能力不建独立 ontology） |
```

改动 2（指针表下方说明段）：

```diff
- 不从网关代码反推本体（INDEX 当前权威规则）。下一步：产品启动时由 owner 确认 ontology 来源。
+ 不从网关代码反推本体（INDEX 当前权威规则；owner 既有明令维持）。ontology 长期方向已裁决
+ （owner O11-③，2026-10-04）：lnkgateway 定位集成层能力/平台基础设施，不建独立 ontology；
+ capability 层已在 skill 仓按 not-applicable 收口（owner 决策记录 O11），docs 侧 authority
+ 登记维持 unresolved 语义冻结（resolver 的 not-applicable 文本触发词语义不适用于本产品，
+ 机制说明见 skill 仓 O11 执行记录）。PRD 层不在 O11 处置范围（仍 unresolved）。
```

**File B：`/opt/code/docs/lanlnk/30-products/lnkgateway/INDEX.md`**

改动 3（三层入口表 本体 行）：

```diff
- | 本体 | `unresolved` | no docs ontology candidate confirmed |
+ | 本体 | 不建（见 ontology/README） | owner O11-③（2026-10-04）：集成层能力不建独立 ontology；authority 登记维持 unresolved 冻结 |
```

改动 4（当前权威规则第二条 bullet 拆分）：

```diff
- - docs ontology/PRD 路径保持 unresolved，待产品负责人确认。
+ - ontology 长期方向已裁决（owner O11-③，2026-10-04）：lnkgateway 定位集成层能力/平台基础设施，
+   不建独立 ontology；resolver authority 登记维持 unresolved 冻结（capability 层在 skill 仓按
+   not-applicable 收口）。
+ - docs PRD 路径保持 unresolved，待产品负责人确认（O11 不处置 PRD 层）。
```

（「未来生成落位规则」节不动——其「canonical 落本目录」在 bullet 内、无表格管道，不在
`_table_cell` 解析面，探针 V1 全量文本已含原段落并实证不翻。）

**提案验证**：以上四行改动 = 探针 V1/V1_INDEX 的**逐字节构成来源**（token 自检：两文件均无
prd-only 子串；V1 实测 unresolved/null 不翻）。docs 侧落盘后建议复跑本探针做落地验证。

### 3.4 (c)/(d) 门禁联动判定

- **(d) 成立（本批采信）**：注记不进入解析面——探针实证 V1/V1b 均不翻，docs 侧仅加说明行，
  门禁（`test_adapter_status_migration_gate.py`）**零改动**，冻结线断言
  `:61 lnkgateway: {"ontology": "unresolved"}` 与 `:250-260`（unresolved + entry=null）维持原样。
  本批验证节中门禁全绿本身即「capability not-applicable 不影响 authority 冻结线」的实证。
- **(c) 备案不启用**：若未来措辞/裁决要求 authority 层也翻 not-applicable，则必须 Batch-2 原子化：
  docs 单元写入触发词（或 resolver 扩 not-applicable token 家族——生产代码改动，需独立授权）**与**
  门禁 `FREEZE_LINES["lnkgateway"]` + `:250-260` 断言同 commit 更新。本轮按决策记录 :25-27 口径
  先停止报告、不执行。

## 4. 本批变更（skill 仓，允许清单内）

### 4.1 两格 capability（blocked → not-applicable）

| 消费方 × 产品 | 前 | 后 | evidence/notes 要点 |
|---|---|---|---|
| product-prd-generator × lnkgateway | **blocked** | **not-applicable** | O11-③ 定判引决策记录；O9 同口径引用；_paths.py 拒绝回落保持；替代路径=not-applicable 登记（非 authority 翻转）；PRD 层不处置；改裁 ①/② 须另落记录 |
| competitor-product-analyzer × lnkgateway | **blocked** | **not-applicable** | O11-③ 定判引决策记录；O9 同口径引用；S1.2/S1.3 降级契约保留为防御性约束；术语归一无对照目标（不从代码反推维持）；改裁 ①/② 须另落记录 |
| requirement-evaluator × lnkgateway | blocked | **blocked（不动）** | 阻塞根因=产品层 PRD unresolved，O11 不处置 PRD 层 |

### 4.2 shared 钉线（`shared/product_context/tests/test_adapter_capabilities_schema.py`）

| 钉线项 | 前值 | 后值 |
|---|---|---|
| EXPECTED_MATRIX[product-prd-generator][lnkgateway] | `"blocked"` | `"not-applicable"` |
| EXPECTED_MATRIX[competitor-product-analyzer][lnkgateway] | `"blocked"` | `"not-applicable"` |
| EXPECTED_DISTRIBUTION["not-applicable"] | 8 | **10**（+2） |
| EXPECTED_DISTRIBUTION["blocked"] | 3 | **1**（−2） |

EXPECTED_MATRIX 上方追加 O11 修订注释（沿 O2/O5-Q5/O8/O7-chat/O7-vision 五代同款格式）。
分布合计不变（48 格）。

### 4.3 新增文件与追加

- 本执行记录：`references/adapter-capability-owner-decision-o11-execution-2026-10-04.md`（本文件）。
- backlog 末尾追加 §16 状态注记：O11 frozen → decided-③ / Batch-1 landed。

## 5. 验证（本会话实测）

| 命令 | 结果 |
|---|---|
| `cd shared/product_context && uv run python -m unittest discover -s tests` | **OK（53 tests，0 failures）**——含 schema 矩阵/分布新钉线 + 门禁 lnkgateway 冻结线（unresolved/entry=null）零改动全绿 |
| `cd skills/business/product-prd-generator && uv run pytest -q` | **169 passed, 3 skipped**（与授权基线一致） |
| `cd skills/business/pricing-generator && uv run pytest -q` | **31 passed** |
| `bash references/scripts/check_docs_consistency.sh` | **0 errors / 0 warnings / 33 checks** |
| `git diff --check` | 干净（无空白错误） |
| `git status --short` + `git diff --name-only` | 增量仅含允许清单：2 capability + 1 schema test + 本记录 + backlog + 决策记录（先前已存在的 untracked）；§6 逐文件实证 |
| 机制探针（附录 A） | live/fixture 七变体全部符合预期（§3.2 矩阵） |

**门禁零触碰实证**：`test_adapter_status_migration_gate.py` 不在 `git diff --name-only` 输出中；
其 lnkgateway 冻结线断言在 capability 两格翻 not-applicable 后仍全绿——即「capability 层
not-applicable 不影响 authority 冻结线」的机械实证（决策记录 :25-27 关注点的直接回答）。

## 6. 允许清单外零改动实证（git status --short）

```text
 M references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md   （§4.3 授权追加）
 M shared/product_context/tests/test_adapter_capabilities_schema.py               （§4.2 授权钉线）
 M skills/business/competitor-product-analyzer/references/adapter-capabilities.yaml（§4.1 授权两格）
 M skills/business/product-prd-generator/references/adapter-capabilities.yaml     （§4.1 授权两格）
?? references/adapter-capability-owner-decision-o11-2026-10-04.md                （决策记录，先前会话已存在）
?? references/adapter-capability-owner-decision-o11-execution-2026-10-04.md      （§4.3 授权新增）
```

未触碰（授权红线逐项核对）：resolver 生产代码（resolver.py/models.py/errors.py 零 diff）、
门禁测试（test_adapter_status_migration_gate.py 零 diff）、company.yaml、30-products/**
（docs 仓本批只读取证）、product-registry.yaml、pricing-generator 及其他产品条目、
requirement-evaluator capability。未执行任何 git add / commit / push。

## 7. 冻结项与后续

- **仍冻结**：O10-report / O10-vision、删除动作（D1/D2 registry 删除等）、lnkreport / lnkvision
  定价数值。本记录不构成上述任何事项的批准。
- **后续动作**：
  1. orchestrator 会话按 §3.3 提案在 docs 仓落两文件注记（落盘后复跑附录 A 探针做落地验证）；
  2. （仅当未来要求 authority 层翻转时）Batch-2 门禁联动，按 §3.4(c) 备案执行；
  3. PRD 层处置（lnkgateway prd unresolved）不在 O11 范围，如启动另立决策记录。

## 附录 A：机制探针脚本（复现用；本批运行于 /tmp/opencode，只读 docs 基座）

```python
# -*- coding: utf-8 -*-
"""O11 机制取证探针（只读）：live 基线复现 + fixture 措辞变体 + 负对照。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/code/skill/shared")
from product_context import resolve_company, resolve_product  # noqa: E402

REAL_BASE = Path("/opt/code/docs/lanlnk")
GW_INDEX = (REAL_BASE / "30-products/lnkgateway/INDEX.md").read_text(encoding="utf-8")
GW_ONT = (REAL_BASE / "30-products/lnkgateway/ontology/README.md").read_text(encoding="utf-8")


def probe(pid, base):
    payload = resolve_product(pid, resolve_company(company_base=base)).as_dict()
    entry = payload["layers"].get("ontology_entry")
    return payload["authority"]["ontology"]["status"], (str(entry) if entry else None)


def fixture(ont_text, index_text=GW_INDEX):
    tmp = Path(tempfile.mkdtemp(prefix="o11probe-", dir="/tmp/opencode"))
    base = tmp / "acme"
    (base / "config").mkdir(parents=True)
    (base / "config" / "company.yaml").write_text(
        "schema_version: 1\nid: acme\nproducts:\n"
        "  - id: lnkgateway\n    name: LnkGateway\n    code_root: null\n    prd_ready: false\n",
        encoding="utf-8")
    root = base / "30-products" / "lnkgateway"
    (root / "ontology").mkdir(parents=True)
    (root / "prd").mkdir()
    (root / "INDEX.md").write_text(index_text, encoding="utf-8")
    (root / "ontology" / "README.md").write_text(ont_text, encoding="utf-8")
    return probe("lnkgateway", base)


V1_ONT = GW_ONT.replace(
    "| canonical ontology | 无（unresolved） |",
    "| canonical ontology | 无（owner 裁定 O11-③，2026-10-04：集成层能力不建独立 ontology） |",
).replace(
    "不从网关代码反推本体（INDEX 当前权威规则）。下一步：产品启动时由 owner 确认 ontology 来源。",
    "不从网关代码反推本体（INDEX 当前权威规则；owner 既有明令维持）。ontology 长期方向已裁决"
    "（owner O11-③，2026-10-04）：lnkgateway 定位集成层能力/平台基础设施，不建独立 ontology；"
    "capability 层已在 skill 仓按 not-applicable 收口（owner 决策记录 O11），docs 侧 authority "
    "登记维持 unresolved 语义冻结（resolver 的 not-applicable 文本触发词语义不适用于本产品，"
    "机制说明见 skill 仓 O11 执行记录）。PRD 层不在 O11 处置范围（仍 unresolved）。",
)
V1_INDEX = GW_INDEX.replace(
    "| 本体 | `unresolved` | no docs ontology candidate confirmed |",
    "| 本体 | 不建（见 ontology/README） | owner O11-③（2026-10-04）：集成层能力不建独立 ontology；"
    "authority 登记维持 unresolved 冻结 |",
).replace(
    "- docs ontology/PRD 路径保持 unresolved，待产品负责人确认。",
    "- ontology 长期方向已裁决（owner O11-③，2026-10-04）：lnkgateway 定位集成层能力/平台基础设施，"
    "不建独立 ontology；resolver authority 登记维持 unresolved 冻结（capability 层在 skill 仓按 "
    "not-applicable 收口）。\n"
    "- docs PRD 路径保持 unresolved，待产品负责人确认（O11 不处置 PRD 层）。",
)
V1B_ONT = GW_ONT.replace(
    "| canonical ontology | 无（unresolved） |",
    "| canonical ontology | 不建（owner 裁定 O11-③，2026-10-04：集成层能力，不建独立 ontology） |",
)
V2_ONT = GW_ONT.replace(
    "| canonical ontology | 无（unresolved） |",
    "| canonical ontology | 不建（owner 裁定 prd-only，2026-10-04） |",
)
V3_ONT = GW_ONT.replace(
    "| canonical ontology | 无（unresolved） |",
    "| canonical ontology | 不建（owner 裁定 O11-③，不落本目录） |",
)
for name, text in (("V1_ONT", V1_ONT), ("V1_INDEX", V1_INDEX)):
    assert "prd-only" not in text.lower(), f"{name} 含禁词"
for name, probe_result in [
    ("live lnkgateway", probe("lnkgateway", REAL_BASE)),
    ("live lnkwebsite", probe("lnkwebsite", REAL_BASE)),
    ("V0 fixture 拷贝", fixture(GW_ONT, GW_INDEX)),
    ("V1 提案", fixture(V1_ONT, V1_INDEX)),
    ("V1b 不建前缀", fixture(V1B_ONT)),
    ("V2 prd-only 负对照", fixture(V2_ONT)),
    ("V3 本目录 负对照", fixture(V3_ONT)),
]:
    print(f"{name:<24} -> {probe_result}")
```

运行（`shared/product_context` 下）：`uv run python /tmp/opencode/o11_mechanism_probe.py`。
本批实测输出见 §3.2 矩阵。
