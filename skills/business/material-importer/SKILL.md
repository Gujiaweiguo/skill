---
name: material-importer
description: |-
  素材导入与结构化 Skill。将原始文档（PPT/Word/Excel/图片）批量转换、提取图片、
  OCR 识别、智能分类，整理为标准化素材存入共享素材库。核心能力：多文件混合拆分、
  AI 内容识别与质量评估、交互式确认。
  触发场景："整理素材"、"导入公司资料"、"把 incoming/ 里的文件入库"、"入库新案例"、
  "检查证照有效期"、"检查素材质量"。
compatibility: >
  Requires Python 3.10+ and uv.

  Quick start:
  ```bash
  export LANLNK_BASE=/opt/code/docs/lanlnk
  cd skills/business/material-importer
  uv sync
  ```

  Falls back from markitdown → python-pptx/python-docx/openpyxl if unavailable.
  OCR: DeepSeek-OCR-2 (VLM) for image-heavy docs via `scripts/ocr_extract.py` (PEP 723 inline deps, ~8GB VRAM).
  Cert expiry: pytesseract (optional, CPU-only, lightweight).
change: >
  v2 — 2026-06-18
  • 简化目录结构：移除 incoming/raw/，转换结果统一进 raw/
  • 新增 P1.5 空章节清理：自动移除空壳章节、占位文本、base64 噪音
  • 新增 P2 拆分触发条件：显式化 4 条必须拆分规则 + 命名规范
  • 新增 P5b 关系索引维护：raw/_index.json 追踪 raw→materials 引用
---

# Material Importer — 素材导入与结构化 Agent Pipeline

## DocSpec 质量基线

本 skill 生成的素材质量报告、缺口分析、入库建议和结构化素材说明必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `DocSpec-通用文档质量规范.md` 和 `文档验收清单.md`。素材来源、质量等级、缺失项和待人工确认项必须保留。

基于 `原始素材 → markitdown 转换 → AI 分类 → 质量评估 → 交互确认 → 标准化入库` 的方案。

## 目录结构（三级）

```
$LANLNK_BASE/
├── incoming/                      ← 🟢 原始素材入口
│                                  只放原始文件（PPTX/DOCX/XLSX/图片）
│                                  转换后由 Agent 清理，不留残余
│
├── raw/                           ← 🟡 中间产物
│   ├── 原始文件.pptx.md             markitdown 转换结果
│   ├── 原始文件_media/              提取的图片
│   └── _index.json                 自动维护的使用关系索引
│
└── materials/                     ← 🔵 最终产出
                                  结构化素材（8 大类，供查询/引用）
```

路径变量：
- `$INCOMING_DIR` = `incoming/`（原始素材入口）
- `$RAW_DIR` = `raw/`（Markdown + 图片 + _index.json）
- `$MATERIALS_DIR` = `materials/`（结构化素材，8 大类）
- `$SCRIPTS_DIR` = `{baseDir}/scripts`

完整目录结构见 `config/lanlnk.yaml`。

> ⚠️ **只有两个 raw**：转换结果统一进 `raw/`，不存在 `incoming/raw/`。  
> 之前遗留的 `incoming/raw/` 是早期 pipeline 产物，应删除。

## 核心原则

1. **不是简单转换**：是对原始内容的理解、拆分、重组
2. **质量优先**：无意义内容不收录，缺失项标记提醒
3. **交互式确认**：每批导入后输出质量报告，逐条请用户确认
4. **多文件混合拆分**：一次多份文件混入，AI 自动拆分到对应类别

## Pipeline

```
incoming/ 里的原始文件（PPTX/DOCX/XLSX/图片）
    ↓
P0: 环境检测 + 素材盘点（检查依赖 + 扫描已有素材）
    ↓
P1: 文档转换
    ├── markitdown 提取文本 → raw/*.md
    └── extract_images.py 提取图片 → raw/*_media/
    ↓
P1.5: 空章节清理（AI 自动移除空壳章节、占位文本、base64 噪音）
    ↓
P2: AI 内容识别与拆分（分类映射见 references/domain-tags.md）
    ↓
P3: 质量评估（评分标准见 references/quality-standards.md）
    ↓
P4: 交互确认（输出导入报告，用户确认后入库）
    ↓
P5: 标准化输出 → materials/（素材模板 + 证照OCR + validate_material.py 校验）
    ↓
P5b: 关系索引维护 → raw/_index.json（记录 raw→materials 引用关系）
```

