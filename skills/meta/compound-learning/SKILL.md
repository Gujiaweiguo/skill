---
name: compound-learning
description: OpenCode / oh-my-openagent / OpenSpec 使用过程中的“复利工程”总路由 Skill。用于在一次开发、文档、PRD、方案、调试、部署或交接工作完成后，复盘可复用经验，并分流写入项目知识库、公共 OpenCode 操作手册或 skill 自身维护文档。触发场景：“复利工程”、“沉淀这次经验”、“对这次工作做复盘”、“把这次 OpenCode/PRD/投标/方案经验沉淀一下”。
compatibility: Pure prompt skill. No runtime dependency. Works inside the skill repository and with external docs under $LANLNK_BASE / $USERGUIDE_BASE.
---

# Compound Learning / 复利工程

## 目标

把一次开发、调试、部署、文档、方案、PRD、投标、手册或交接包工作中产生的可复用经验沉淀下来，让下一次更快、更准、更少踩坑。

本 skill 不负责生成 PRD、投标文件、PPT、Word、代码或手册本身；它负责在工作完成后做复盘、分流和持久化。

一句话：**Skill/OpenCode 负责做事，复利工程负责长记性，项目知识库服务 agent，公共手册服务人，OpenSpec 负责改系统。**

## 触发场景

使用本 skill 当用户说：

- “复利工程”
- “沉淀这次经验”
- “对这次工作做复盘”
- “把这次 OpenCode 使用经验沉淀一下”
- “把这次代码/调试/部署经验沉淀一下”
- “把这次 PRD 经验沉淀一下”
- “把这次投标/方案/手册的坑记录下来”
- “以后这类文档/开发任务都按这个模式”

也适用于完成以下工作后的收尾：

- PRD / 产品规划
- 战略简报 / 行业研究
- 公司介绍 / 客户方案
- 立项报告
- 投标文件 / 响应表 / 报价单
- PPT / Word 正式文档
- 操作手册 / 部署维护手册
- 跨系统需求交接包
- OpenCode / OpenSpec 开发流程
- 项目调试 / 部署 / 验证闭环
- skill 自身使用或维护经验

## 不触发场景

- 单纯业务代码细节且不影响 OpenCode 使用方式、项目协作方式或后续 agent 操作
- 一次性内容修改，没有可复用经验
- 未完成、未验证、仍处于猜测的结论
- 涉及密钥、客户敏感数据、内部报价明细等不能持久化的信息

## 工作流程

### Step 1. 回顾本次工作

先列出本次实际产出：

- 用了哪些 skill
- 产出了哪些文件
- 哪些路径是成果文件
- 哪些路径是中间文件
- 是否有用户确认过的新口径
- 是否有非显而易见的 bug、坑、设计决策
- 是否产生了交接包或后续 OpenSpec change 输入

不要根据记忆猜测；必须检查文件或 git diff。

### Step 2. 识别工作类型

| 类型 | 复盘重点 |
|---|---|
| PRD | 术语口径、域知识、分期、PRD vs 代码差异、交接包、需求证据 |
| 战略简报 | 分析框架、竞品证据、市场趋势、结论口径、后续产品路线 |
| 公司介绍/客户方案 | 素材标签、案例匹配、行业话术、客户画像、方案结构 |
| 投标 | 评分点、响应模板、偏离表、报价结构、资质复用、招标限制 |
| PPT | 版式模板、图表表达、视觉风格、客户偏好、内容压缩规则 |
| Word 正式文档 | 内容包格式、模板映射、样式坑、目录/页眉页脚规则 |
| 操作手册 | 页面探测、截图策略、失败容错、RAG 切块、运行环境前置条件 |
| 部署维护手册 | IaC 提取、接口检测、排障 SOP、脱敏规则、回滚方案 |
| 交接包 | 项目边界、接口契约、验收清单、OpenSpec change 拆分 |
| OpenCode / OpenSpec 使用 | 提示词模式、agent/skill 协作、OpenSpec 闭环、验证门禁、失败恢复 |
| 项目开发/调试/部署 | 项目运行时陷阱、环境变量、测试基线、手动 QA、agent 可复用操作规则 |
| skill 自身维护 | 触发边界、已知限制、references、troubleshooting、共享规则 |

### Step 3. 判断是否值得沉淀

应该沉淀：

- 下次会复用的判断方法
- 用户明确确认的术语或产品口径
- 影响多个 skill 的规则
- 某个 skill 的非显而易见限制
- 生成器/模板/格式踩坑
- 诊断和排障流程
- 可复用交接包结构
- 被证明失败的做法及原因

