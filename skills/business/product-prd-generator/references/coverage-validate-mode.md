# coverage-validate 模式改造方案

> **文档性质**：product-prd-generator 新增 `--mode coverage-validate` 的设计与实施规格
> **创建日期**：2026-07-06
> **状态**：待实施

---

## 1. 目标与非目标

### 1.1 目标

在不重跑全量 PRD 生成的前提下，把新进来的客户需求/竞品资料对照现有 PRD + 代码基线，自动输出：

1. **客户需求覆盖度矩阵**（客户 × 能力 × PRD 状态 × 证据强度）
2. **竞品能力覆盖度矩阵**（竞品 × 能力 × PRD 状态 × 证据强度）
3. **增量 gap 报告**（本次新材料带来的新缺口，对比上次 baseline）
4. **弱证据 review 清单**（机器无法确定强度的项，需人工确认）

替代当前手工做的"7 家客户 × 25 能力核对表"和"5 竞品 × 能力核对表"。

### 1.2 非目标

- **不重跑全量 PRD 生成**。`render.py` 不执行，`产品PRD.md` 不重新生成。
- **不自动决定 P0/P1/P2 优先级**。优先级需要业务判断，工具只输出证据强度和建议，人工最终决定。
- **不自动判断证据域归属**（如"明源账龄证据来自住宅/售楼还是商管"）。这类判断进 review 清单，人工确认。
- **不替代 material-importer**。原始文档的 docx/xlsx/pdf → md 转换仍由 material-importer 完成。

---

## 2. CLI 接口设计

### 2.1 新增参数

```
product-prd-generator \
  --project 商管系统 \
  --code-root /opt/code/mi \
  --docs-root $LANLNK_BASE/raw/prd-商管系统 \
  --skill-root ... \
  --parsed-dir parsed \
  --output-dir output \
  --mode coverage-validate \
  [--baseline parsed/coverage-baseline.json] \
  [--update-baseline] \
  [--customers 万达,深圳中旅,深圳华侨城,深圳安居,深圳星盛,厦门象屿,厦门象屿产发] \
  [--competitors 海鼎,明源,学伟,悦商,旗茂,ifca,凯捷]
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--mode` | `generate` | `generate` = 当前全量生成行为；`coverage-validate` = 新模式 |
| `--baseline` | `parsed/coverage-baseline.json` | 上次运行的 requirement 签名快照，用于增量检测 |
| `--update-baseline` | false | 本次运行结束后用当前结果更新 baseline |
| `--customers` | 自动检测 | 限定纳入矩阵的客户名（逗号分隔）；不传则自动从路径提取全部 |
| `--competitors` | 自动检测 | 同上，竞品名 |

### 2.2 main.py 分支逻辑

```python
if args.mode == "coverage-validate":
    # 前三步不变：code_map → doc_map → reconcile
    # 第四步替换：不跑 render，改跑 coverage_validate
    _run("product_prd_generator.coverage_validate", [
        "--reconcile", str(reconcile_path),
        "--doc-map", str(doc_map_path),
        "--output-dir", args.output_dir,
        "--baseline", args.baseline,
        "--update-baseline" if args.update_baseline else "",
        "--customers", args.customers,
        "--competitors", args.competitors,
    ])
else:
    # 当前全量管线：render → word_export → review
    ...
```

---

## 3. 新模块在管线中的位置

```
当前管线（generate 模式）：
  code_map.py → current-code-map.json
  doc_map.py  → current-doc-map.json
  reconcile.py → capability-reconciliation.json
  render.py   → 产品PRD.md + 功能清单.md + 差距分析.md     ← 全量生成
  word_export → 产品PRD.docx（可选）
  review.py   → review/pending-items.md

新增管线（coverage-validate 模式）：
  code_map.py → current-code-map.json                      ← 复用不改
  doc_map.py  → current-doc-map.json                       ← 复用不改
  reconcile.py → capability-reconciliation.json             ← 复用不改
  coverage_validate.py →                                    ← 新增
    ├─ output/PRD客户需求覆盖度矩阵.json
    ├─ output/PRD客户需求覆盖度矩阵.md
    ├─ output/PRD竞品覆盖度矩阵.json
    ├─ output/PRD竞品覆盖度矩阵.md
    ├─ output/增量gap报告.md
    ├─ review/evidence-weak-items.md
    └─ parsed/coverage-baseline.json（如果 --update-baseline）
```

