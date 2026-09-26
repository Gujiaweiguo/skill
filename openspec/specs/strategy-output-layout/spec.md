# strategy-output-layout Specification

## Purpose
TBD - created by archiving change strategy-output-layout-flattening. Update Purpose after archive.
## Requirements
### Requirement: 配置驱动路径解析

战略分析 SHALL 仅从 company.yaml 解析 `strategy.root` 得到 `$STRATEGY_ROOT = <COMPANY_BASE>/<strategy.root>/<主题>`；原始输入、中间产物、材料、交付四个锚点 SHALL 固定为 `<COMPANY_BASE>/{incoming,raw,materials,out}`。SHALL NOT 再定义或创建主题级 input/raw/parsed/review/output 子目录。

#### Scenario: 新主题零流水线目录
- **WHEN** 对任意公司运行完整战略分析流程
- **THEN** 除 out 平铺文件外，仅在 incoming/raw/materials 各出现一个主题相关位置，$STRATEGY_ROOT 下零子目录

#### Scenario: 输入指针归位
- **WHEN** 战略资料入库与登记完成
- **THEN** 《资料来源清单》位于 `incoming/<主题>/`，source-ref 指向真实 OCR 合并文件而非通配名

### Requirement: 可复用产物直接入库

P3 竞品能力矩阵与 P5 政策监管信号 SHALL 直接写入 materials 对应类目（13-competitors / 03-products 类目位）并携带完整 frontmatter；status 字段 MUST 如实表达核验程度。skill MUST NOT 先写 parsed 再人工搬运。P2 方法论归纳（`methodology_ref` 非空时）的统一框架产物 SHALL 入库 `materials/10-methodology/方法论归纳-<来源>-<日期>.md`（带 frontmatter，随 git 分发供后续主题复用）；仅归纳过程稿（差异记录、舍弃版本）留 `raw/<主题>/`。

#### Scenario: 一步入库
- **WHEN** 政策驱动型行业完成市场信号整理
- **THEN** `materials/03-products/政策与市场/政策监管信号.md` 直接存在且 frontmatter 可解析

#### Scenario: 方法论归纳成为可复用资产
- **WHEN** methodology_ref 非空的公司完成 P2
- **THEN** `materials/10-methodology/` 下存在带 frontmatter 的归纳产物；第二个战略主题可直接复用该框架而无需重归纳；归纳差异过程稿仍在 raw/<主题>/

### Requirement: 平铺输出与唯一例外

P8 全部最终产出 SHALL 平铺写入 $STRATEGY_ROOT：总报告、产品机会清单、待确认事项、自身能力盘点为平铺 md；evidence-ledger.json 为唯一非 md/ppt 例外；PPT 由内容包调用渲染层生成后平铺，其生成脚本 MUST 位于 `raw/<主题>/` 且以主题目录为工作目录执行。

#### Scenario: 台账在 git 中
- **WHEN** 列出 $STRATEGY_ROOT
- **THEN** 文件全集为 {总报告, 机会清单, 待确认事项, 自身能力盘点, 资料来源清单*.md※, evidence-ledger.json, pptx}（※资料来源清单若按 docs 决策存 incoming 则不含），无子目录、无 js

### Requirement: 引用与共存约束

产出内部相对链接 SHALL 全部从最终文件位置解析成功；MUST NOT 出现指向 raw 底稿的活动链接；对存量 lanlnk 旧主题 SHOULD 保留「按原样可读」兼容说明而 MUST NOT 要求迁移。

#### Scenario: 兼容存量
- **WHEN** 阅读 SKILL.md 输出契约章节
- **THEN** 包含 lanlnk 存量五层主题不迁移、可读性不受影响的说明