### P0 环境检测

```bash
uv sync                    # 安装依赖（含 markitdown、python-pptx、openpyxl 等）
uv run {baseDir}/scripts/validate_material.py $MATERIALS_DIR  # 校验已有素材
```

### P1 文档转换

```bash
# 文本转换
markitdown "incoming/原始文件.pptx" > "raw/原始文件.pptx.md"

# 图片提取（支持 PPTX/DOCX，自动修正 Markdown 图片路径）
uv run {baseDir}/scripts/extract_images.py incoming/   # 批量处理
uv run {baseDir}/scripts/extract_images.py incoming/ --json  # Agent 程序化读取
```

### P1.5 空章节清理（新增）

转换后的 markdown 可能包含来自原始文档的空壳章节、占位文本和内嵌图片噪音。**此步骤由 AI 自动完成**，不依赖脚本。

清理规则：

| 清理项 | 规则 | 示例 |
|--------|------|------|
| **空章节** | 标题下无实质内容（仅空白/标点/换行）→ 移除该章节 | `## XXXX集团现状`（下面空）→ 删 |
| **占位文本** | 纯占位符（`XXXX`、`…`、`……`、纯标点行）→ 移除 | `XXXX集团` → 处理为上下文推断 |
| **内嵌 base64 图片** | 超过 500 字符的 data URI → 替换为 `[图片: 第N页]` | `![](data:image/png;base64,iVBOR...)` → `[图片: 第15页]` |
| **空行坍缩** | 连续 3+ 空行 → 压缩为 1 行 | 保留基本排版结构 |

执行方式：

```
读取 raw/*.md → AI 逐段判断内容有效性 → 清理后覆盖原文件
```

### P2 AI 内容识别与拆分

分类映射表见 `references/domain-tags.md`（可按需调整业务线标签）。

#### 拆分触发条件（必须执行）

以下情况 **必须拆分**，不得保留为单一大文件：

| 条件 | 处理方式 | 示例 |
|------|---------|------|
| 一份文件含 **2+ 个客户案例** | 按客户名称拆为独立文件 | `XX公司介绍.pptx` 含天河城/喜街/宝能 3 个案例 → `天河城案例.md`、`喜街案例.md`、`宝能案例.md` |
| 一份文件**混合产品+案例+公司简介** | 按 `03-products/`、`02-cases/`、`01-company/` 类别拆分 | `CRE系统介绍.pptx` → 产品描述归 products，案例归 cases |
| 单文件 **> 500 行**且内容不属于单一类别 | 提示用户确认是否拆分，列出各章节归类建议 | 用户确认后执行 |
| 一份文档产出**多类素材**（技术文件） | 按类型拆分：案例 + 实施 + 服务 + 人员 + 资质 | 投标方案 → 实施方法论归 impl，服务归 svc，案例归 cases |

#### 拆分后命名规则

```
raw/
├── 原始文件名_子类.md              ← 拆分后的文件
├── 原始文件名_产品A.md
└── 原始文件名_案例B.md
```

拆分后源文件保留（作为完整参考），拆分出的文件以 `原始文件名_子类.md` 命名。

### P3 质量评估

评分标准见 `references/quality-standards.md`（8 类素材逐项 checklist + 红线规则，可按需调整）。

| 评分 | 含义 | 处理 |
|------|------|------|
| ⭐⭐⭐ | 完整 | 直接入库 |
| ⭐⭐ | 部分缺失 | 入库 + 标记 ⚠️ |
| ⭐ | 严重缺失 | 拒绝，说明原因 |

### P4 交互确认

1. 输出导入报告（新增/更新/跳过/丢弃），逐条列出缺失项
2. 用户确认或补充信息
3. 最终写入素材库

### P5 标准化输出

**素材模板** — 统一 YAML frontmatter 格式：
```markdown
---
id: "case-YYYYMMDD-NNN"
type: "案例"
name: "世欧广场会员系统小程序"
domain: ["商管", "会员"]
status: "complete"
created: "YYYY-MM-DD"
source: "raw/原始文件.pptx.md"
---
```