---

## 4. 输入/输出契约

### 4.1 输入（全部复用现有产物）

| 输入 | 来源 | 用途 |
|---|---|---|
| `capability-reconciliation.json` | reconcile.py | `requirements[]` 提供 `(source_type, source_customer, normalized_term, matched_capability, code_status, priority, nearby_text, evidence)` |
| `current-doc-map.json` | doc_map.py | `features[]` 提供竞品侧证据（`source_type=competitor`）；`requirements[]` 提供行级 `nearby_text` 和 `evidence` 用于强度判断 |

### 4.2 输出

#### `output/PRD客户需求覆盖度矩阵.json`

```json
{
  "schema_version": "1",
  "project": "商管系统",
  "generated_at": "2026-07-06T...",
  "customers": ["万达", "深圳中旅", "深圳华侨城", "深圳安居", "深圳星盛", "厦门象屿", "厦门象屿产发"],
  "capabilities": [
    {
      "capability_id": "aging-analysis",
      "capability_name": "账龄分析",
      "module": "财务管理",
      "customer_evidence": {
        "万达": {"strength": "absent", "source_files": [], "line_refs": [], "note": ""},
        "厦门象屿": {
          "strength": "strong",
          "source_files": ["01-customer-requirements/厦门象屿/02-需求文档/厦门嘉盛恒...md"],
          "line_refs": [859, 861, 1335],
          "note": "欠款台账按账龄汇总 + 合同欠款账龄分析表"
        }
      },
      "overall_customer_strength": "single_strong",
      "customer_consensus_count": 1,
      "prd_status": "P0已补",
      "confidence": "medium",
      "needs_review": false,
      "recommendation": "保持 P0，字段以象屿口径为主"
    }
  ]
}
```

#### `output/PRD客户需求覆盖度矩阵.md`

人类可读版，格式对齐当前手工矩阵：

```markdown
| 能力 | 万达 | 中旅 | 华侨城 | 安居 | 星盛 | 象屿 | 象屿产发 | PRD状态 | 整体强度 | 需复核 |
|---|---|---|---|---|---|---|---|---|---|---|
| 账龄分析 | — | 弱 | 中 | 中 | 弱 | **强** | 中 | 🟢 P0已补 | 单客户强 | ✗ |
| 催缴/付款通知 | **强** | 中 | 中 | **强** | — | **强** | **强** | 🟢 P0已补 | 客户共识强 | ✗ |
```

#### `output/增量gap报告.md`

```markdown
# 增量 Gap 报告

对比 baseline: parsed/coverage-baseline.json (2026-07-01)
当前运行: 2026-07-06

## 新增需求（baseline 中不存在）

| # | 来源 | 客户/竞品 | 能力 | nearby_text | 匹配状态 | 建议 |
|---|---|---|---|---|---|---|
| 1 | 客户需求 | 厦门象屿产发 | 产税计提 | "从租房产税计提=当月不动产租金收入*12%" | unmatched | 新增 P2 候选 |

## 消失需求（baseline 中有，当前不存在）

（信息性，不触发动作）

## 修改需求（同签名但 nearby_text 变化）

（信息性，提示证据可能已更新）
```

#### `review/evidence-weak-items.md`

```markdown
# 弱证据 / 待人工确认项

以下能力的证据强度机器无法自动确定，需人工复核：

| 能力 | 来源 | 问题类型 | 当前机器判断 | 需人工确认 |
|---|---|---|---|---|
| 账龄分析 | 明源 | 域归属不明 | competitor_medium | 确认是商管还是住宅/售楼 |
| 月进撤场统计 | 旗茂 | 仅 URL 无字段 | competitor_medium | 确认是否有字段级证据 |
```

