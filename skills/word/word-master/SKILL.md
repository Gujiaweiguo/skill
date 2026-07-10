---
name: word-master
description: |-
  专业 Word 文档创作 Skill。基于 `结构化内容包 + python-docx 模板引擎` 方案，
  通过 python-docx 编程生成格式统一、可继续编辑的 .docx 文件。
  专为正式商务文档设计，支持封面模板、章节样式系统、表格模板库、
  页眉页脚、目录自动生成、附录管理等企业级文档需求。
  触发场景："出标书"、"生成技术方案"、"做投标文件"、"写正式方案"、
  "做一份正式文档"、"商务标"、"技术标"、"资质汇编"、"投标文件汇编"、
  "Word文档"、"正式报告"、"方案书"。
  当业务 Skill（如 bid-doc-master、project-proposal-generator）输出 Word 内容包时，
  此 Skill 负责最终的格式排版和文档生成。也支持基于模板直接创建。
compatibility: >
  Requires Python 3.10+ with python-docx.
  Provides a `pyproject.toml` for deterministic dependency setup.
  Degrades gracefully: output structured Markdown if python-docx unavailable.

  Quick start:
  ```bash
  # 安装依赖（一次性的）
  cd /opt/code/skill/skills/word/word-master
  uv sync
  ```

  上游业务 Skill 输出 Word 内容包后自动调用：
  - bid-doc-master → "生成技术标" → word-master 解析 → 输出 .docx
  - project-proposal-generator → "生成立项建议书" → word-master 解析 → 输出 .docx
  - company-intro-generator → "生成方案书" → word-master 解析 → 输出 .docx
---

# Word Master — 专业文档创作 Agent Pipeline

## DocSpec 质量基线

本 skill 渲染的 Word 内容包、正式 Word 文档和模板说明必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `PPT与Word内容包质量规范.md` 和 `文档验收清单.md`。内容包解析、模板选择、表格、图片、目录和降级产物必须可检查。

基于 `结构化内容包 + python-docx 模板引擎` 方案，上游 Skill 负责"说什么"，
word-master 负责"怎么排"——格式规范、章节管理、表格样式、页眉页脚。

---

## 配置读取

**第一步：设置素材根目录**

```bash
export LANLNK_BASE=/opt/code/docs/lanlnk
```

**第二步：设置路径变量**

| 变量 | 路径 |
|------|------|
| `$WORD_TEMPLATES_DIR` | `/opt/code/skill/skills/word/word-master/templates` |
| `$PROPOSALS_DIR` | `$LANLNK_BASE/out/proposals` |
| `$BIDDING_DIR` | `$LANLNK_BASE/out/bidding` |

---

## 业务流程

```
上游业务 Skill 输出 Word 内容包
        ↓
P0: 环境检测 + 输入解析
        ↓
P1: 模板选择（封面/章节/表格）
        ↓
P2: 文档生成（逐章构建）
        ↓
P3: 格式后处理（目录/页眉页脚/页码）
        ↓
P4: QA 验收 + 交付
```

---

## P0: 环境检测与输入解析

### 0.1 环境检测

```
1. python-docx 可用？ → 可生成 .docx
2. 模板文件存在？ → 可加载封面/页眉模板
3. 内容包解析成功？ → 继续
```

### 0.2 输入类型判断

| 输入类型 | 处理方式 |
|---------|---------|
| **结构化 Word 内容包 `*.word-content.md`** | 解析并渲染（标准方式） |
| **已有 .docx 模板 + 大纲** | 修改模板文件，替换/追加内容 |
| **纯大纲/要点** | 按标准模板新建，填充内容 |
| **已有文稿/文章** | 提取核心内容，按章节结构重组 |

### 0.3 Word 内容包格式

业务 Skill 输出的 Word 内容包（`.word-content.md`）遵循 [Word 内容包格式规范](./reference/word-content-package-spec.md)。

**核心结构速览：**

```
📄 *.word-content.md
├── YAML frontmatter: 元数据 + 封面 + 页眉页脚 + 目录设置 + 素材引用
└── 章节列表
    ├── heading-1（章，page_break）
    │   ├── heading-2（节）
    │   ├── heading-3（小节）
    │   ├── 正文段落 / 列表 / 图片
    │   └── table: function-matrix / comparison-table / pricing-table / ...
    └── 附录
```

详细字段说明、表格类型、页眉页脚协议、模板枚举等请参考完整规范文档。

### 0.4 内容包解析引擎

