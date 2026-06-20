# Word 内容包格式规范 v1.0

## 概述

Word 内容包（Word Content Package）是**业务 Skill → word-master** 之间的标准数据交换格式。
业务 Skill 负责"说什么"（内容策略、章节编排、数据表格），
word-master 负责"怎么排"（模板选择、章节样式、表格格式、页眉页脚）。

与 PPT 内容包（`.content.md`）不同，Word 内容包侧重 **文档结构 + 表格数据 + 章节排版**，
而非页面视觉设计。

## 文件格式

- 格式：Markdown + YAML frontmatter
- 编码：UTF-8
- 扩展名：`.word-content.md`
- 存放目录：`{项目目录}/content-packages/`
  - 立项报告：`$PROPOSALS_DIR/{项目}/content-packages/`
  - 方案书/公司介绍：`$PROPOSALS_DIR/content-packages/`
  - 投标文件：`$BIDDING_DIR/content-packages/`

## 完整结构

```markdown
---
# ========== 元数据 ==========
title: "项目名称 + 文档类型"
project: "客户项目名称"
client: "客户单位全称"
type: "technical | commercial | proposal | report | intro"
template: "bidding-standard | bidding-technical | bidding-commercial | proposal | report"
date: "2026-06-15"
author: "蓝联科技"

# ========== 封面信息 ==========
cover:
  title: "正祥广场会员系统"
  subtitle: "技术方案"
  version: "V1.0"
  confidential: true                    # true → 封面标注"机密"

# ========== 页眉页脚 ==========
header:
  left: "蓝联科技"                       # 左：公司名
  right: "正祥广场会员系统技术方案"         # 右：项目名称 + 文档类型
footer:
  left: "机密"                           # 左：密级标记
  center: ""                             # 中：留空
  right: "第 {page} 页"                  # 右：页码占位符

# ========== 目录设置 ==========
toc:
  enabled: true                          # 是否生成目录
  max_level: 3                           # 目录深度（1-3级标题）
  include_heading: false                 # 目录标题"目录"是否计入目录页

# ========== 素材引用 ==========
sources:
  - path: "$MATERIALS_DIR/03-products/商圈会员CRM系统.md"
    type: 产品方案
  - path: "$MATERIALS_DIR/04-cases/时尚天河CRM会员营销.md"
    type: 客户案例
  - path: "$MATERIALS_DIR/07-personnel/项目团队架构.md"
    type: 人员配置
---

# 章节列表

<!--
每章为一个标题 + 内容块。
word-master 根据 style/table 字段选择对应排版方式。
page_break: true → 该章节前插入分页符。
-->

## 第一章 项目概述

```yaml
style: heading-1
page_break: true
```

项目正文段落... 正文使用标准字体（宋体12pt，行距1.5倍）。

### 1.1 项目背景

```yaml
style: heading-2
```

背景描述正文...

### 1.2 建设目标

```yaml
style: heading-2
```

- 建立统一的会员管理体系
- 实现全场积分互通
- 打造数字化营销能力

## 第二章 技术方案

```yaml
style: heading-1
page_break: true
```

### 2.1 系统架构

```yaml
style: heading-2
```

系统采用微服务架构...

### 2.2 功能模块清单

```yaml
style: heading-2
table: function-matrix
table_data:
  header: ["模块", "功能", "描述", "优先级"]
  column_widths: [15, 15, 45, 10]        # 列宽百分比（可选）
  rows:
    - ["会员管理", "会员注册", "支持手机号+微信快速注册", "P0"]
    - ["会员管理", "等级管理", "普卡-银卡-金卡-钻石四级", "P0"]
    - ["积分体系", "消费积分", "全场消费自动累积积分", "P0"]
    - ["停车服务", "停车缴费", "消费免停、积分抵扣", "P1"]
    - ["营销工具", "优惠券", "满减/折扣/秒杀券", "P0"]
```

## 第三章 项目实施计划

```yaml
style: heading-1
page_break: true
table: implementation-plan
table_data:
  header: ["阶段", "时间", "工作内容", "交付物"]
  column_widths: [12, 10, 40, 28]
  rows:
    - ["需求调研", "第1-2周", "现场调研、需求确认", "需求规格说明书"]
    - ["系统设计", "第3-4周", "架构设计、UI设计", "设计文档"]
    - ["开发实施", "第5-10周", "迭代开发", "可运行系统"]
    - ["测试验收", "第11-12周", "功能测试、UAT", "测试报告"]
    - ["上线部署", "第13周", "生产环境部署", "上线确认"]