---

## 5. 覆盖度矩阵生成算法

### 5.1 客户矩阵 pivot

```python
def build_customer_matrix(
    reconcile_result: ReconcileResult,
    doc_map: DocMap,
    customers: list[str],
) -> CustomerMatrix:
    """
    pivot: RequirementRecord[] → customer × capability 矩阵
    
    步骤:
    1. 从 reconcile_result.requirements 筛选 source_type == "customer-requirements"
    2. 按 source_customer 分组
    3. 按 normalized_term (或 matched_capability) 二次分组
    4. 每个 (customer, capability) 单元格调用 score_customer_evidence() 评强度
    """
```

### 5.2 竞品矩阵 pivot

```python
def build_competitor_matrix(
    reconcile_result: ReconcileResult,
    doc_map: DocMap,
    competitors: list[str],
) -> CompetitorMatrix:
    """
    pivot: DocFeature[source_type=competitor][] → competitor × capability 矩阵
    
    步骤:
    1. 从 doc_map.features 筛选 source_type == "competitor"
    2. 从 source_file 路径提取竞品名（02-competitors/{竞品名}/...）
    3. 按竞品名 + normalized_term 分组
    4. 每个 (competitor, capability) 单元格调用 score_competitor_evidence() 评强度
    """
```

> **注意**：竞品名提取逻辑当前 doc_map.py 没有（只有 `_extract_customer`）。在 coverage_validate.py 内部用路径解析实现，不改 doc_map.py。

### 5.3 能力维度归一

矩阵的行（能力维度）来源优先级：

1. `matched_capability`（reconcile 已匹配到 spec capability ID）→ 用 capability ID
2. `normalized_term`（reconcile 未匹配但术语归一成功）→ 用 normalized_term
3. `function`（原始 heading）→ unmatched，进增量 gap

---

## 6. 证据强度评分规则

### 6.1 客户证据强度（每单元格）

| 强度 | 判定规则（机器可执行） |
|---|---|
| `strong` | heading depth ≤ 3 **且** nearby_text 长度 ≥ 50 字符 **且** evidence 非空 |
| `medium` | heading depth ≤ 3 **但** nearby_text < 50 字符；**或** depth = 4 但 nearby_text 含功能关键词 |
| `weak` | depth ≥ 4 **且** nearby_text < 50 字符；**或** 仅在周边 scenario 上下文出现 |
| `absent` | 该客户无 requirement 匹配到此 capability |

> nearby_text 长度阈值 50 字符可配置。依据：手工复核中"强"证据的 nearby_text 普遍 ≥ 50 字（如象屿行 488-497 现金流预测算例）。

### 6.2 竞品证据强度（每单元格）

| 强度 | 判定规则（机器可执行） |
|---|---|
| `strong` | source_file 来自功能手册/操作手册（`.doc.md` / 蓝图方案） **且** evidence 含 `doc` 类型引用 **且** nearby_text ≥ 50 字符 |
| `medium` | source_file 来自 pptx/xlsx 转换（汇报方案/功能清单）**或** evidence 仅含路径无章节；**或** demo 探测数据（路径含 `qimao/page-fields-`） |
| `weak` | nearby_text < 30 字符 **或** source_file 来自 OCR 噪音文件 |
| `absent` | 该竞品无 feature 匹配到此 capability |

### 6.3 能力整体强度（行级汇总）

| 整体强度 | 判定规则 |
|---|---|
| `customer_consensus_strong` | ≥ 3 家客户 strong **或** ≥ 2 家客户 strong + ≥ 1 家竞品 strong |
| `customer_consensus_medium` | 1-2 家客户 strong；**或** ≥ 2 家客户 medium + 竞品 medium+ |
| `single_customer_strong` | 仅 1 家客户 strong，其余 absent/weak |
| `competitor_supported` | 无客户 strong，但 ≥ 2 家竞品 strong |
| `competitor_single` | 仅 1 家竞品 strong |
| `weak` | 仅 weak/absent 证据 |

### 6.4 机器无法确定的（进 review）

