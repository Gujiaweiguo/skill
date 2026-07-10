---
name: competitor-product-analyzer
description: |-
  竞品产品能力分析与产品优化建议 Skill。基于「证据型能力抽取 + 加权对比矩阵 + 蓝联现状映射 + 分级改进建议」方案，
  把一份竞品资料（操作手册 / 产品手册 / 截图 / 数据字典 / 方案汇报）或一个授权 demo 账号，
  评估成「竞品有哪些产品能力、证据来自哪里、蓝联该补什么、借鉴什么、观察什么」。
  触发场景："分析一下旗茂商管系统"、"用这个 demo 账号看看竞品有什么功能"、"对比 XX 竞品给出产品改进建议"、
  "把这份竞品操作手册转成能力清单和借鉴建议"、"竞品 demo 探测 + 文档对照"。
  仅面向内部产品规划与产品优化决策，不生成完整 PRD、不生成报价/方案/投标文件、不做战略定位判断。

  不做的事情：
  - 不生成完整 PRD（交给 product-prd-generator）
  - 不做战略定位/市场判断（交给 strategy-brief-generator）
  - 不写方案/报价/投标（交给 company-intro-generator / pricing-generator / bid-doc-master）
  - 不评估客户需求满足度（交给 requirement-evaluator）
  - 不修改业务系统代码（/opt/code/mi）
  - 不绕过登录/验证码/权限/反爬，不做漏洞测试
compatibility: >
  纯提示词 skill，无 Python 依赖。
  文档转换复用 material-importer（markitdown + 图片提取 + OCR）。
  Demo 探测复用 doc-generator 的 Playwright 模式与文本/角色 locator 规范。
  能力对齐参考 product-prd-generator 输出的功能清单与 ontology（$LANLNK_BASE/config/ontology/business-ontology.yaml）。
  商管域知识参考 $LANLNK_BASE/out/prd/商管系统/域知识.md。

  Quick start:
  ```bash
  export LANLNK_BASE=/opt/code/docs/lanlnk
  ```

  用户只需告诉 Agent 竞品名、资料来源（手册路径 / demo URL / 两者）和对照产品，Agent 自动完成：
  - "分析一下旗茂商管系统，操作手册在 materials/13-competitors/qimao/"
  - "用 demo 账号 llkj/llkj123 探测 http://oa.1qmall.cn/SMallTest/，对比 MI 给改进建议"
  - "这份竞品手册 + 这个 demo 账号，做交叉验证，输出能力矩阵和借鉴清单"
---

# Competitor Product Analyzer — 竞品产品能力分析与产品优化建议 Agent Pipeline

## DocSpec 质量基线

本 skill 生成的竞品能力清单、证据台账、对比矩阵、产品优化建议和 review 清单必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `DocSpec-通用文档质量规范.md`、`PRD质量规范.md` 和 `文档验收清单.md`。竞品证据必须可追溯，不得把 demo 看不到写成竞品没有。

基于「证据型能力抽取 + 加权对比矩阵 + 蓝联现状映射 + 分级改进建议」方案。

## 核心定位

这个 skill 是 **PRD 之前、战略简报之后的产品情报层**。

它回答的是：

- 竞品实际有哪些产品能力（不是销售话术）？
- 每条能力的证据来自哪里？可信度多高？
- 蓝联当前产品（MI / CRM / AI）相对竞品是 existing / partial / missing / better？
- 竞品的哪些设计值得蓝联借鉴？哪些必须补齐？哪些只是观察？
- 产品改进建议如何排优先级（P0/P1/P2/P3）？

它不回答：

- 蓝联整体战略怎么定位（→ strategy-brief-generator）
- 具体功能字段/接口/页面怎么设计（→ product-prd-generator）
- 客户方案怎么写、投标怎么响应（→ company-intro-generator / bid-doc-master）
- 客户需求满足度多少（→ requirement-evaluator）

## 与兄弟 Skill 的边界

```
material-importer（文档转换/OCR）  ←─ 你复用它的 markitdown + 图片提取能力
        ↓
doc-generator（demo 探测/截图）    ←─ 你复用它的运行时探测/locator 规范（不直接调用）
        ↓
competitor-product-analyzer（能力分析 + 改进建议）  ←─ 你在这里
        ↓
product-prd-generator（PRD / 功能清单 / 差距分析）  ←─ 你的改进建议交给它落地
        ↓
strategy-brief-generator（战略定位 / 竞对打法）     ←─ 你的能力矩阵作为战略证据之一
```

**严格不做的事：**

- 不写字段、接口、页面、数据模型（→ PRD）
- 不写战略定位、市场判断、客户路线（→ strategy）
- 不写方案汇报、报价、投标（→ company-intro / pricing / bid-doc）
- 不评估客户需求满足度（→ requirement-evaluator）
- 不直接修改业务系统代码（/opt/code/mi）
- 不绕过登录/验证码/权限/反爬，不做漏洞测试或压力测试
- 不把竞品截图/UI 文字直接用于客户材料

## 三种输入模式