word-master 内置 python-docx 渲染引擎，部署在 `src/` 目录：

```
src/
├── __init__.py          # 包导出
├── parser.py            # 内容包解析器 (.word-content.md → ContentPackage)
├── renderer.py          # 文档渲染器 (ContentPackage → .docx)
├── table_styles.py      # 表格样式系统 (function-matrix / pricing-table / ...)
└── main.py              # CLI 入口

用法:
    cd /opt/code/skill/skills/word/word-master
    uv run python -m src.main <内容包路径>
    uv run python -m src.main <内容包路径> --output 输出路径.docx

测试:
    uv run python -m src.main test/test.word-content.md -v
```

### 0.5 内容包校验器

渲染前用 `scripts/validate_package.py` 校验内容包，提前拦截格式错误：

```bash
cd /opt/code/skill/skills/word/word-master
export LANLNK_BASE=/opt/code/docs/lanlnk

# 校验单个文件
uv run scripts/validate_package.py <内容包.word-content.md>

# 校验目录下所有内容包
uv run scripts/validate_package.py $LANLNK_BASE/out/proposals/

# 详细输出（显示警告）
uv run scripts/validate_package.py <路径> --verbose

# JSON 输出（供程序调用）
uv run scripts/validate_package.py <路径> --json
```

校验规则：
- **P0 错误**（阻断渲染）：frontmatter 缺失/未闭合、YAML 解析失败、title 为空、type/template 枚举值无效、header/footer 非字典、table 缺少 table_data
- **P1 警告**（不阻断）：date 格式不规范、cover.title 为空、toc.max_level 超范围、图片/素材路径不存在、表格列数不一致

---

## P1: 模板选择

### 1.1 模板体系

根据文档类型选择对应模板：

| 文档类型 | template 字段 | 封面模板 | 章节样式 | 默认字体 |
|---------|-------------|---------|---------|---------|
| 技术标 | bidding-technical | `templates/bidding-technical-base.docx` | 正式/微软雅黑标题/宋体正文 | H1=微软雅黑16pt加粗，正文=宋体12pt，行距1.5 |
| 商务标 | bidding-commercial | `templates/bidding-commercial-base.docx` | 正式/微软雅黑标题/宋体正文 | 深红调封面，页脚机密标记，报价表金额右对齐 |
| 投标文件汇编 | bidding-compilation | `templates/bidding-technical-base.docx` | 正式/微软雅黑标题/宋体正文 | 复用技术标模板 |
| 方案书 | proposal | `templates/bidding-technical-base.docx` | 商务/微软雅黑 | 复用技术标模板，修改封面信息 |
| 立项报告 | report | `templates/bidding-technical-base.docx` | 商务/微软雅黑 | 复用技术标模板 |
| 公司介绍 | intro | `templates/bidding-technical-base.docx` | 商务/微软雅黑 | 复用技术标模板 |

### 1.2 模板文件结构

模板文件为完整基础模板（含封面样式 + 页面设置 + 标题样式体系 + 页眉页脚 + 表格样式），word-master 在模板基础上填充章节内容，无需"查找替换"：

```
templates/
├── bidding-technical-base.docx      # 技术标基础模板（蓝色调封面 + 样式体系）
├── bidding-commercial-base.docx     # 商务标基础模板（红色调封面 + 报价表样式）
├── company-intro-template/          # 公司介绍模板
│   ├── company-intro.word-content.md  # 内容包模板（6章标准结构）
│   └── README.md                      # 使用说明
└── _analysis_report.json            # 模板分析报告（技术参考）
```

**公司介绍模板**适用于：客户要求提供公司介绍、资质、案例清单、合同信息的场景。复制内容包 → 更新业绩和案例数据 → word-master 生成。
3. 章节样式：使用 python-docx 默认样式

---

## P2: 文档生成（逐章构建）

### 2.1 章节处理

根据内容包的章节列表逐章构建：

| 内容包元素 | word-master 处理 |
|-----------|----------------|
| `heading-1` 章节 | 分页 + H1 样式 |
| `heading-2` 小节 | H2 样式，不分页 |
| `heading-3` 子节 | H3 样式 |
| 普通段落 | 正文样式，自动缩进 |
| 列表项（`-`） | 项目符号列表 |
| 编号项（`1.`） | 编号列表 |
| 引用块（`>`） | 正文引用样式 |
| `注意`/`警告` | 特殊样式（灰色底纹/黄色底纹） |

### 2.2 表格生成

根据内容包中的 table 类型选择对应表格样式：

