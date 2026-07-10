# DocSpec - 文档质量规范包

DocSpec 是 `/opt/code/skill` 下所有文档类 skill 与 skill 写作本身的质量基线。它先作为共享规范运行，稳定后再抽象成独立质量评审 skill。

## 适用范围

必须引用 DocSpec 的场景：

| 类型 | 覆盖 skill / 文档 |
|---|---|
| 产品规划 | `product-prd-generator`、PRD、功能清单、差距分析、需求证据表 |
| 售前与投标 | `company-intro-generator`、`project-proposal-generator`、`bid-doc-master`、方案书、立项报告、投标文件 |
| 战略与评估 | `strategy-brief-generator`、`requirement-evaluator`、战略简报、需求满足度评估 |
| 手册与知识库 | `doc-generator`、`ops-manual-generator`、用户手册、部署手册、维护手册、RAG 知识库版 |
| Office 内容包 | `word-master`、`ppt-master`、`mckinsey-pptx`、`frontend-slides`、Word/PPT 内容包 |
| 报价与表格 | `pricing-generator`、报价单、功能报价清单、方案对比表 |
| skill 编写 | 新增/修改 `SKILL.md`、`references/`、`troubleshooting.md`、跨 skill 维护规则 |

## 如何使用

### 不写 skill 时怎么用

当只是人工/agent 写一份文档，不新增 skill：

1. 写前填 Doc Brief：受众、用途、输入来源、输出格式、交付边界、待确认项。
2. 写中按文档类型选择专项规范，建立证据链、覆盖矩阵或响应矩阵。
3. 写后跑 `文档验收清单.md`，把未通过项转成 `待确认/缺口/风险`。
4. 交付时说明验证方式，不把猜测写成结论。

### 写或改 skill 时怎么用

1. 先读 `Skill写作质量规范.md`。
2. 在 skill 的流程、输出、验收、禁止事项里接入 DocSpec。
3. 如果经验影响多个文档类 skill，写入本目录；只影响单个 skill，写入该 skill 的 `SKILL.md` 或 `references/troubleshooting.md`。

## 文件说明

| 文件 | 用途 |
|---|---|
| `DocSpec-通用文档质量规范.md` | 所有文档共用的质量门禁 |
| `文档类Skill适配规范.md` | 文档生成类 skill 如何接入 DocSpec |
| `Skill写作质量规范.md` | 写 skill / references / troubleshooting 的规范 |
| `PRD质量规范.md` | PRD 与产品规划文档规范 |
| `方案与投标文档质量规范.md` | 公司介绍、方案、立项、投标文档规范 |
| `手册与知识库文档质量规范.md` | 操作手册、部署维护手册、RAG 知识库规范 |
| `PPT与Word内容包质量规范.md` | PPT/Word 内容包和正式文档规范 |
| `文档验收清单.md` | 交付前检查清单 |
| `复利工程迭代机制.md` | 如何通过复利工程持续完善 DocSpec |

## 权威位置

- 权威规范：`/opt/code/skill/references/docspec/`
- 跨 skill 入口：`/opt/code/skill/AGENTS.md`
- 复利入口：`/opt/code/skill/skills/meta/compound-learning/SKILL.md`
- 业务资料入口：`$LANLNK_BASE/knowledge/README.md` 可引用本目录，但不复制规范正文。
