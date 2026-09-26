# multi-company-strategy Specification

## Purpose
TBD - created by archiving change company-agnostic-skills. Update Purpose after archive.
## Requirements
### Requirement: company.yaml 驱动的路径解析
strategy-brief-generator SHALL 从当前公司 company.yaml 解析：战略根（`strategy.root`，拼接分析主题，主题默认「<domain>战略」可由用户指定）、方法论源（`strategy.methodology_ref`）、自身盘点输入（products[].code_root 非空读源码路径、空则引用 materials 素材）。MUST NOT 在 SKILL.md 中写死任何公司名、产品名或「商业地产信息化战略」类域名。

#### Scenario: lianyou 主题解析
- **WHEN** 以 lianyou 为当前公司发起战略分析且未指定主题
- **THEN** 输出根为 lianyou/out/strategy/医药监管科技战略/（domain 取自 company.yaml）

#### Scenario: lanlnk 存量主题兼容
- **WHEN** 以 lanlnk 为当前公司分析且主题指定「商业地产信息化战略」
- **THEN** 输出根与改造前一致（out/strategy/商业地产信息化战略/）

#### Scenario: methodology_ref 分支
- **WHEN** methodology_ref 为 null（lianyou）
- **THEN** P2 方法论归纳跳过，直接使用内置通用四看框架
- **WHEN** methodology_ref 非空（lanlnk 指向明源资料位）
- **THEN** P2 从该目录归纳方法论，并保留「方法论模板 vs 竞品证据」双重角色管理规则

### Requirement: 四看框架政策维度
通用四看「看市场」SHALL 固定包含「政策与监管环境」子项（政府行业政策/监管趋势/合规压力/政策机会窗口）。当 company.yaml `industry_profile.policy_driven: true` 时：P5 市场信号整理 MUST 单独产出 `parsed/market/政策监管信号.md`（本地政策资料引用 + 联网检索，逐条带来源），P8 简报看市场章节 MUST 含政策独立小节。

#### Scenario: 政策驱动型行业升格
- **WHEN** lianyou（policy_driven: true）运行战略分析
- **THEN** parsed/market/政策监管信号.md 存在且每条信号带来源，简报含「政策与监管环境」独立小节

#### Scenario: 非政策驱动型不删除维度
- **WHEN** lanlnk（policy_driven: false）运行战略分析
- **THEN** 政策作为看市场常规子项保留（并入市场信号，不独立成文）

### Requirement: 产品机会清单输出与反哺
P8 输出 SHALL 固定包含 `output/产品机会清单.md`：每条机会含机会名/证据 ID（回链 evidence-ledger）/目标客户/建议优先级/与现有产品关系（新/扩展/替代）；文件头部 SHALL 含操作指引——用户确认机会后在 docs 仓库执行 `scripts/onboard.sh product <company> <pid> --name <名>` 完成配置反哺。

#### Scenario: 清单结构完整
- **WHEN** lianyou 战略简报生成完成
- **THEN** output/产品机会清单.md 存在，条目字段齐全且证据 ID 可在 evidence-ledger 中查到

#### Scenario: 反哺指引可执行
- **WHEN** 用户按清单指引执行 onboard.sh product
- **THEN** company.yaml products 增长且新条目含 name（来源即清单机会名）

### Requirement: 公司叙事外置加载
strategy-brief-generator SKILL.md SHALL 只保留通用引擎方法论；公司专属写作约束 SHALL 外置到 `<company>/config/sales-playbook/strategy-brief.md`，P0 公司确定后如该文件存在则 MUST 加载为写作约束。蓝联原「设计决策」章（B/D 路线、岗位病药矩阵、蓝联整体视角、30/60 天交付口径、可达度表述等）SHALL 原文迁移至 `lanlnk/config/sales-playbook/strategy-brief.md`，skill 内留指针。

#### Scenario: lanlnk 叙事不变
- **WHEN** 以 lanlnk 运行战略分析
- **THEN** sales-playbook/strategy-brief.md 被加载，B/D 路线等写作约束生效（与改造前等价）

#### Scenario: lianyou 无叙事文件不报错
- **WHEN** lianyou 无 config/sales-playbook/
- **THEN** 跳过加载，按通用引擎执行，无警告级以上输出

### Requirement: 输入目录公司自定二级结构
输入目录 SHALL 保持五分类抽象（00-methodology/01-market/02-industry-workflow/03-competitors/04-self），二级子目录（如 lanlnk 的商管系统/会员系统竞品树）SHALL 由公司域知识决定而非 skill 写死；skill 文档中的目录示例 MUST 标注「示例为 lanlnk 实例化」。

#### Scenario: lianyou 竞品目录自由命名
- **WHEN** lianyou 的 input/03-competitors/ 下按监管科技行业建子目录（如 追溯系统厂商/）
- **THEN** P3 竞品抽取按实际目录结构工作，不因非蓝联命名而失败

