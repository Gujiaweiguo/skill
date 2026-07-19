# bid-doc-master Troubleshooting

本文件记录 bid-doc-master 的**非显然行为**与**踩坑修复**——读代码不会立刻理解"为什么这么做"的那些。
与 `case-example.md`（演示完整投标案例）配合阅读。

> 复杂度分级：本 skill 属 AGENTS.md tier 表的 **Complex**（多模块包），troubleshooting.md 必填。

---

## 1. CLI 工具是两步式，不是一步式

**症状**：试图用一个命令从招标文件直接出 .docx，找不到对应 flag。

**根因**：bid-doc-master 内置 CLI 故意拆成两步，因为中间产物 `tender_raw.json` 需要 agent 人工分析填充 `TenderInfo` 字段（招标文件的原始文本不能直接驱动内容包生成）。

**正确流程**：
```bash
cd skills/business/bid-doc-master

# Step 1: 招标文件 → 结构化 JSON
uv run python -m src.main extract "招标文件.docx" "功能清单.xlsx" -o tender_raw.json -v

# Step 2: agent 分析 tender_raw.json，手填 TenderInfo JSON 后生成内容包
uv run python -m src.main generate tender_info.json \
  --bidder "广州市蓝联科技有限公司" \
  --type technical \
  --slide \
  -v
```

**不要尝试**：`uv run python -m src.main everything 招标文件.docx` 之类的"端到端"假命令——不存在。
未知 TenderInfo 字段一律留空 `[]`，**不得编造**。

详见 SKILL.md §3.0.1。

---

## 2. Pricing Compiler YAML 必须用 `categories` 顶层列表

**症状**：跑 `pricing_compiler.py` 报 KeyError 或生成的 xlsx 报价表为空。

**根因**：早期版本 schema 用嵌套 `items.software`，现已废弃。当前 schema 要求：

```yaml
categories:
  - name: 软件产品
    items:
      - id: S001
        name: 商管系统
        description: ...
        first_unit_price: 100000
        first_qty: 1
        new_unit_price: 100000
        new_qty: 1
  - name: 二开服务
    items: [...]
```

**关键字段**（缺失任一会失败）：
- 顶层用 `categories`（list），不是 `items`
- 每个 item 必须有 `id` / `name` / `description`
- 价格字段：`first_unit_price` + `first_qty`（首年）+ `new_unit_price` + `new_qty`（次年）

详见 AGENTS.md §「Pricing Compiler YAML Schema」。

---

## 3. Word 内容包交给 word-master，不要本 skill 直接生成 .docx

**症状**：试图在 bid-doc-master 里用 python-docx 直接写 .docx，结果缺样式/缺模板/章节错乱。

**根因**：商务标与技术标的 .docx 排版是 word-master 的职责，bid-doc-master 只负责输出符合 [Word 内容包规范](../../word/word-master/reference/word-content-package-spec.md) 的 `.word-content.md` 中间产物。

**架构**：
```
bid-doc-master                word-master
─────────────                 ────────────
.word-content.md  ────────→  uv run python -m src.main <pkg.md>
(本 skill 输出)              (排版 + 模板套用)
                                ↓
                            商务标.docx / 技术标.docx
```

**正确调用**（参考 AGENTS.md §「word-master calling pattern」）：
```python
import subprocess
subprocess.run(
    ["uv", "run", "python", "-m", "src.main", str(content_path.resolve()), "--output", str(output)],
    cwd=str(word_master_dir),  # 必须在 word-master 目录用 uv 跑，不是 python3
)
# content_path 必须是绝对路径——subprocess cwd 会切换，相对路径会断
```

**注意路径**：word-master 的规范目录是 `reference/`（**单数**），不是 `references/`（复数）。这是历史命名差异，不影响功能。

---

## 4. Markdown 表格列名禁用特殊字符

**症状**：内容包里的 `markdown` 字段渲染出来的不是表格，而是一坨纯文本。

**根因**：YAML `markdown` 字段含 markdown 表格时，列名出现 `→` / `←` / `*` / `#` 等特殊字符，分隔符行 `| → |` 不是合法的 markdown 对齐说明符（合法的只有 `---` / `:---` / `---:` / `:---:`）。解析器识别失败 → 整张表塌成纯文本。

**错误示例**：
```markdown
| 源模块 | → | 目标模块 |     ← 列名 → 不是合法对齐说明符
|--------|---|----------|
| 合同   | → | 财务      |
```

**正确写法**：把特殊字符合并到相邻列名。
```markdown
| 联动路径（源→目标） |     ← 列名只含中文/字母/数字
|---------------------|
| 合同 → 财务          |
```