| 模式 | 触发条件 | 主证据来源 | 弱证据来源 |
|---|---|---|---|
| `manual-only` | 只有手册/产品文档/截图/PPT | 操作手册、功能手册、数据字典、蓝图方案 | 销售策略、方案汇报 |
| `demo-only` | 只有 demo URL 或测试账号 | 运行时探测（菜单/页面/流程/截图） | 无 |
| `manual-plus-demo` | 手册 + demo 都有 | 手册与 demo 一致的能力 | 仅手册提及或仅 demo 可见的能力（需交叉验证）|

**模式自动判定**：Agent 根据用户输入自动判定模式，无需用户显式指定。两者都有时默认 `manual-plus-demo`，做交叉验证。

## 方法论

### 能力矩阵，不是功能打勾表

行业最佳实践明确：100 行的"有/没有"打勾表对决策无价值。本 skill 强制使用**加权能力矩阵**：

- 每条能力记录**实现质量**（Leading / Competitive / Behind / Missing），不是 binary yes/no
- 每条能力挂**证据链**（文件路径 + 章节/页码 + 截图 + URL + 探测时间）
- 每条能力标**置信度**（high / medium / low）
- 每条能力映射**蓝联现状**（existing / partial / missing / better-than-lanlnk / unknown）
- 改进建议分四类：**补齐 / 增强 / 借鉴 / 观察**，并标注 P0/P1/P2/P3

### 证据纪律

**每条能力判断必须可追溯。** 战略简报的证据纪律在此同样适用，三类标记：

| 标记 | 含义 | 要求 |
|---|---|---|
| `【证据】` | 来自资料或运行时的事实 | 必须引用具体来源（文件 + 章节/页码 或 URL + 截图 + 探测时间）|
| `【判断】` | 基于证据的推理 | 必须列出依据的证据 ID |
| `【假设】` | 未证实的假设 | 必须标注，并说明如何验证 |

禁止的行为：

- 禁止把销售策略材料当产品事实（只能作弱证据，置信度 low）
- 禁止把"demo 账号看不到"等同于"竞品没有"
- 禁止把方案汇报 PPT 的功能列表等同于实际能力（汇报材料会夸大）
- 禁止无来源的能力断言
- 禁止把竞品宣传话术直接抄进蓝联产品建议

详细规则见 `references/evidence-ledger.md`。

### 合规与凭据安全（红线）

| 红线 | 说明 |
|---|---|
| 只使用授权访问 | demo 账号必须由竞品方主动提供或公开渠道获得，不得伪造身份、不得盗用账号 |
| 不绕过任何控制 | 不破解验证码、不绕过权限、不破解反爬、不绕过接口限流 |
| 不做攻击性测试 | 不做漏洞扫描、SQL 注入、压力测试、批量数据导出 |
| 凭据只进 .auth.json | 用户名密码只写入 `$ANALYSIS_ROOT/.auth.json`（mode 0600，gitignored），不进日志/报告/截图说明/git |
| 最小数据采集 | 只采集能力分析必需的页面/字段/截图，不抓取客户数据、个人隐私、交易明细 |
| 截图默认脱敏 | 截图中的客户名、手机号、金额等敏感信息在写入证据前必须打码或替换为占位符 |
| 留来源与时间戳 | 每条证据记录 URL + 探测时间 + 账号权限等级，便于复核 |

详细规则见 `references/safety-and-ethics.md`。

## 目录契约

### 两阶段分离：采集入库（S0）+ 能力分析（S1/S5）

本 skill 的产物分两个阶段，目录严格分离：

| 阶段 | 触发 | 产物位置 | 性质 |
|---|---|---|---|
| **S0 采集入库** | 用户提供手册路径或 demo 账号 | `incoming/` + `raw/` + `materials/13-competitors/` | 竞品素材沉淀（三层归属）|
| **S1/S5 能力分析** | 需要做能力矩阵/改进建议/PRD 时 | `out/prd/商管系统/competitor-analysis/<vendor>/` | 蓝联对竞品的分析结论 |

> **为什么分离**：采集入库是"竞品有什么"（事实层，可被多个 skill 复用）；能力分析是"蓝联该怎么改进"（判断层，依赖蓝联功能清单和客户优先级）。混在一起会导致采集产物被分析结论淹没，且 materials 层缺失导致其他 skill 无法复用竞品素材。

### S0 采集入库：三层归属（遵循 lanlnk 统一素材库规范）

```text
$LANLNK_BASE/
├── incoming/competitor-<vendor>/              ← 🟢 原始证据入口
│   ├── runtime-snapshots/                     demo 探测原始证据（HTML 快照/登录响应/导航响应）
│   ├── manuals/                               手册原始文件（PPTX/DOCX/XLSX/PDF）
│   └── proposals/                             方案汇报原始文件
│
├── raw/prd-商管系统/02-competitors/<vendor>/   ← 🟡 转换产物（gitignored，百度盘）
│   ├── 01-销售策略/                           markitdown 转换的 md + 提取图片
│   ├── 02-方案汇报/
│   ├── 03-报价商务/
│   ├── 04-产品功能/
│   │   └── page-fields/                       从 demo HTML 提取的页面字段/按钮 JSON
│   ├── 05-实施与服务/
│   │   └── demo-runtime/                      demo 运行时探测记录（capture-manifest/runtime-probe）
│   └── 06-行业洞察/
│
└── materials/13-competitors/<vendor>/          ← 🔵 权威精华（进 Git）
    ├── README.md                              素材库入口（资料状态+目录结构+关键发现）
    ├── source-inventory.md                    资料盘点（来源/日期/证据强度/缺口）
    ├── demo-page-inventory.md                 demo 页面/菜单/字段/按钮/截图清单
    ├── 01-销售策略/ ~ 06-行业洞察/             6类分类精华
    └── imgs/                                  脱敏截图（百度盘，gitignored）
```

