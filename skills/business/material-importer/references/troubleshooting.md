# material-importer Troubleshooting（已知坑与修复规则）

复杂度分层：本 skill 为多模块包（complex 级），本文件为必配的坑位登记处。
每条格式：症状 → 根因 → 修复/规则，附代码锚点（file + function）。

## 1. Excel 序列日期误转（108 个假 1900 日期事故）

- 症状：凭证表 T1 编码（2/5/8）、科目码（~100）、年份 2024 被批量转成
  1900 年附近日期（2024 → 1905-07-16），共 108 处污染。
- 根因：旧实现逐单元格 `1 < val < 100000` 强转，任何中等数字都命中。
- 修复：**列级投票**（`convert_excel.py: _coerced_columns`）——列内 ≥2 个数值
  且全部满足 `30000 < val < 100000`（约 1982–2173 年）才整列转换，
  一票反例否决整列。
- 残留风险：整体落在 30000~100000 的非日期数字列（如月租金 45000 元）
  仍会被误转 → `--no-date-coerce` 兜底关闭。
- 事实基线：真日期 openpyxl 本来就以 `datetime` 返回（number_format 驱动，
  `normalize_cell` 的 datetime 分支），数字分支历史上**只有误报没有漏报**。

## 2. 表头扫描行宽基准（fix-1 lane 实测踩坑）

- 症状：香格里拉 sheet 原始 257 列，表头自动扫描永不触发，前言区检不出。
- 根因：non_empty_ratio（`_row_ratio`）用**原始行宽**做分母，257 列里
  表头行占比永远达不到 0.6 阈值。
- 规则：行占比必须用**尾部裁剪后**的行宽计算——`read_sheet_data` 中
  `_trim_trailing` 必须先于 `_detect_preface` 执行（当前顺序正确，
  改动时不得调换）。

## 3. Excel epoch 与校验锚点

- Excel 序列日期纪元是 **1899-12-30**（`EXCEL_EPOCH`），不是 1900-01-01
  （Excel 1900 闰年 bug）。
- 校验转换正确性用锚点：serial **44927 = 2023-01-01**，不要手算天数。

## 4. 百分比浮点伪影

- 症状：`0.15 * 100 = 15.000000000000002`，渲染成 `15.000000000000002%`。
- 修复：`normalize_cell` 用 `:g` 格式化（`f"{val * 100:g}%"`）。

## 5. bool 是 int 子类

- 数值统计（日期列投票 `_coerced_columns`、百分比/单元格判定
  `normalize_cell` / `excel_serial_to_date`）必须显式排除
  `isinstance(val, bool)`，否则 True/False 会被当 1/0 参与投票。

## 6. markitdown 静默吞损坏文件

- 症状：损坏 pptx 字节被 markitdown 当纯文本转换，rc=0 产出垃圾。
- 修复：`convert_doc.py: main` 魔数守卫——OOXML 必须 `PK` 开头、
  PDF 必须 `%PDF-` 开头，否则拒绝转换。

## 7. pdftoppm 零填充命名随总页数变

- 症状：总页数 <10 时输出 `slide_1-1.png`，≥10 时 `slide_1-01.png`，
  硬编码文件名找不到。
- 修复：`pptx_table_guard.py` escalate 用 glob `slide_{n}-*.png` 兜底。

## 8. python-pptx 限制

- `.ppt`（旧二进制格式）不支持 → `iter_pptx` 报 skipped，不尝试转换。
- shape 迭代必须过滤 `has_table`（`_find_tables`）——SlidePlaceholder
  无 `.table` 属性，直接访问会抛 AttributeError。

## 9. raw 文件名前缀装饰

- 症状：`03-competitors_会员系统_科传_...` 等前缀是分类装饰；
  raw md 与 incoming 原件匹配时只试最长后缀漏掉 22/29 个。
- 修复：`backfill_source.py: raw_suffix_keys` 枚举**所有**含扩展名的
  下划线后缀逐个尝试，而非仅最长后缀。

## 10. 溯源指向政策（P0）

- `source:` 永远指向 incoming 原件（或 30-products 等被 track 的上游 PRD），
  **绝不指向 raw 投影**；authored 件写 `source: "none"`。
- 消费方不得把 `none` 当投影证据引用。

## 11. 批量写素材闸门（任何写 /opt/code/docs 的脚本必须遵守）

1. dry-run 先行，先看清单再落盘；
2. 唯一匹配才写（歧义 → unmatched，不猜）；
3. 分桶上限（如 150）防一次失控写穿；
4. validator 前后基线 diff 必须零新增错误；
5. has-source 的文件绝不重写。

## 12. pre-commit hook

- 改 SKILL.md / AGENTS.md 会触发 `check_skill_ecosystem.sh --ci`；
  提交前本地先跑一遍，避免 hook 拦截后返工。

## 基线测试

`tests/test_golden_fixtures.py` 钉住两个驱动本周修复的金样例
（福州香格里拉 xlsx / 明源产品拆分 pptx），sha 漂移即 FAIL 提示更新预期。

## 13. markitdown pptx shape-type 限制 → 渲染+OCR 升级

**症状**：`markitdown` rc=1，`PptxConverter threw NotImplementedError: Shape instance of unrecognized shape type`；文件本身合法（PK 魔数，python-pptx 可解析）。
**根因**：markitdown 的 pptx 转换器不支持部分异形 shape 类型，是提取器限制非文件损坏。
**修复**：走升级路径 `pptx_table_guard.py escalate --slides 1..N`（soffice→pdf→pdftoppm 渲染）+ `ocr_extract.py`（DeepSeek-OCR-2）。2026-10-16 生产实证：2 个失败 deck（14+40 页）经此路径完整救回，21 列合并表头以 rowspan/colspan 结构恢复。raw 投影头部标 `fidelity: visual-ocr`。

## 14. pptx 媒体引用名映射（含音频/NULL rel 边角）

**症状**：markitdown 产物的 `![](楼栋png.jpg)` 类引用悬空，python-pptx 图片迭代找不到对应形状。
**根因与修法**：markitdown 引用名来自 shape 的 cNvPr `name`（含非图片填充形状）；提取要走 slide XML：`cNvPr-name → a:blip/@r:embed → slide rels → media`。三个边角（2026-10-16 实测）：
- 引用名像 `.jpg` 实为内嵌音频（背景音乐 MP3）→ 按 zip 真实类型保存为 mp3；
- 源 pptx 关系 `Target="NULL"`（作者自剥图）→ 无物可救，引用留痕并记录原因；
- 重复 shape 名按 slide 顺序消费候选。

## 15. 批量转换展平命名三层坑

**症状**：批量转换后 raw 出现 `xxx~a1b2c3.md` 撞名、部分文件 OSError Errno 36、markdown 内容存成 `.xlsx` 扩展名。
**修法**（2026-10-16 竞对批量 572 件实证）：
- 撞名：incoming 内部重复包展平后同名 → 按 sha256 去重，或嵌入源父目录段消歧，禁止 `~hash` 作为最终名（破坏后缀解析约定）；
- Errno 36：文件名 >255 字节 → fit() 截断至 ≤240 字节，产物从暂存区按映射归位；
- 错扩展名：按内容判别（`<!--` 开头 = markdown）重命名 `.md`，勿信扩展名。