这是**跨 skill 陷阱**（product-prd-generator / bid-doc-master / word-master 都中过招），见 AGENTS.md §「Markdown 矩阵表格列名陷阱」。

---

## 5. LSP 报的 docx / openpyxl 错误是假阳性

**症状**：编辑 `pricing_compiler.py` 时，LSP 给 `load_workbook` / `Workbook.active` 等大量报"not a known attribute"。

**根因**：openpyxl 与 python-docx 的 type stubs 不完整。LSP 静态分析看不到运行时方法。

**正确动作**：**不要"修复"这些报错**。不要加 `# type: ignore`、不要改写为 `getattr(...)`、不要重构。**实际跑 `uv run` 不会出错**，验证以运行为准。

同理：LSP 偶尔报 `test_reader.py` / `test_generator.py` 有问题——这两个文件**不存在**，是 LSP 缓存遗留，清缓存即可。

详见 AGENTS.md §「LSP Warning」。

---

## 6. 响应矩阵不能漏响应项（资格审查缺项 = 直接废标）

**症状**：以为"资格要求都是标准材料，可以后面补"，结果投标被废。

**根因**：投标文件的资格审查缺项通常**直接废标**，不像评分项可以扣分了事。

**正确动作**：在 P1 招标文件解析阶段就建立**响应矩阵**（SKILL.md §1.3 + §4.1），每一条招标要求都要落到：
- ✅ 已覆盖
- ⚠️ 待确认（要用户提供）
- ❌ 缺失（模板/输入材料没对应内容）
- 🚫 风险（可能废标/扣分）

**禁止跳步**：见 SKILL.md §4.0 「Common Rationalizations 反借口表」——6 条常见的"偷懒理由"+真实风险+正确动作。

---

## 7. 禁止编造任何资质 / 业绩 / 报价 / 人员

**症状**：agent 觉得"没有信息就帮用户补一个合理值"——**严重合规风险**。

**根因**：编造资质证书、人员证书、业绩合同、报价金额、授权文件会让投标人在履约/审计阶段被追责，严重时涉及法律。

**唯一正确动作**：所有未知字段统一标记为 `待确认`，列入 `$BIDDING_DIR/<项目名>/output/06-待确认事项-confirmation-list.md`，等用户补全后再继续。

详见 SKILL.md §4.3「禁止事项」。

---

## 8. 模板复用前必须先建立响应矩阵

**症状**："模板已经是终稿，直接替换项目名就行"——结果投标文件出现旧项目残留、漏响应新招标要求。

**根因**：历史模板不会自动覆盖本次招标新增的章节/评分项/资格要求。

**正确流程**（SKILL.md P2 模板素材映射）：
1. 先做招标要求响应矩阵（哪些章节/评分项/资格要求）
2. 再分析已有模板能复用哪些章节
3. 建立变量表（`{项目名}` / `{采购人}` / `{投标人}` / `{日期}` 等）
4. 替换变量后，**逐项比对**响应矩阵 vs 实际输出，确认无遗漏

`case-example.md` 演示了完整案例。

---

## 9. openpyxl 报价合计公式不要在未核对前覆盖

**症状**：直接修改 xlsx 报价表的汇总单元格，结果小写/大写/分项合计/总价不一致——投标无效或扣分。

**根因**：报价表汇总格通常含 Excel 公式（`=SUM(...)`）。手工覆盖会破坏公式。

**正确动作**：
1. 先识别报价口径（最高限价 / 税率 / 含税不含税 / 分项 vs 总价）—— SKILL.md §1.2 强制要求项
2. 生成报价待确认清单（让用户确认公式）
3. **核对无误后**才能改汇总单元格
4. 最后跑一致性校验（SKILL.md §4.2）：小写、大写、分项合计、总价必须一致

---

## 10. 输出路径

所有产物必须落 `$BIDDING_DIR/<项目名>/output/`（默认 `$LANLNK_BASE/bidding/<项目名>/output/`）。内容包中间产物落 `output/content-packages/` 子目录。

完整目录结构见 SKILL.md §5.1。

---

## 与其它文档的关系

| 文件 | 作用 | 何时读 |
|---|---|---|
| 本文件 | 踩坑 + 非显然行为 | 第一次跑、出错时、改 SKILL.md 时 |
| `case-example.md` | 完整投标案例演示 | 第一次跑、不确定流程时 |
| SKILL.md §4.0「Common Rationalizations」 | 反借口表（6 条禁止跳步） | 每个 project 开始时复读 |
| SKILL.md §4.3「禁止事项」 | 5 条红线 | 每次交付前复读 |
| `../../word/word-master/reference/word-content-package-spec.md` | Word 内容包字段规范 | 写 `.word-content.md` 前 |