```

## 第四章 人员配置

```yaml
style: heading-1
page_break: true
table: personnel-matrix
table_data:
  header: ["角色", "姓名", "职责", "证书"]
  column_widths: [15, 12, 45, 18]
  rows:
    - ["项目总监", "待确认", "项目整体把控", "PMP"]
    - ["高级项目经理", "待确认", "项目进度管理", "PMP"]
    - ["技术总监", "待确认", "技术架构设计", "高级工程师"]
    - ["研发经理", "待确认", "开发管理", ""]
```

## 第五章 售后服务

```yaml
style: heading-1
page_break: true
```

### 5.1 服务内容

```yaml
style: heading-2
```

- 7×24小时技术支持
- 每月系统巡检
- 季度运维报告
```

---

## 元数据字段说明

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `title` | ✅ | string | 文档标题，显示在封面和页眉 |
| `project` | ✅ | string | 项目名称 |
| `client` | ✅ | string | 客户单位全称 |
| `type` | ✅ | enum | 文档类型，决定模板选择 |
| `template` | ✅ | enum | 封面/风格模板 |
| `date` | ✅ | string | 文档日期 |
| `author` | ✅ | string | 文档作者/公司 |
| `cover` | ❌ | object | 封面自定义信息 |
| `header` | ❌ | object | 页眉配置 |
| `footer` | ❌ | object | 页脚配置 |
| `toc` | ❌ | object | 目录设置 |
| `sources` | ❌ | array | 素材引用列表 |
| `format_overrides` | ❌ | dict | 格式覆盖（响应招标格式要求） |

### format_overrides 字段说明

当投标文件有明确的格式要求时，AI 从招标文件中提取结构化格式覆盖数据，经 `format_overrides` 字段传递给 word-master，使其在模板基础上应用招标要求的格式。

```yaml
format_overrides:
  font:
    body: '宋体'              # 正文字体
    heading: '黑体'            # 标题字体
    ascii: 'Times New Roman'   # 西文字体
    size: 12                   # 正文字号（pt）
    heading_1_size: 16         # 一级标题字号（可选）
    heading_2_size: 14         # 二级标题字号（可选）
  margins:
    top: 2.54
    bottom: 2.54
    left: 3.17
    right: 3.17
  page:
    size: 'A4'                 # A4 / A3 / Letter
    orientation: 'portrait'    # portrait / landscape
  line_spacing: 1.5            # 行距
```

**优先级**：`format_overrides` > 模板样式 > word-master 默认样式。
启用流程：<br/>
1. 加载基础模板 → 2. 应用 `format_overrides` 覆盖 → 3. 渲染内容

### type 枚举值

| type | 适用文档 | 默认模板 |
|------|---------|---------|
| `technical` | 技术标、技术方案 | `bidding-technical` |
| `commercial` | 商务标 | `bidding-commercial` |
| `proposal` | 方案书、产品介绍 | `proposal` |
| `report` | 立项建议书、调研报告 | `report` |
| `intro` | 公司简介 | `proposal` |

### template 枚举值

| template | 适用场景 | 封面特征 |
|----------|---------|---------|
| `bidding-standard` | 投标文件通用 | 投标专用封面，含项目编号/投标单位 |
| `bidding-technical` | 技术标 | 技术标封面，蓝色调 |
| `bidding-commercial` | 商务标 | 商务标封面，红色调 |
| `proposal` | 方案书/公司介绍 | 标准商务封面，含副标题/版本 |
| `report` | 立项建议书/报告 | 简约封面，侧重标题+日期 |

---

## 章节元素说明

### 标题层级

| style | 对应 Word 样式 | 字体 | 字号 | 用途 |
|-------|---------------|------|------|------|
| `heading-1` | Heading 1 | 黑体/微软雅黑 | 16pt | 章标题（第一章、第二章...） |
| `heading-2` | Heading 2 | 黑体/微软雅黑 | 14pt | 节标题（1.1、1.2...） |
| `heading-3` | Heading 3 | 黑体/微软雅黑 | 12pt | 小节标题（1.1.1、1.1.2...） |
| `heading-4` | Heading 4 | 黑体/微软雅黑 | 11pt | 更低层级 |

### 分页控制

| 参数 | 值 | 效果 |
|------|-----|------|
| `page_break` | `true` | 该章节前插入分页符 |
| `page_break` | `false`（默认） | 连续排版，不分页 |

建议：每个 `heading-1` 章节前 `page_break: true`，保持每章从新页开始。

### 正文段落

正文段落直接跟在标题块后面，无需 YAML 块包裹：

```yaml
style: heading-2
```

正文在这里直接写...

### 列表