不要沉淀：

- 一次性客户名字或一次性路径
- 显而易见的常识
- 未验证猜测
- 密钥、token、连接串、密码、身份证、手机号等敏感信息
- 客户私密报价、未公开商业条件
- 临时工具输出和中间文件清单

### Step 4. 分流写入位置

先判断经验属于哪个复利通道，再写入唯一权威位置。

#### 通道 A：项目内复利（给 agent 用）

适用：只影响当前项目、当前代码库、当前运行环境或当前业务域的经验。

| 经验类型 | 写入位置 |
|---|---|
| 项目运行时陷阱、环境配置、测试基线 | 目标项目 `AGENTS.md` |
| 项目排障 SOP、部署/验证步骤 | 目标项目 `docs/troubleshooting.md`、`docs/*.md` |
| 项目领域术语、边界、验收口径 | `$LANLNK_BASE/prd/<项目>/域知识.md` 或目标项目 docs |
| 需要改系统行为 | 回到目标项目 OpenSpec，不在复利工程里直接改代码 |

例：LnkChatBI 的 `SECRET_KEY` 必须显式设置、`cre_bi_demo` 需要 `SET search_path`、某项目已知测试 fake 签名问题。

#### 通道 B：公共 OpenCode 使用复利（给人用）

适用：适用于多个项目、多个 OpenCode session，能帮助人更好操作 OpenCode / oh-my-openagent / OpenSpec 的经验。

| 经验类型 | 写入位置 |
|---|---|
| 日常开发流程、BUG 修复、大任务规划、agent 协作 | `/opt/code/docs/opencode/10-实战手册/README.md` |
| OpenSpec 目录、产物、验证、归档、测试门禁 | `/opt/code/docs/opencode/20-OpenSpec流程/README.md` |
| 提示词模板、模型选择、压缩/交接口令 | `/opt/code/docs/opencode/30-提示词与模型/README.md` |
| 手册维护机制、复利工程规则、AGENTS 可发现性 | `/opt/code/docs/opencode/90-复利工程/README.md` |
| 不确定归属但可能有价值 | `/opt/code/docs/opencode/90-复利工程/待整理.md` |

写公共 OpenCode 手册前，必须先搜索 `/opt/code/docs/opencode`，已有内容只增量补充，不新建重复文件；更新后同步记录 `/opt/code/docs/opencode/90-复利工程/更新日志.md`。

例：配 `.env` 前先读 `Settings` 类确认字段名、OpenSpec 先出 proposal/tasks 草案确认再 apply、预先存在测试失败先用 `git stash` 验证 baseline。

#### 通道 C：skill 自身复利（给 skill 维护用）

适用：影响某个 skill 的触发边界、提示词结构、已知限制、维护规则或排障流程。

| 经验类型 | 写入位置 |
|---|---|
| 跨 skill 通用规则 | `/opt/code/skill/AGENTS.md` |
| 某个 skill 的已知限制/设计决策/维护规则 | `/opt/code/skill/skills/<category>/<skill>/SKILL.md` |
| 诊断、排障、修复流程 | `/opt/code/skill/skills/<category>/<skill>/references/troubleshooting.md` |
| 共享标签/素材规则 | 对应共享文件，如 `material-importer/references/domain-tags.md`，并检查同步副本 |

例：本 skill 增加“项目内复利 vs 公共 OpenCode 手册 vs skill 自身维护”的三通道判断；某 generator 的 YAML 陷阱写入对应 troubleshooting。

分流原则：**Promote up, don't duplicate**。

- 只影响一个项目 → 项目内复利
- 影响多个项目的 OpenCode 使用方式 → 公共 OpenCode 使用复利
- 只影响一个 skill → skill 自身复利
- 影响两个以上 skill → `/opt/code/skill/AGENTS.md`
- 需要人看见的经验，不能只写 `AGENTS.md`；至少在面向人的 README/手册加路标

### Step 5. 修改文件

修改时遵守：

- 只写非显而易见、可复用、已验证的经验
- 不写秘密或客户敏感信息
- 不覆盖用户/其他 agent 的未提交改动
- 同一经验只写一个权威位置，必要时用引用指向
- 对复杂 skill，保持「已知限制」+「设计决策」+「维护规则」结构
- 对诊断流程，优先写 `references/troubleshooting.md`

### Step 6. 验证

至少检查：