以下情况机器标注 `needs_review = true`，写入 `review/evidence-weak-items.md`：

| 问题类型 | 触发条件 | 人工需确认 |
|---|---|---|
| `domain_ambiguous` | 竞品 source_file 路径含 `明源` **且** capability 在住宅/售楼 ontology 中也存在（如"账龄""成本""计划"） | 确认证据来自商管还是住宅/售楼 |
| `url_only` | 竞品 source_file 来自 demo 探测（路径含 `qimao/`）**且** evidence 无 `doc` 类型行级引用 | 确认是否有字段级证据 |
| `single_source_customer` | 仅 1 家客户 strong **且** 0 家竞品 strong | 确认是否为单客户特有需求 |
| `contradiction` | 同一 capability 在客户侧 strong 但 reconcile 匹配到 `explicitly-not-do` | 确认是 PRD 有意不做还是遗漏 |

---

## 7. 增量 gap 检测

### 7.1 Requirement 签名

```python
def requirement_signature(req: RequirementRecord) -> str:
    """
    签名 = sha256(source_type + source_customer + normalized_term + function)
    不含 nearby_text（文本可能微调）和 priority（优先级会变）。
    """
    raw = f"{req.source_type}|{req.source_customer}|{req.normalized_term}|{req.function}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

### 7.2 Baseline 格式

```json
{
  "schema_version": "1",
  "generated_at": "2026-07-01T...",
  "signatures": {
    "a1b2c3d4e5f67890": {
      "source_type": "customer-requirements",
      "source_customer": "厦门象屿",
      "normalized_term": "aging-analysis",
      "function": "合同欠款账龄分析表"
    }
  }
}
```

### 7.3 Delta 分类

| Delta 类型 | 判定 | 处理 |
|---|---|---|
| `delta_new` | 当前签名不在 baseline 中 | 写入增量 gap 报告，标记为新增候选 |
| `delta_dropped` | baseline 签名不在当前中 | 信息性记录，不触发动作（可能资料被移走） |
| `delta_modified` | 签名相同但 nearby_text hash 变化 | 信息性记录，提示证据可能已更新 |

---

## 8. 复用 / 新增 / 不改清单

### 8.1 完整复用（不改一行）

| 模块 | 复用内容 |
|---|---|
| `code_map.py` | 提取代码侧 capability，输出 `current-code-map.json` |
| `doc_map.py` | 提取文档侧 feature/requirement，输出 `current-doc-map.json`。`source_type`/`source_customer` 分类逻辑已具备 |
| `reconcile.py` | 匹配 doc ↔ code，输出 `capability-reconciliation.json`。`RequirementRecord` 已含全部矩阵所需字段 |
| `models.py` | `CapabilityStatus`/`Confidence`/`EvidenceKind`/`Priority` 枚举复用 |
| `references/term-aliases.yaml` | 术语归一复用 |
| `references/reconciliation-schema.json` | reconcile 输出格式复用 |

### 8.2 新增

| 文件 | 内容 | 预估 LOC |
|---|---|---|
| `product_prd_generator/coverage_validate.py` | 新模块：矩阵 pivot + 强度评分 + delta 检测 + MD/JSON 渲染 | 350-450 |
| `references/coverage-validate-mode.md` | 本设计文档 | — |

### 8.3 小改（加分支，不改现有逻辑）

| 文件 | 改动 |
|---|---|
| `main.py` | 加 `--mode`/`--baseline`/`--update-baseline`/`--customers`/`--competitors` 参数；加 `coverage-validate` 分支 |
| `SKILL.md` | 加「coverage-validate 模式」章节（运行方式 + 输出说明 + 与 generate 模式的区别） |

### 8.4 不改

| 文件 | 理由 |
|---|---|
| `render.py` | 全量 PRD 渲染逻辑不变，coverage-validate 不调用它 |
| `word_export.py` | 同上 |
| `review.py` | 现有 pending-items 逻辑不变；evidence-weak-items 是 coverage_validate 内部输出 |
| `data_model.py` | 数据模型层不涉及 |

---

## 9. coverage_validate.py 模块结构

```python
# product_prd_generator/coverage_validate.py