**6类分类体系**（所有竞品统一，证据强度标注）：

| 分类 | 证据强度 | 典型内容 |
|---|---|---|
| `01-销售策略/` | 极弱（销售话术，不作产品事实）| 市场定位、培训资料、星狼营 |
| `02-方案汇报/` | 弱（汇报会夸大，需运行时或手册佐证）| 通用售前方案、汇报 PPT |
| `03-报价商务/` | 仅作定价参考，不进能力矩阵 | 报价单、商务条款、合同模板 |
| `04-产品功能/` | **强**（功能清单、数据字典、业务逻辑）| 功能清单、demo 页面字段、数据字典 |
| `05-实施与服务/` | **强**（操作手册、功能手册、蓝图方案）| 操作手册、demo 探测记录、蓝图 |
| `06-行业洞察/` | 仅作背景，不进能力矩阵 | 行业最佳实践、业务标准化、趋势 |

### S1/S5 能力分析：competitor-analysis 输出

```text
$LANLNK_BASE/out/prd/商管系统/competitor-analysis/<vendor>/
├── .auth.json                          ← demo 凭据（mode 0600，gitignored）
├── capability-map.json                 ← 竞品能力结构化清单（从 materials 素材抽取）
├── competitor-capability-map.md        ← 人类可读版
├── ability-comparison-matrix.json      ← 加权对比矩阵（含蓝联现状 + 改进建议）
├── ability-comparison-matrix.md
├── lanlnk-product-improvement-recommendations.md  ← 主交付件：产品改进建议
├── evidence-ledger.json                ← 证据台账（引用 materials/raw 路径）
├── evidence-ledger.md
└── review/
    └── pending-items.md                ← 待确认/冲突/缺口
```

> **competitor-analysis 不存原始素材**：只存分析结论。原始素材和转换产物在 S0 阶段已入三层。competitor-analysis 中的 evidence-ledger 通过路径引用 materials/raw 中的证据，不复制原文。

## 处理流程

### S0 采集入库阶段（手册/demo 采集 → 三层归属）

```
S0.1: 输入解析 → 判定模式（manual-only / demo-only / manual-plus-demo）
      ↓
S0.2: 原始证据入库 → incoming/competitor-<vendor>/
      ├── manual: 复制原始文件（PPTX/DOCX/XLSX/PDF）
      └── demo: 抓取 HTML 快照 + 登录响应(脱敏) + 导航响应 + 页面 HTML
      ↓
S0.3: 转换产物入库 → raw/prd-商管系统/02-competitors/<vendor>/<6类>/
      ├── manual: markitdown 转 md + extract_images 提取图片 + OCR
      └── demo: 正则解析页面字段/按钮 → page-fields JSON + demo-runtime 记录
      ↓
S0.4: 权威精华入库 → materials/13-competitors/<vendor>/<6类>/
      ├── README.md（素材库入口）
      ├── source-inventory.md（资料盘点）
      ├── demo-page-inventory.md（demo 页面/菜单/字段/按钮/截图清单）
      ├── 04-产品功能/能力清单.md（从 page-fields 提炼的人类可读能力清单）
      ├── 05-实施与服务/截图索引.md（截图清单 + 脱敏规则）
      └── imgs/（脱敏截图，百度盘）
      ↓
S0.5: 资料盘点交付 → 用户确认素材完整性和缺口
```

**S0 阶段边界**：只做入库和素材沉淀，不做能力矩阵、不做产品改进建议、不做 PRD。这些进入 S1/S5。

### S1/S5 能力分析阶段（从 materials 抽取 → 分析结论）

```
S1.1: 能力抽取（从 materials/raw 统一 schema 合并）→ capability-map.json
      ↓ 引用 materials/13-competitors/<vendor>/04-产品功能/ + raw/ page-fields
S1.2: 术语归一（对齐商管域知识 + ontology）
      ↓
S1.3: 蓝联现状映射（读 product-prd-generator 的功能清单）
      ↓
S1.4: 加权对比矩阵 + 改进建议分级
      ↓ ability-comparison-matrix.json + improvement-recommendations.md
S1.5: 证据台账 + 待确认项
      ↓ evidence-ledger.json（引用 materials/raw 路径，不复制原文）+ review/pending-items.md
S1.6: 交互确认与交付
```

**S1 阶段产物全部在 `out/prd/商管系统/competitor-analysis/<vendor>/`**，不回写 materials（避免分析结论污染素材库）。

### S0.1 输入解析

从用户描述中提取：