1. 修改文件存在。
2. 新增内容可被 grep 到关键术语。
3. Markdown 标题层级正确。
4. 没有 secret、token、连接串、密码。
5. 如果经验也需要人知道，检查是否能从 README、CONTRIBUTING、docs/README 或 `/opt/code/docs/opencode/README.md` 发现。
6. 如果改共享文件，检查是否需要同步另一个共享副本。
7. 如果用户要求 commit，按仓库约定提交；否则报告未提交状态。

## 各类任务复盘清单

### PRD / 产品规划

- 是否有新的产品术语口径？
- 是否有 PRD→实施交接的新模式？
- 是否有新的分期原则或验收链路？
- 是否有新的域知识要放到 `$LANLNK_BASE/prd/<项目>/域知识.md`？
- 是否有代码实现边界需要写入交接包？

### 战略简报

- 是否有新的分析框架？
- 是否有竞品/市场证据的固定来源？
- 是否有用户确认的战略判断口径？
- 是否会指导产品路线或后续交接包？

### 公司介绍 / 客户方案

- 是否有新的行业标签、场景标签或案例匹配规则？
- 是否有客户偏好的表达方式？
- 是否有素材库缺口或证照有效期问题？
- 是否要同步 `domain-tags.md` 或案例元数据？

### 投标文件

- 是否有新的招标评分点响应模板？
- 是否有报价结构或折扣规则？
- 是否有偏离表、响应表、资质证明的复用模式？
- 是否有不能写入的敏感报价信息？

### PPT / Word

- 是否有模板限制或渲染坑？
- 是否有内容包字段规范变化？
- 是否有视觉/版式复用规则？
- 是否有 Word/PPT 生成器需要修复的行为？

### 操作手册

- 是否有运行时探测策略变化？
- 是否有 Playwright 截图失败容错经验？
- 是否有 RAG 友好 chunks/llms 输出规范变化？
- 是否需要写入 doc-generator 的已知限制？

### 部署维护手册

- 是否有新的 IaC 提取规则？
- 是否有接口检测模板？
- 是否有脱敏/回滚/排障 SOP？
- 是否应该沉淀到 ops-manual-generator？

### 交接包

- 是否有新的跨项目协作模式？
- 是否有标准文件结构？
- 是否有 OpenSpec change 拆分模板？
- 是否有跨系统接口契约或验收清单复用价值？

### OpenCode / OpenSpec 使用

- 是否有新的高成功率提示词模式？
- 是否有 agent/skill 选择或切换经验？
- 是否有 OpenSpec propose/apply/verify/archive 流程改进？
- 是否有后台任务、codegraph、LSP、Playwright 等工具使用边界？
- 是否有“人看手册”和“agent 看 AGENTS.md”的可发现性问题？

### 项目开发 / 调试 / 部署

- 是否有项目级运行时陷阱，必须写进项目 `AGENTS.md`？
- 是否有环境变量、端口、容器、数据库、登录、seed 数据前置条件？
- 是否有预先存在的测试失败或测试隔离策略？
- 是否有手动 QA 路径比单元测试更能证明完成？
- 是否只适用于当前项目，因而不应写入公共 OpenCode 手册？

### Skill 自身维护

- 是否暴露了某个 skill 的触发边界问题？
- 是否需要调整 `description`、不触发场景或输出格式？
- 是否需要新增 `references/troubleshooting.md`？
- 是否有跨 skill 通用规则应 promote 到 `/opt/code/skill/AGENTS.md`？

## 输出格式

复利工程完成后，用以下格式汇报：

```text
复利工程完成。

项目内复利：
- <路径>: <新增/修改了什么；如果不适用，写“无”>

公共 OpenCode 手册：
- <路径>: <新增/修改了什么；如果不适用，写“无”>

Skill 自身复利：
- <路径>: <新增/修改了什么；如果不适用，写“无”>

未沉淀：
- <内容>: <原因，如一次性/敏感/未验证>

验证：
- agent 可读: <pass / not needed>
- 人类入口可发现: <pass / not needed / 待补路标>
- 无敏感信息: <pass>
- 关键术语可检索: <pass>

后续建议：
- <可选>
```

## Commit 建议

如果用户要求提交，建议 commit message：

```text
docs: persist lessons via 复利工程
```

如果本次只修改某个 skill，也可用：

```text
docs(<skill-name>): persist compound learning notes
```

## 维护规则

修改本 skill 时，优先保持纯提示词，不引入脚本。只有当复利工程需要自动扫描 session、批量生成 diff 或跨仓库索引时，再考虑增加工具脚本。
