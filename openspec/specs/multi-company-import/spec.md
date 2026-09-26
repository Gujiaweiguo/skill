# multi-company-import Specification

## Purpose
TBD - created by archiving change company-agnostic-skills. Update Purpose after archive.
## Requirements
### Requirement: 公司基座解析与无静默默认
material-importer 的所有脚本（batch_competitor_import.py / case_matcher.py / scan_raw_index.py 及后续新增入口）SHALL 按 `COMPANY_BASE || LANLNK_BASE` 顺序解析公司根目录，解析后 MUST 校验 `<base>/config/company.yaml` 存在；未设变量或校验失败时 MUST 以非零码退出并输出修复提示（含 export 示例），MUST NOT 回退到任何硬编码默认公司路径。CLI 显式路径参数（如 --raw-dir）优先于 env 推导。

#### Scenario: COMPANY_BASE 指向 lianyou
- **WHEN** `COMPANY_BASE=/opt/code/docs/lianyou` 时运行 scan_raw_index.py
- **THEN** raw/materials 目录均解析到 lianyou 下，行为与 LANLNK_BASE 等价

#### Scenario: 变量缺失报错
- **WHEN** 两个变量均未设置时运行任一脚本
- **THEN** 非零码退出，错误信息含 export COMPANY_BASE 示例，无文件写入

#### Scenario: 指向无配置目录报错
- **WHEN** `COMPANY_BASE` 指向的目录无 config/company.yaml
- **THEN** 非零码退出并提示「该目录不是已注册公司（缺 config/company.yaml）」，不自动创建配置

### Requirement: 竞品导入子路径参数化
batch_competitor_import.py SHALL 提供 `--raw-competitors` 与 `--materials-competitors` CLI 参数覆盖默认子路径；未提供时按公司推导：company.yaml products 中恰有一个 prd_ready 产品时用 `raw/prd-<对应产品素材名>/02-competitors`，无法唯一定位时 MUST 报错要求显式传参。lanlnk 现有调用（不传参）行为 MUST 保持不变。

#### Scenario: lanlnk 存量行为不变
- **WHEN** 在 lanlnk（LANLNK_BASE 或 COMPANY_BASE 均可）下按原方式（不传新参数）运行
- **THEN** 仍解析到 raw/prd-商管系统/02-competitors 与 materials/13-competitors

#### Scenario: 多产品歧义报错
- **WHEN** 公司有多个 prd_ready 产品且未传 --raw-competitors
- **THEN** 报错列出候选产品，要求显式传参

### Requirement: 公司级标签优先
P2 分类与素材组织 SHALL 优先读取 company.yaml materials.domain_tags 指向的公司级标签文件（agent 流程步骤）；文件不存在时回退 skill 内置 references/domain-tags.md（现状行为），MUST NOT 因公司文件缺失而失败。case_matcher 的标签始终来自案例 frontmatter 实际数据。

#### Scenario: 公司标签指导分类
- **WHEN** lianyou 的 config/materials/domain-tags.yaml 填入行业标签后 agent 执行 P2 分类
- **THEN** 分类映射参考公司标签文件（如 医药流通/监管合规），而非商管域内置标签

#### Scenario: 缺失回退
- **WHEN** 公司级标签文件不存在
- **THEN** P2 分类参考 skill 内置 domain-tags.md，流程正常完成

### Requirement: SKILL.md 公司路由与文档修正
material-importer SKILL.md 的 P0 章节 SHALL 包含公司确定步骤（cwd 推断 → 用户点名 → 询问，绝不猜默认）与 COMPANY_BASE 导出示例；MUST 修正悬空的 `config/lanlnk.yaml` 引用（改为各公司 `config/company.yaml` + COMPANIES.md 契约引用）；Quick start SHALL 以 COMPANY_BASE 为推荐写法并保留 LANLNK_BASE 兼容说明。

#### Scenario: agent 按 P0 路由
- **WHEN** agent 在 docs 根被要求「入库素材」且未提公司
- **THEN** 按 SKILL.md 指引询问公司（列出 lanlnk/lianyou）后再执行

#### Scenario: 悬空引用清除
- **WHEN** 检查 SKILL.md 全文
- **THEN** 不存在指向 skill 内 config/lanlnk.yaml 的引用，公司结构说明指向 company.yaml 机制