| 参数 | 说明 | 示例 |
|---|---|---|
| 竞品名 | 用于目录命名 | 旗茂 / 海鼎 / 明源 |
| 资料来源 | manual 路径 / demo URL / 两者 | `incoming/competitor-qimao/manuals/` + `http://oa.1qmall.cn/SMallTest/` |
| demo 凭据（如有）| 用户名/密码 | llkj / llkj123（只进 .auth.json 或会话临时使用）|
| 对照产品 | 蓝联哪个产品作基准（S1 阶段用）| MI（商管系统）/ CRM / AI |
| 客户业态（可选）| 辅助理解能力语义 | 购物中心 / 写字楼 / 产业园区 |

判定模式：

- 只提供路径 → `manual-only`
- 只提供 URL → `demo-only`
- 两者都提供 → `manual-plus-demo`（默认，做交叉验证）

输出 `materials/13-competitors/<vendor>/source-inventory.md`：每份资料记录 `来源 / 采集日期 / 证据强度 / 转换状态 / 缺口`。

### S0.2 原始证据入库（incoming 层）

**manual 模式**：将用户提供的原始文件复制到 `incoming/competitor-<vendor>/manuals/`（或 proposals/）。

**demo 模式**：抓取运行时证据到 `incoming/competitor-<vendor>/runtime-snapshots/`：
- 登录页 HTML、主框架 HTML、关键 JS 文件
- 登录响应（**必须脱敏**：移除密码、加密密钥 EncryptionKey、权限原文 RoleFunctionality，只保留元数据）
- 导航接口响应（LoadNav / 菜单结构 JSON）
- 各页面 HTML 快照

**凭据安全红线**：用户名和密码只用于授权采集，**不写入 incoming/raw/materials 任何文件**。登录响应脱敏后只保留 `result / msg / MainPage / login_meta(不含密钥) / role_functionality_count`。

### S0.3 转换产物入库（raw 层）

**manual 模式**——复用 `material-importer` 的 markitdown + 图片提取 + OCR：

```bash
cd /opt/code/skill/skills/business/material-importer
uv run scripts/extract_images.py "<incoming/competitor-<vendor>/manuals/>"
markitdown "<原始文件>" -o "<raw 目录>/<6类>/<同名>.md"
```

转换规则与 material-importer 一致：PPTX/DOCX/XLSX/PDF → markdown，图片提取到 `raw/<6类>/<filename>_media/`，空章节清理。按 6 类分类归档到 `raw/prd-商管系统/02-competitors/<vendor>/<01~06>/`。

**OCR**：图片型资料（扫描手册、PPT 截图）用 DeepSeek-OCR-2，复用 material-importer 的 `scripts/ocr_extract.py`。

**demo 模式**——从 incoming 层的 HTML 快照提取结构化字段：
- 正则解析 layui table cols 的 title / 表单 label / placeholder → 页面字段清单
- 从登录响应的 RoleFunctionality 权限矩阵提取按钮清单（比 HTML toolbar 模板解析更完整）
- 产物：`raw/prd-商管系统/02-competitors/<vendor>/04-产品功能/page-fields/page-fields-*.json` + `05-实施与服务/demo-runtime/capture-manifest.json`

### S0.4 权威精华入库（materials 层）

从 raw 层提炼可复用精华到 `materials/13-competitors/<vendor>/`：

| 文件 | 来源 | 内容 |
|---|---|---|
| `README.md` | 新建 | 素材库入口（资料状态+目录结构+关键发现+三层归属）|
| `source-inventory.md` | S0.1 产出 | 资料盘点 |
| `demo-page-inventory.md` | 从 page-fields JSON 提炼 | demo 页面/菜单/字段/按钮/截图清单（人类可读总览）|
| `04-产品功能/能力清单.md` | 从 page-fields JSON 提炼 | 竞品能力结构化清单（按模块分组）|
| `05-实施与服务/截图索引.md` | 从 capture-manifest 提炼 | 截图清单 + 脱敏规则 |
| `imgs/*.png` | demo 截图 | 脱敏截图（百度盘，gitignored）|

**manual 精华**：从 raw 的 markitdown md 中提炼业务逻辑要点，写入对应分类子目录（如 `05-实施与服务/操作手册摘要.md`）。

> **materials 层是 Git 跟踪的权威精华**，其他 skill（product-prd-generator / strategy-brief-generator / company-intro-generator）从这里读取竞品素材。raw 和 incoming 是百度盘（gitignored）。

### S0.2/S0.3 Demo 运行时探测（demo 模式，入 incoming + raw 层）

**复用 `doc-generator` 的运行时探测与截图规范**。详细页面抽取策略见 `references/page-extraction-strategy.md`。

**S0.2/S0.3 demo 探测执行顺序**：

1. **凭据写入** `.auth.json`（mode 0600，gitignored），首次询问用户，二次复用。**密码不写入任何其他文件**。
2. **加载 playwright skill**：`skill(name="playwright")`
3. **半自动登录**（如登录页有验证码）：Playwright 启动浏览器 + 填账号密码 + **暂停让用户人工识别验证码** + 检测登录成功
4. **菜单加载机制探测**：读 `<a>` 标签的 onclick handler，判定是 accordion / CreateLeftNav 替换式 / 异步加载 / SPA 路由切换（4 种机制详见 page-extraction-strategy.md）
5. **菜单结构收集**：按机制选脚本，循环点击顶级菜单 + sleep + 读 divSide 容器，拿到全部二级菜单文本
6. **二级菜单 URL 提取**：从 `<a onclick>` 用正则 `/addTab\(['"]([^'"]+)/` 拿到每个页面的 URL
7. **页面字段抽取**（三档降级）：
   - **模式 A（同源 fetch + 正则）**：默认起点，一次 evaluate 批量抓 10-20 页，每页 50ms。HTML 含字段名/按钮文本的 layui/服务器渲染站点最有效
   - **模式 B（addTab + iframe.contentDocument）**：模式 A 失败（fields=[] 或全是噪音）时升级，每页 3-5s。⚠️ **禁止在 iframe 内调用 element.click()**——会触发跳转导致 page URL 重置为 about:blank，会话失效
   - **模式 C（Playwright snapshot）**：兜底，每页 5-10s，仅用于 P0 必补的重点页面