def main() -> int:
    """CLI entry point, called by main.py subprocess."""
    args = parse_args()
    reconcile = load_reconcile(args.reconcile)
    doc_map = load_doc_map(args.doc_map)
    baseline = load_baseline(args.baseline) if args.baseline else None
    
    # 1. 构建矩阵
    customer_matrix = build_customer_matrix(reconcile, doc_map, args.customers)
    competitor_matrix = build_competitor_matrix(reconcile, doc_map, args.competitors)
    
    # 2. 评分 + 标记 review
    scored = score_and_flag(customer_matrix, competitor_matrix)
    
    # 3. 增量检测
    delta = detect_delta(reconcile.requirements, baseline)
    
    # 4. 输出
    write_customer_matrix_json(scored, args.output_dir)
    write_customer_matrix_md(scored, args.output_dir)
    write_competitor_matrix_json(scored, args.output_dir)
    write_competitor_matrix_md(scored, args.output_dir)
    write_delta_report(delta, args.output_dir)
    write_weak_evidence_review(scored, review_dir)
    
    # 5. 更新 baseline
    if args.update_baseline:
        write_baseline(reconcile.requirements, args.baseline)
    
    return 0


# --- 矩阵构建 ---

def build_customer_matrix(reconcile, doc_map, customers) -> dict:
    """pivot RequirementRecord → customer × capability"""

def build_competitor_matrix(reconcile, doc_map, competitors) -> dict:
    """pivot DocFeature[source_type=competitor] → competitor × capability
    竞品名从 source_file 路径 02-competitors/{name}/ 提取。"""

def _extract_competitor_name(source_file: str) -> str:
    """从路径提取竞品名，类似 doc_map._extract_customer 但针对 02-competitors/"""


# --- 强度评分 ---

def score_customer_evidence(reqs: list[RequirementRecord]) -> str:
    """返回 strong/medium/weak/absent"""

def score_competitor_evidence(features: list[dict]) -> str:
    """返回 strong/medium/weak/absent"""

def score_overall(customer_scores: dict, competitor_scores: dict) -> str:
    """返回 customer_consensus_strong/.../weak"""


# --- Review 标记 ---

def flag_for_review(capability_id: str, customer_matrix, competitor_matrix) -> ReviewItem | None:
    """检查 domain_ambiguous / url_only / single_source_customer / contradiction"""


# --- 增量检测 ---

def requirement_signature(req: RequirementRecord) -> str:
    """sha256(source_type|source_customer|normalized_term|function)[:16]"""

def detect_delta(current_reqs, baseline_signatures) -> DeltaReport


# --- 渲染 ---

def render_customer_matrix_md(matrix) -> str:
    """Markdown 表格，对齐当前手工矩阵格式"""

def render_delta_md(delta) -> str
```

---

## 10. SKILL.md 需要补充的章节

在 SKILL.md「运行方式」章节后新增：

```markdown
## coverage-validate 模式

### 用途

新材料（客户需求/竞品资料）入库后，对照现有 PRD + 代码做覆盖度校验，输出矩阵和增量 gap，
不重跑全量 PRD 生成。适用于 PRD v1.x 持续完善场景。

### 运行方式

​```bash
cd skills/business/product-prd-generator
export LANLNK_BASE=/opt/code/docs/lanlnk
uv run product-prd-generator \
  --project 商管系统 \
  --code-root /opt/code/mi \
  --docs-root $LANLNK_BASE/raw/prd-商管系统 \
  --skill-root . \
  --parsed-dir $LANLNK_BASE/prd/商管系统/parsed \
  --output-dir $LANLNK_BASE/prd/商管系统/output \
  --mode coverage-validate \
  --baseline $LANLNK_BASE/prd/商管系统/parsed/coverage-baseline.json \
  --update-baseline
​```

### 输出