| table 类型 | 用途 | 样式特点 |
|-----------|------|---------|
| `function-matrix` | 功能模块清单 | 表头蓝色底纹+白色字，隔行灰色底纹 |
| `implementation-plan` | 实施计划 | 表头深蓝底纹+白色字，行高固定 |
| `personnel-matrix` | 人员配置 | 表头深蓝底纹+白色字，含证书列 |
| `pricing-table` | 报价明细 | 表头深蓝底纹+白色字，汇总行加粗 |
| `comparison-table` | 对比分析 | 表头深蓝底纹+白色字，对比列高亮 |
| `default-table` | 通用表格 | 表头灰色底纹+加粗，基础边框 |

### 2.3 图片处理

- 引用路径以 `$MATERIALS_DIR` 开头 → 替换为实际路径
- 引用路径以 `$LANLNK_BASE` 开头 → 替换为实际路径
- 绝对路径 → 直接加载
- 路径无效 → 插入占位符并提示："⚠️ 图片未找到：{路径}"

### 2.4 交叉引用（投标专用）

投标文件中常见的交叉引用需求：

| 引用类型 | 内容包写法 | word-master 处理 |
|---------|-----------|----------------|
| 章节引用 | `见第一章` | 自动填充章节号 |
| 表格引用 | `见功能模块清单表` | 自动编号+交叉引用 |
| 资质引用 | `详见附件一：ISO认证` | 自动链接到附录 |
| 评分响应 | `评分项1：见技术方案2.1节` | 双向引用（评分表←→技术方案） |

---

## P3: 格式后处理

### 3.1 封面生成

- 有模板：加载模板封面，填充标题/副标题/日期
- 无模板：自动创建封面页，居中排版

### 3.2 目录自动生成

```
目录格式（投标标准）：
目  录

一、投标函 ................................... 1
二、法定代表人证明 ........................... 3
三、项目概述 ................................. 5
    3.1 项目背景 .............................. 5
    3.2 建设目标 .............................. 7
四、技术方案 ................................. 10
...
```

- 合并所有 heading-1 章节标题（带编号）
- heading-2 缩进展示
- 页码自动链接

### 3.3 页眉页脚

- 奇数页/偶数页/首页不同（投标要求）
- 页眉：左公司名称 + 右项目名称
- 页脚：机密标记 + 居中页码 + 总页数
- 页码从封面后开始编号

### 3.4 编号体系

```
投标标准编号：
第一章
  第一节
    一、标题
      1. 标题
        （1）标题
```

- 自动为 heading-1 → `一、二、三...`
- heading-2 → `（一）（二）（三）...`
- heading-3 → `1. 2. 3....`
- 章节编号与目录编号一致

---

## P4: QA 验收

### 4.1 完整性检查

- [ ] 所有章节内容已填充（无空白页）
- [ ] 表格数据完整（无空行/断列）
- [ ] 图片路径有效（无断链）
- [ ] 目录页数与实际匹配

### 4.2 格式一致性检查

- [ ] 所有 heading-1 使用同一样式
- [ ] 所有 heading-2 使用同一样式
- [ ] 所有表格样式一致
- [ ] 页眉页脚在全文统一
- [ ] 页码连续不中断

### 4.3 投标专项检查

- [ ] 封面信息完整（项目名称+投标单位+日期）
- [ ] 营业执照等基本资质已附
- [ ] 密封标记/机密标记正确
- [ ] 页码从封面后开始编号（封面不编号）
- [ ] 目录页码指向正确章节

### 4.4 输出报告

```
✅ 文档已生成
📁 位置：$BIDDING_DIR/正祥广场投标/
📄 文件：
   - 正祥广场_技术标_20260615.docx（已生成）
   - 正祥广场_商务标_20260615.docx（已生成）
   
📐 模板：bidding-technical（技术标标准模板）
📊 章节数：8章 | 表格数：6个 | 总页数：约85页
```

---

## 与兄弟 Skill 的关系

```
business/project-proposal-generator → Word 内容包 → word-master → 立项建议书.docx
business/bid-doc-master             → Word 内容包 → word-master → 技术标.docx / 商务标.docx
business/company-intro-generator    → Word 内容包 → word-master → 方案书.docx
        ↓
office/ppt-master（PPT 设计）
office/pdf-toc-master（PDF 目录提取）
```

word-master 专注于**文档格式与排版**，不涉及内容策划。
上游业务 Skill 专注于**内容策略与素材匹配**，不涉及格式细节。