8. **流程推断**：从按钮组合识别 CRUD/查询/导出/审批等典型流程
9. **截图**：每模块选 1-3 张关键页面（首页 + 重点表单/报表），脱敏后存到 `materials/13-competitors/<vendor>/imgs/`
10. **locator 规范**：只用 text/role/placeholder/label，禁用 CSS/XPath（与 doc-generator 一致）
11. **单页失败容忍**：一个页面 timeout 或 fetch 失败不阻塞整体，记入 capture-manifest
12. **权限标记**：demo 账号无法访问的页面标 `accessible: false` + `requires_role`，**不判定为竞品没有此功能**
13. **按钮清单交叉验证**：从登录响应的 RoleFunctionality 权限矩阵提取每个页面的按钮列表，比 HTML toolbar 模板解析更完整
14. **原始证据入 incoming**：HTML 快照/登录响应(脱敏)/导航响应 → `incoming/competitor-<vendor>/runtime-snapshots/`
15. **转换产物入 raw**：page-fields JSON + capture-manifest → `raw/prd-商管系统/02-competitors/<vendor>/04-产品功能/page-fields/` + `05-实施与服务/demo-runtime/`

**关键约束**：

- 不绕过任何权限控制
- 不做漏洞测试或压力测试
- 截图中的客户名/手机号/金额必须脱敏后再写入证据
- 探测时间精确到分钟，记录账号角色（如"普通商户账号"/"管理员账号"）
- **预算控制**：模式 A/B/C 性能差 100 倍以上，永远从 A 开始；80 页全用 A 仅 4s，全用 C 需 7-13 分钟

### S1.1 能力抽取（从 materials/raw 合并）

从文档（S0.3 raw 层）和运行时（S0.2/S0.3 page-fields）合并抽取能力，统一 schema（详见 `references/capability-schema.md`）：

```json
{
  "vendor": "qimao",
  "product": "旗茂 BS 商管系统",
  "module": "合同管理",
  "capability_name": "新合同申请",
  "original_term": "新合同申请单",
  "standard_term": "lease-contract-management",
  "capability_type": "功能",
  "scenario": "招商定稿后发起合同审批",
  "role": ["招商经理", "法务"],
  "workflow": ["选铺位", "录条款", "上传附件", "提交审批"],
  "fields": ["铺位号", "租期", "租金", "免租期", "审批人"],
  "permissions": ["招商经理可建", "法务可审"],
  "reports": [],
  "integrations": [],
  "data_structures": [],
  "evidence": [
    {
      "source_type": "manual",
      "source_ref": "materials/13-competitors/qimao/05-实施与服务/合同模块操作手册.pdf §3.2 p.45",
      "screenshot": null,
      "url": null,
      "probed_at": null,
      "account_role": null
    },
    {
      "source_type": "demo-runtime",
      "source_ref": "合同管理 → 新合同申请 页面",
      "screenshot": "imgs/合同管理_3_新合同申请表单.png",
      "url": "http://oa.1qmall.cn/SMallTest/contract/new",
      "probed_at": "2026-07-06T11:30:00+08:00",
      "account_role": "管理员"
    }
  ],
  "confidence": "high",
  "status_vs_lanlnk": "partial",
  "quality_assessment": "Competitive",
  "notes": "旗茂的免租期支持分段，蓝联目前只支持整段"
}
```

**capability_type 取值**：`功能 | 流程 | 字段 | 权限 | 数据结构 | 报表 | 集成 | AI/BI`

**quality_assessment 取值**（实现质量，不是有没有）：

| 取值 | 含义 |
|---|---|
| `Leading` | 业界最佳实现，是购买理由 |
| `Competitive` | 满足买家预期，不是差异化 |
| `Behind` | 功能存在但有明显短板 |
| `Missing` | 未观察到（不等于竞品没有，可能是权限/版本未覆盖）|

**confidence 取值**：

| 取值 | 判定 |
|---|---|
| `high` | 手册 + 运行时一致，或多份独立资料互证 |
| `medium` | 单一来源（仅手册 或 仅运行时）|
| `low` | 仅销售材料，或运行时无法复现，或资料日期不明 |

**status_vs_lanlnk 取值**：

| 取值 | 含义 |
|---|---|
| `existing` | 蓝联已有且证据充分 |
| `partial` | 蓝联有但不完整 |
| `missing` | 蓝联未见实现 |
| `better-than-lanlnk` | 竞品实现质量优于蓝联（重点借鉴对象）|
| `unknown` | 蓝联现状无法判断（进 review）|