| 文件 | 用途 |
|---|---|
| `output/PRD客户需求覆盖度矩阵.json` | 结构化矩阵，供下游工具消费 |
| `output/PRD客户需求覆盖度矩阵.md` | 人类可读，对齐当前手工矩阵格式 |
| `output/PRD竞品覆盖度矩阵.json` / `.md` | 同上，竞品维度 |
| `output/增量gap报告.md` | 本次新材料带来的新缺口 |
| `review/evidence-weak-items.md` | 机器无法确定的证据强度，需人工确认 |

### 与 generate 模式的区别

| 维度 | generate | coverage-validate |
|---|---|---|
| code_map / doc_map / reconcile | ✅ 运行 | ✅ 运行 |
| render（全量 PRD 生成）| ✅ 运行 | ❌ 不运行 |
| 覆盖度矩阵输出 | ❌ | ✅ |
| 增量 gap 检测 | ❌ | ✅ |
| 弱证据 review | ❌ | ✅ |
| 适用场景 | 首次生成 / 主干重构 | 持续完善 / 新材料校验 |

### 证据强度说明

（引用本文件 §6 的评分规则表）

### 已知限制

- **~19% 匹配率瓶颈仍然存在**：coverage-validate 复用 reconcile 的术语匹配，ontology 覆盖率不足时 unmatched 需求会进增量 gap 而非矩阵。继续扩 ontology 术语是唯一提升路径。
- **机器无法判断域归属**：如明源"账龄"证据来自住宅/售楼还是商管，进 `review/evidence-weak-items.md` 待人工确认。
- **竞品名提取依赖路径规范**：要求竞品资料在 `02-competitors/{竞品名}/` 下；旗茂 demo 探测数据在 `competitor-analysis/qimao/` 下需特殊处理。
```

---

## 11. 验证方式

### 11.1 单元验证

| 验证项 | 方法 |
|---|---|
| 矩阵 pivot 正确 | 用当前 `parsed/capability-reconciliation.json` 跑一次，对比手工矩阵的"催缴""账龄""存款转移"等已知单元格 |
| 强度评分合理 | 对比本次手工复核结论：象屿账龄=strong、万达账龄=absent、旗茂报表=medium、明源账龄=domain_ambiguous |
| delta 检测正确 | 首次跑 baseline 为空 → 全部进 delta_new；二次跑 → 仅新增进 delta_new |
| review 标记正确 | 明源账龄应进 `domain_ambiguous`；旗茂月进撤场应进 `url_only` |

### 11.2 集成验证

```bash
# 首次运行（无 baseline）
uv run product-prd-generator --mode coverage-validate ...
# 预期：全部 requirement 进 delta_new，矩阵全量输出

# 模拟新增材料：向 raw/ 加一份新客户需求 md
# 二次运行
uv run product-prd-generator --mode coverage-validate --update-baseline ...
# 预期：仅新客户的需求进 delta_new，矩阵更新该客户列
```

### 11.3 对比验证

将机器输出的 `PRD客户需求覆盖度矩阵.md` 与当前手工维护的 `competitor-analysis/_baseline/PRD客户需求覆盖度矩阵-v1.0.md` 逐单元格对比，差异应 ≤ 5%（允许因 ontology 匹配率导致的 unmatched 差异）。

---

## 12. 实施顺序建议

| 步骤 | 内容 | 前置 |
|---|---|---|
| 1 | `coverage_validate.py` 骨架 + CLI 参数 + 加载 reconcile/doc_map | 无 |
| 2 | `build_customer_matrix` + `score_customer_evidence` + MD 渲染 | 步骤 1 |
| 3 | `build_competitor_matrix` + `score_competitor_evidence` + 竞品名提取 | 步骤 2 |
| 4 | `score_overall` + `flag_for_review` + weak-evidence 输出 | 步骤 3 |
| 5 | `detect_delta` + baseline 读写 + 增量 gap 报告 | 步骤 2 |
| 6 | `main.py` 加 `--mode` 分支 | 步骤 1-5 |
| 7 | SKILL.md 补章节 | 步骤 6 |
| 8 | 用当前商管系统数据跑验证 | 步骤 7 |

每步可独立提交，步骤 2-5 可并行。