使用标准 Markdown 列表语法，word-master 转为 Word 列表：

```markdown
- 第一项
- 第二项
  - 子项
```

### 图片引用

```markdown
![架构图]($MATERIALS_DIR/03-products/architecture.png)
```

- word-master 根据路径读取图片插入文档
- 图片路径统一使用 `$MATERIALS_DIR` 变量
- 支持 `png`、`jpg`、`svg` 格式

---

## 表格类型

| table 类型 | 用途 | 样式特征 |
|-----------|------|---------|
| `default-table` | 通用表格 | 标准边框，表头灰底加粗 |
| `comparison-table` | 对比/响应表 | 左列加粗，交替行色 |
| `function-matrix` | 功能清单 | 多列功能表，首列合并同类行 |
| `pricing-table` | 预算/报价表 | 右列右对齐（金额），底部合计行 |
| `implementation-plan` | 实施计划 | 带阶段行底色标记 |
| `personnel-matrix` | 人员配置 | 含证书列，姓名列可标记"待确认" |
| `comparison` | 商务/技术偏离表 | 招标要求→响应情况→偏离说明三列 |

### 表格结构规范

每个表格必须包含：
- `header`：表头行（字符串数组）
- `rows`：数据行（字符串数组嵌套）
- `column_widths`：列宽百分比（可选，不指定则由 word-master 自动分配）

示例（偏离表）：

```yaml
table: comparison
table_data:
  header: ["招标要求", "响应情况", "偏离说明"]
  column_widths: [35, 35, 30]
  rows:
    - ["提供7×24小时技术支持", "提供7×24小时电话和远程支持", "无偏离"]
    - ["项目经理需持有PMP证书", "项目经理持有PMP证书，5年经验", "优于"]
    - ["需驻场服务", "提供远程+定期驻场", "部分偏离"]
```

---

## 页眉页脚协议

### 页眉

```yaml
header:
  left: "蓝联科技"          # 左对齐 — 通常公司名
  center: ""                # 居中 — 通常留空或放Logo
  right: "正祥广场会员系统技术方案"  # 右对齐 — 通常项目名称+文档类型
```

三栏布局：左、中、右各占一个 tab 位置。

### 页脚

```yaml
footer:
  left: "机密"              # 左对齐 — 密级
  center: ""                # 居中 — 通常留空
  right: "第 {page} 页"     # 右对齐 — 页码
```

页脚页码支持占位符：
- `{page}` — 当前页码
- `{total}` — 总页数
- `第 {page} 页 / 共 {total} 页` → "第 1 页 / 共 35 页"

### 首页不同

封面页自动隐藏页眉页脚（首页不同设置），从正文页（第一章）开始显示。

---

## 目录规范

```yaml
toc:
  enabled: true             # 是否生成目录
  max_level: 3              # 包含到第几级标题
  include_heading: false    # "目录"标题本身是否计入目录
```

- 目录自动插在封面页之后、第一章之前
- 目录页不计页码（显示为罗马数字 i, ii, iii 或取消页码）
- 正文从第一章开始计阿拉伯数字页码

---

## 附录与附件

附录通过 `heading-1` + `page_break: true` 实现，在章节标题中标注"附录"：

```yaml
## 附录A 公司资质

style: heading-1
page_break: true
```

### A.1 营业执照

```yaml
style: heading-2
```

附件的引用方式：

```markdown
详细资质清单见附件：$BIDDING_DIR/资质汇编/蓝联科技资质汇编.pdf
```

word-master 将附件引用转为脚注或附录引用标记。

---

## 文档编号规范

word-master 自动生成文档编号（放在封面/页眉/页脚）：

```
格式：{缩写}-{项目编号}-{文档类型}-{版本号}

示例：
LNK-ZXGCMALL-TEC-V1.0
├── LNK         公司缩写
├── ZXGCMALL    项目拼音缩写
├── TEC         文档类型（TEC技术标/COM商务标/PRP方案书/RPT报告）
└── V1.0        版本号
```

可通过元数据中的 `doc_id` 字段覆盖：

```yaml
doc_id: "LNK-ZXGCMALL-TEC-V1.0"
```

---

## 内容包生成规范

1. 业务 Skill 完成内容编排后，按此格式输出 `.word-content.md`
2. 放入 `{项目目录}/content-packages/` 临时目录
3. word-master 检测到 `.word-content.md` 输入时，按此协议解析生成 `.docx`
4. 内容包本身不包含图片二进制数据，仅引用路径
5. 图片路径统一使用 `$MATERIALS_DIR` / `$PROPOSALS_DIR` / `$BIDDING_DIR` 等变量