### S1.2 术语归一

把竞品的原始术语映射到蓝联标准功能名，复用：

- `$LANLNK_BASE/out/prd/商管系统/域知识.md`（商管域术语别名表）
- `$LANLNK_BASE/config/ontology/business-ontology.yaml`（8 模块 482 术语）
- `product-prd-generator/references/term-aliases.yaml`

找不到映射的术语进 `review/pending-items.md`，不强行归一。

### S1.3 蓝联现状映射

读对照产品的功能清单：

| 对照产品 | 功能清单路径 |
|---|---|
| MI / 商管系统 | `$LANLNK_BASE/out/prd/商管系统/output/功能清单.md` |
| CRM / 会员系统 | `$LANLNK_BASE/materials/03-products/CRM会员系统功能清单.md` |
| AI Skills | `$LANLNK_BASE/materials/11-cre-ai-skills/02_机会与产品/岗位 AI Skills 增强性与摩擦消除分析矩阵.md` |

逐条把竞品能力映射到蓝联功能清单的 `existing/partial/missing`，填 `status_vs_lanlnk`。

功能清单不存在时提示：

```
未找到 <产品> 的功能清单。请先运行 product-prd-generator 生成，或提供功能清单路径。
本 skill 在缺功能清单时会退化为只输出竞品能力清单，不做蓝联现状映射。
```

### S1.4 加权对比矩阵 + 改进建议

详见 `references/comparison-matrix.md`。核心：

**权重来自客户/买家重要性**，不是内部拍脑袋。**权重来源降级路径**（按优先级，前一个不可用时降级到下一个）：

1. **用户在 P0 显式提供**——最高优先级
2. **`requirement-evaluator` 的客户需求汇总**（频率高的能力维度加权）——最理想来源
3. **`$LANLNK_BASE/materials/10-methodology/methodology/15-商业地产岗位病药矩阵.md`**（多岗位共同痛点加权）——长期参考
4. **`$LANLNK_BASE/out/prd/<产品>/output/功能清单.md` 的 missing/partial 项分布**——反向推断客户痛点（missing 多的维度 = 蓝联弱项 = 应加权）
5. **默认均匀分布**——仅当以上都缺失时，且必须在 `ability-comparison-matrix.json` 的 `weight_source` 标注 `"unweighted-fallback"`，并在 review/pending-items.md 提示"权重未校准"

**降级规则**：每降一级，结果报告的"管理层摘要"必须显式标注权重来源和置信度。**禁止**把降级路径 4-5 的结果当作"客户真实优先级"陈述。

**改进建议四类**：

| 建议 | 触发条件 | 优先级 |
|---|---|---|
| `补齐` | 蓝联 missing 且客户会关心 | P0/P1 |
| `增强` | 蓝联 partial 或竞品 Leading 而蓝联 Behind | P1/P2 |
| `借鉴` | 竞品设计好但不一定立刻做 | P2/P3 |
| `观察` | 证据弱、账号权限不足、或仅销售宣传 | 不进路线图 |

输出 `ability-comparison-matrix.md`（人类可读）+ `lanlnk-product-improvement-recommendations.md`（主交付件）。

### S1.5 证据台账 + 待确认项

详见 `references/evidence-ledger.md`。每条证据记录：

```text
- ID: EV-001
- 能力ID: CAP-合同管理-新合同申请
- 声明: 旗茂支持免租期分段（前 3 个月全免，后续 3 个月半免）
- 类型: 证据
- 来源: materials/13-competitors/qimao/05-实施与服务/合同模块操作手册.pdf §3.2 p.45 + 运行时截图 imgs/合同管理_3_新合同申请表单.png
- 探测时间: 2026-07-06T11:30:00+08:00（运行时）/ 2024-08（手册版本）
- 置信度: high（手册 + 运行时一致）
- 账号权限: 管理员
```

`review/pending-items.md` 记录：

- 术语映射不清
- demo 账号权限不足导致的能力盲区
- 手册版本日期过旧（>2 年）
- 资料类型单一（只有销售策略，无产品手册）
- 竞品能力与蓝联冲突无法判定

### S1.6 交互确认与交付

1. 展示能力统计：发现 N 项能力，按类型/置信度/蓝联现状分布
2. 展示改进建议统计：补齐 X 项 / 增强 Y 项 / 借鉴 Z 项 / 观察 W 项
3. 展示证据覆盖度：high X% / medium Y% / low Z%
4. 列出 `review/pending-items.md` 中需用户确认的关键问题
5. 提示后续动作：
   - 改进建议交给 `product-prd-generator` 落地 PRD
   - 能力矩阵作为 `strategy-brief-generator` 的竞品证据
   - 待确认项可与竞品方/销售/客户复核

## 使用示例

### 示例 1：manual + demo（旗茂）

> 用户："分析旗茂 BS 商管系统，手册在 materials/13-competitors/qimao/，demo 账号 llkj/llkj123，URL http://oa.1qmall.cn/SMallTest/Login.html，对比 MI"