**证照模板** — 增加 issued/expires/issuer/cert_no/images 字段。
**文件命名**：中文可读名，案例以客户+项目命名，资质以证书全称命名。
**ID 规则**：`{type}-YYYYMMDD-NNN`（case-/prod-/qual-/impl-/svc-/hr-）。

### P5b 关系索引维护（新增）

每次入库/更新素材时，自动维护 `raw/_index.json`，记录"哪个 raw 文件被哪些 material 消费了"。

```json
{
  "蓝联科技_投标解决方案.docx.md": {
    "imported_at": "2026-06-18",
    "imported_from": "incoming/蓝联科技_投标解决方案.docx",
    "consumed_by": [
      "materials/03-products/系统实施与服务体系.md",
      "materials/05-bid/投标模板.md"
    ],
    "unconsumed_sections": [
      "公司简介部分 - 未在 materials 中引用"
    ],
    "needs_review": false
  },
  ...
}
```

**维护规则**：
- 新建 material 时 → 在 `consumed_by` 中添加引用路径
- 修改 material 时 → 检查 source 是否变动，更新 `consumed_by`
- 清理 raw 文件前 → 检查 `consumed_by` 是否为空，非空则提示用户确认
- `unconsumed_sections` 由 AI 判断（对比 raw 文件内容 vs materials 中实际使用的部分）

**证照有效期检查**：
```bash
uv run {baseDir}/scripts/check_cert.py $LANLNK_BASE/materials
uv run {baseDir}/scripts/check_cert.py $LANLNK_BASE/materials --json  # Agent 程序化读取
```

**素材文件校验**：
```bash
uv run {baseDir}/scripts/validate_material.py $MATERIALS_DIR          # 文本报告
uv run {baseDir}/scripts/validate_material.py $MATERIALS_DIR --json   # JSON 输出
```

**案例匹配**（company-intro-generator / bid-doc-master 生成时调用）：
```bash
uv run {baseDir}/scripts/case_matcher.py --industry 商业地产 --scenarios 会员营销,积分 --limit 5
uv run {baseDir}/scripts/case_matcher.py --keywords 私域,商城 --json   # JSON 输出
uv run {baseDir}/scripts/case_matcher.py --list-tags                   # 列出所有行业和场景标签
```
匹配维度：行业（×3）、场景（×2.5）、关键词（×1.5）、规模相近度（×1）、完整度（×0.5）。

### P6 资料缺口审查

两种模式，完整框架见 `references/gap-analysis.md`：
- **方案介绍模式**（触发："检查素材够不够做XX方案"）— 5 层覆盖率评分
- **投标模式**（触发："检查XX项目投标还缺什么"）— 9 维度符合性 + 风险评分

## 使用示例

> 用户："把 incoming/ 里的文件都入库"

```
Agent:
   扫描到 2 份文件，按以下流程处理：
   ✅ 动感小西关技术文件.docx → 转换为 Markdown + 提取图片
   ✅ 动感小西关报价文件.xlsx → 转换为 Markdown
   ✅ P1.5: 空章节清理 → 移除 3 个空壳章节，压缩 2 处 base64 图片
   ✅ P2: 内容拆分 → 识别出 6 类素材（技术文件含实施+服务+案例+资质+人员）
   ✅ P5b: 更新 _index.json

   AI 识别并拆分为 6 类素材：
   ✅ [实施] 蓝联科技实施方法论 — 评分 ⭐⭐⭐ 完整
   ✅ [服务] 技术支持与服务体系 — 评分 ⭐⭐⭐ 完整
   ✅ [案例] 动感小西关会员小程序 — 评分 ⭐⭐
   ⚠️ [资质] ISO27001认证 — 评分 ⭐⭐ 缺有效期
   ⚠️ [人员] 项目团队 — 评分 ⭐ 缺具体人员姓名
   ❌ [x] 重复内容（公司简介）— 已存在，跳过

   需确认：ISO27001 有效期？项目团队具体人员信息？

   关系索引已更新：
   ✅ raw/蓝联科技_投标解决方案.docx.md
      → consumed_by: 系统实施与服务体系.md
      → unconsumed_sections: [公司简介, 客户案例] 建议进一步提取
```
