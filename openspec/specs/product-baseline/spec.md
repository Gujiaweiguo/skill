# product-baseline Specification

## Purpose
TBD - created by archiving change simplify-product-baseline-to-three-layers. Update Purpose after archive.
## Requirements
### Requirement: 产品基线 SHALL 只暴露三层用户可见分层
Skill 的产品基线入口 SHALL 只以三层呈现：本体（ontology，产品世界的对象/术语/规则/能力）、PRD（产品目标与本轮变更）、代码（codebase，当前实现事实）。产品本体层内部允许由多个文件组成，但概念上 SHALL 保持一层；任何 model_kind 式分类 SHALL 仅作为可选内部提示，不得作为用户入口概念。

#### Scenario: 任意产品按三层配置
- **WHEN** 任一已注册产品（lnkcre/lnkreport/lnkchatbi/lnkchat/lnkvision/lnkgateway）被配置或分析
- **THEN** Skill SHALL 只以 本体/PRD/代码 三层组织该产品的基线、规划与实现事实，不要求用户先选择模型分类

#### Scenario: 本体层多文件仍是一层
- **WHEN** LnkCRE 的本体由 business-ontology.yaml 与 domain-model/ 多个文件共同构成
- **THEN** Skill SHALL 将它们整体视为 LnkCRE 的本体层，不拆分为多个用户可见层

### Requirement: 非独立层产物 SHALL 归属到某一层的工作产物
OpenSpec change/测试/验证回执 SHALL 归属代码层；Semantic Release SHALL 归属本体层的发布快照；UI 设计系统约束 SHALL 归属 PRD 内容；竞品分析与客户需求 SHALL 归属 PRD 输入。它们 SHALL NOT 被呈现为独立的架构分层。

#### Scenario: Semantic Release 被定位为本体快照
- **WHEN** 一个 Semantic Release 发布包被生成或消费
- **THEN** Skill SHALL 将其描述为本体层的版本化发布切片，并保留 accepted 状态、完整 source revision 与 commit-scoped evidence 的发布纪律

#### Scenario: OpenSpec 被定位为代码层机制
- **WHEN** 增量 PRD 产出目标仓消费提示词
- **THEN** Skill SHALL 把 OpenSpec change 的创建与归档描述为代码仓内部的实施机制，而非规划层的一部分

### Requirement: 产品注册表 SHALL 覆盖已注册产品且可扩展
Skill SHALL 维护产品注册表，至少覆盖 lnkcre、lnkreport、lnkchatbi、lnkchat、lnkvision、lnkgateway，并支持以单条 entry 扩展未来产品。路径未确认的字段 SHALL 显式为 null 并附 unresolved 说明；未知或未注册产品 SHALL 显式降级说明，不得静默回退到商管 ontology。

#### Scenario: 注册表覆盖六个产品
- **WHEN** 读取产品注册表
- **THEN** 六个已注册产品 SHALL 各有一条 entry，已确认路径与磁盘一致，未确认路径为 null 而非编造值

#### Scenario: 未注册产品不静默套用商管语义
- **WHEN** 分析一个注册表中不存在的产品
- **THEN** Skill SHALL 输出显式的 unresolved/降级说明，不得把商管 ontology 或 CRE 模块当作该产品默认本体

### Requirement: legacy model_kind 值 SHALL 保持可解析
既有 model_kind 枚举值（business-ontology / capability-model / operational-domain-model / product-runtime-model / semantic-release）SHALL 继续被 schema 接受，且该字段 SHALL 为可选；包含 legacy 值的既有产物 SHALL 不因本次术语收敛而失效。

#### Scenario: 旧配置继续通过校验
- **WHEN** 一份带有 `model_kind: operational-domain-model` 的既有产品配置被解析
- **THEN** 校验 SHALL 通过，该字段被当作内部提示而非分层入口