```
Agent:
  [S0.1] 模式: manual-plus-demo | 竞品: qimao | 对照产品: MI（S1阶段用）
       资料盘点: 12 份手册（操作手册 5 + 功能手册 4 + 数据字典 1 + 蓝图 2）
       demo: http://oa.1qmall.cn/SMallTest/ | 账号角色待探测

  [S0.2] 原始证据入库 → incoming/competitor-qimao/
       ├── manuals/（12份原始文件）
       └── runtime-snapshots/（HTML快照 + 登录响应(脱敏) + 导航响应）

  [S0.3] 转换产物入库 → raw/prd-商管系统/02-competitors/qimao/<6类>/
       ├── 12 份手册 markitdown 转 md + 138 张提取图片
       └── demo: page-fields JSON + capture-manifest

  [S0.4] 权威精华入库 → materials/13-competitors/qimao/
       ├── README.md + source-inventory.md + demo-page-inventory.md
       ├── 04-产品功能/能力清单.md
       ├── 05-实施与服务/截图索引.md + 操作手册摘要
       └── imgs/（47张脱敏截图）

  --- 用户确认素材完整性后，进入 S1 能力分析 ---

  [S1.1] 抽取能力 86 项（功能 52 + 流程 18 + 字段 12 + 权限 4）
  [S1.2] 术语归一: 79 项匹配 ontology，7 项进 review
  [S1.3] 蓝联现状映射: existing 41 / partial 23 / missing 18 / better-than-lanlnk 4
  [S1.4] 加权矩阵 → 改进建议: 补齐 12 / 增强 19 / 借鉴 8 / 观察 47
  [S1.5] 证据台账 142 条（引用 materials/raw 路径）| high 68% / medium 24% / low 8%
         review: 7 项术语未映射 + 2 项 demo 权限未知 + 3 项手册版本过旧

  [S1.6] 交付: competitor-analysis/qimao/
       主交付件: lanlnk-product-improvement-recommendations.md
       后续: 改进建议交给 product-prd-generator 落地 PRD
```

### 示例 2：demo-only

> 用户："用这个 demo 账号探测一下 XX 竞品，URL xxx，账号 yyy/zzz"

```
Agent:
  [S0.1] 模式: demo-only | 竞品: xx | 警告: 无手册佐证，能力清单置信度上限 medium，建议补充手册

  [S0.2] 原始证据入库 → incoming/competitor-xx/runtime-snapshots/
  [S0.3] 转换产物入库 → raw/prd-商管系统/02-competitors/xx/04-产品功能/page-fields/
  [S0.4] 权威精华入库 → materials/13-competitors/xx/{README, source-inventory, demo-page-inventory, 04-产品功能/能力清单}

  --- 用户确认后，进入 S1 能力分析（仅基于运行时可见部分）---

  [S1.1] 抽取能力（仅运行时可见部分）
  [S1.3] 蓝联现状映射（仅对运行时可见能力）
  [S1.4] 改进建议（标注"仅基于运行时探测，建议补充手册复核"）
  [S1.6] 交付 + 提示: manual 模式补完后可重跑 manual-plus-demo 提升置信度
```

### 示例 3：明确拒绝越界

> 用户："顺便帮我做一份竞品对比 PPT 给客户看"

```
Agent:
  我只做内部能力分析和产品改进建议。
  客户面向的竞品对比 PPT 请交给 company-intro-generator（模式B 供应商入围方案）。
  我的能力矩阵可作为那份方案的内部证据，但不直接生成客户材料。
```

## 配置读取

```bash
export LANLNK_BASE=/opt/code/docs/lanlnk
```

| 变量 | 路径 | 说明 |
|---|---|---|
| `$MATERIALS_DIR` | `$LANLNK_BASE/materials` | 素材库根 |
| `$COMPETITORS_DIR` | `$MATERIALS_DIR/13-competitors` | 竞品库（6 类分类）|
| `$INCOMING_VENDOR_DIR` | `$LANLNK_BASE/incoming/competitor-<vendor>/` | **S0 原始证据入口**（百度盘）|
| `$RAW_VENDOR_DIR` | `$LANLNK_BASE/raw/prd-商管系统/02-competitors/<vendor>/` | **S0 转换产物**（gitignored，百度盘）|
| `$MATERIALS_VENDOR_DIR` | `$COMPETITORS_DIR/<vendor>/` | **S0 权威精华**（进 Git）|
| `$PRD_DIR` | `$LANLNK_BASE/out/prd/商管系统` | PRD 项目根 |
| `$ANALYSIS_ROOT` | `$PRD_DIR/competitor-analysis/<vendor>` | **S1 能力分析输出根**（不含原始素材）|
| `$USERGUIDE_BASE` | `$LANLNK_BASE/materials/03-products/user-guides` | doc-generator 的输出根（如需生成竞品操作手册）|

## 已知限制

- **demo 账号权限决定可见性**：管理员账号能看到的能力 ≠ 普通账号能看到的能力。分析报告必须标注账号角色，"未观察到"≠"竞品没有"。
- **手册版本可能过旧**：手册日期 >2 年时必须提示，能力清单标注"基于 YYYY 版手册"。
- **销售策略类材料不能当产品事实**：`01-销售策略` 和 `02-方案汇报` 只能作弱证据，置信度上限 low。
- **截图脱敏可能丢信息**：客户名/手机号/金额打码后，部分字段证据强度下降。
- **术语归一依赖 ontology 完整度**：当前 ontology 572+ 术语，覆盖率约 19%，未映射术语会进 review。
- **不做定量市场预测**：不评估竞品市场份额、收入、客户数等需第三方调研机构的指标。
- **不评估竞品技术栈性能**：不测响应时间、并发、可用性等技术指标（属运维范畴）。
- **Playwright 依赖**：demo 模式需要 playwright skill 可用 + 目标站点可访问。不可用时退化为 manual-only。
- **不直接生成 PRD/方案/报价**：改进建议是 Markdown，落地交给 product-prd-generator；客户方案交给 company-intro-generator。
- **JS 渲染页面静态解析可能失败**：纯 SPA（Vue/React）的字段在运行时才渲染，模式 A（同源 fetch + 正则）拿不到。必须升级到模式 B（addTab + iframe.contentDocument）或模式 C（Playwright snapshot）。详见 `references/page-extraction-strategy.md`。
- **菜单加载机制差异大**：不同竞品站的菜单加载机制不同（accordion / CreateLeftNav 替换式 / 异步加载 / SPA 路由），必须先探测 onclick handler 才能选择正确的菜单收集脚本，不能假设所有站点都是 accordion。
- **iframe 内 evaluate 高风险**：在 iframe.contentDocument 里调用 element.click() 可能触发跳转或打开新窗口，导致整个 Playwright page 的 URL 被重置为 about:blank，会话失效。**iframe 内只读 DOM，交互操作放回主 document 上下文**。
- **权重来源降级可能误导**：当 requirement-evaluator 输入缺失时，权重只能从功能清单 missing 分布推导，这是反向推断不是客户真实优先级。报告必须显式标注权重来源。
- **改进建议的"客户必需"标记依赖外部输入**：本 skill 自己无法判断某项能力是否"客户必需"，必须借助 requirement-evaluator 或用户在 P0 显式提供。无外部输入时，"P0 必补"标记只能基于"购买理由级领先"的主观判断，置信度 medium。

## 设计决策

### 三档页面抽取策略（A/B/C 降级）

P2 阶段不直接走 doc-generator 的"运行时探测 + Playwright snapshot"，而是先用低成本的"同源 fetch + 正则解析"批量抓取，失败才升级到 addTab+iframe，最后才用 Playwright snapshot。**理由**：性能差 100 倍以上（A 4s vs C 7-13 分钟），且大部分 layui/服务器渲染站点用模式 A 已能拿到 60% 以上字段。详见 `references/page-extraction-strategy.md`。

**拒绝的替代方案**：直接用 doc-generator 的 Playwright snapshot 模式——对 80+ 页面站点不现实（耗时 + token 爆炸）。

### 权重来源五级降级

权重不是"客户重要性"的客观度量，而是来源置信度的体现。从"用户显式提供"到"默认均匀"共五级，每级降级必须在报告中显式标注。**理由**：避免把"基于功能清单 missing 分布的反向推断"误陈述为"客户真实优先级"。

**拒绝的替代方案**：所有降级都用均匀分布——会让改进建议失去优先级意义，客户无法判断"先做什么"。

### iframe 内禁止 click

在 iframe.contentDocument 里调用 element.click() 会让 Playwright page 失去对主上下文的控制（实测 URL 重置为 about:blank）。**理由**：iframe click 可能触发 `_blank` 跳转或站点导航逻辑，绕过 Playwright 的事件循环。

**正确做法**：iframe 内只 querySelector 读 DOM 文本/属性，交互操作回到主 document 上下文用 Playwright API（browser_click with ref）。

### 半自动登录（验证码场景）

登录页有验证码时，不用 OCR 自动识别（合规违规），改为"Playwright 启动浏览器 + 填账号密码 + 暂停让用户人工识别验证码 + 检测登录成功"。**理由**：合规优先，用户体验损失可接受（只损失 30 秒）。

**拒绝的替代方案**：OCR 自动识别验证码——违反 ToS，可能违法。

## 维护规则

修改本 skill 时：

1. **判断归属**：通用能力分析方法论 → 留在本文件；商管域专属知识 → 写入 `$PRD_DIR/商管系统/域知识.md`
2. **更新本文件**的「已知限制」章节
3. **能力 schema 变更**同步更新 `references/capability-schema.md`
4. **证据规则变更**同步更新 `references/evidence-ledger.md`
5. **合规规则变更**同步更新 `references/safety-and-ethics.md`，并检查与 `doc-generator` 的凭据规范一致
6. **新增竞品**时，在 S0 阶段建立三层目录：`incoming/competitor-<vendor>/`、`raw/prd-商管系统/02-competitors/<vendor>/<6类>/`、`materials/13-competitors/<vendor>/<6类>/`；S1 阶段再建 `competitor-analysis/<vendor>/`
7. **改对比矩阵权重模型**时，同步 `references/comparison-matrix.md` 并检查与 `requirement-evaluator` 的客户需求优先级口径一致
8. **遇到新菜单加载机制**（如新的 SPA 框架/新的导航模式）时，更新 `references/page-extraction-strategy.md` 的"4 种典型机制"表，并补充实战经验

**判断标准**：如果一个分析行为或合规坑"下次的我"读到不一定能立刻理解为什么这么做，就应该记录。
