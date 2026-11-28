# Skill 生态季度审计报告（2026-Q4）

> 期间：2026-10-22（上轮审计提交 `93ae62d`）→ 2026-11-28（`a1dbe37`）。上轮为 2026-07 → 2026-10-22，本轮按同一格式续做，不取代上轮报告。
> 方法：git log 主题归类（85 commits）+ 双门禁脚本实跑 + 拓扑清点 + 上轮开放项逐项复检。事实来源：两条只读调查 + orchestrator 独立抽验（带 ✓ 的数字由主会话重跑复核；未带 ✓ 的来自调查，未逐项复核）。
> 边界：只看 skill 仓。docs 仓在途内容不属于本审计范围。

## 结论摘要

**P0=0 / P1=0 / P2=0，双门禁 PASS（ecosystem 32+20 passes；docs-consistency 44 pass / 0 warn）✓。** 自定义 skill 31 → 32，32 软链 0 断链、全相对路径 ✓。零 P0/P1 遗留；上轮 4 个开放项关闭 1 个，其余 3 个为继承开放。

本季没有新的 skill 群上线，主线是**既有能力的加固与规约化**：产品接入治理弧线（lnkcard → lnkmember → lnkretail）、material-importer 溯源弧线、openspec 2.1.0 sync，以及一条持续运转的复利沉淀线（11 个提交，占 13%）。

## 拓扑变化

| 项 | 2026-10 | 2026-Q4 | 验证 |
|---|---|---|---|
| 自定义 skill | 31 | **32**（+psql-access；juejin-publish 改名 content-distribution，净 0；crela-daily-skill 下线，净 −1 → 合计 +1） | `find skills -mindepth 3 -maxdepth 3 -name SKILL.md -type f \| wc -l` ✓ |
| 软链 | 31 | **32**，0 断链，全相对路径 ✓ | 逐个 `[ -e ]` + `readlink` |
| `.opencode/command/` | 不存在 | 不存在 | `ls -d .opencode/command` |
| openspec upstream 实体目录 | 10 | **12**（+bulk-archive-change、+update-change，2.1.0 sync），0 软链混入，13 个文件 tracked（12 SKILL.md + 1 标记）✓ | `find .agents/skills -mindepth 1 -maxdepth 1 -type d \| wc -l` |
| 共享文件表 | 10 文件 | **13 文件**（+provenance-evidence-boundary.md、+material-classification.md、+implementation_return_compat.py），表格与脚本数组同序 ✓ | check_docs_consistency.sh Check 2 PASS |
| 生态门禁 | 31+8 passes | **32+20 passes** | P1-8 新增 12 个 upstream 目录检查；P0 +1 来自 psql-access 软链 |
| docs 一致性 | 35 pass | **44 pass** | 见下方「pass 数不可跨季直接比较」 |

**pass 数不可跨季直接比较**：docs-consistency 的 pass 数包含 docs 侧产品目录登记数（Check 4），该数随 docs 仓变化。把基线版脚本放在当前仓库上跑得到 38，而非上轮记录的 35；这 3 个差来自 docs 侧环境变化。当前版 44，脚本自身增量是 6，全部来自新增的 3 个共享文件条目（Check 1 存在性与 Check 5 tracked 视角各计一次）✓。44 个 pass 的逐项构成本轮未完全对平，报告只记上述已验证的差值。

## 本季新增治理资产

- **产品接入治理弧线**（product-prd-generator，43 文件 / +4750 行）：lnkcard、lnkmember、lnkretail 逐个接入；归档证据驱动的能力状态；规划型（planning）与技术骨架（technical-only）两条基线；capability 钉线 56 条与 6 份 adapter 文件分布一致（implemented 16 / partial 14 / onboarding 12 / not-applicable 12 / unsupported 1 / blocked 1）✓，钉线测试 10 passed。SKILL.md 新增「Step 7：治理层登记（必做）」——lnkretail、lnkmember 连续漏在同一处后所设。
- **material-importer 溯源弧线**（25 文件）：多公司溯源加固，web-capture / authored / raw-branch 来源声明识别，v7 manifest 假阳性修复。
- **openspec 2.1.0 sync 与规格维护**：upstream 实体目录由 `.opencode/skills/` 迁到 `.agents/skills/`（+2 skills）；5 个存量规格的 TBD Purpose 回填；5 规格 12 处超长 requirement 拆分，全仓 strict 清零。主规格零 delta 头残留、零 TBD Purpose、0 个 active change ✓。
- **治理交接契约 v2.0 → v2.1**（openspec-practice）：只读模式权限语义矩阵、回执严格校验三段报告、版本三分与勘误模式。
- **content-operations / content-distribution**：juejin-publish 重构为 adapter 模式并改名；新增维护修订能力。
- **模板去客户化 + DocSpec**：ppt-master、word-master、company-intro-generator 的模板与示例不再写死真实客户内容；DocSpec《Skill写作质量规范》新增对应禁令。
- **AGENTS.md**：471 行，Conventions 粗体标题规则 48 条；本季新增 7 条跨 skill 规则（竞品控件语义实测纪律、冷启动交接三件套、skill 目录双拼布局、Pre-commit hook、shell 判空必须交叉验证、openspec archive 五坑、门禁类建议先查现有守卫）。
- **验收记录 5 份**（`references/*-acceptance-*.md` ✓）与 1 份 Owner 决策记录（lnkretail 升 partial）新增。

## 提交主题归类（85 commits ✓）

| 主线 | 数 | 代表提交 |
|---|---|---|
| product-prd-generator 产品接入与治理 | 26 | 08e2c4c、4a35d48、c694f86、06ebc11、a47769c |
| material-importer 溯源 | 15 | 32149d4、d6b17ca、334201b、b977a89 |
| 复利工程沉淀 | 11 | bafd13c、d0a4bdd、c85b997、dc2ae34、bda3e14、b665b59 |
| openspec upstream sync + 规格维护 | 8 | 9c14740、b101166、44edb5c、1dafb3c、738fb6f |
| 治理 / 审计 / AGENTS / 共享文件 | 8 | 5e0c317、111c9c0、70c83d9、a841844 |
| content-operations / content-distribution | 7 | c5a5b7f、51d3d61、1403d62 |
| 模板去客户化 + DocSpec | 3 | f2bc46d、f80c9a8、eecb0c8 |
| competitor-product-analyzer | 2 | e749257、c6346fc |
| 其他（skill 生命周期：psql-access 上线、crela 下线、O10 快照标注等） | 5 | a3bd6e1、93f962a、a1dbe37 |

按类型：docs 37 / feat 21 / fix 12 / chore 7 / test 6 / refactor 2 ✓。规模：161 文件，+20788 / −790 行，无合并提交 ✓。

## 上轮开放项逐项复检

| 上轮编号 | 内容 | 现状 |
|---|---|---|
| 1 | 运行时验证缺口 | ⚠️ 继承开放。`references/scripts/` 中 `available_skills` 零命中 ✓，门禁仍只做磁盘 / git 视角校验 |
| 2 | 契约↔schema 演化速度差（strict 收紧待 owner 裁决） | ⚠️ 继承开放。`implementation-return.schema.json` 顶层仍 `additionalProperties: true` ✓；契约侧已先行严格化（回执三段报告成为发射前、吸收前必跑步骤），schema 本体未收紧 |
| 3 | 跨仓并行会话在途碰撞 | ⚠️ 继承开放，依赖执行纪律。无机械守卫 |
| 4 | helper 共享登记（3B） | ✅ **已关闭**（`a841844`，2026-11-28）：双侧登记 + execution-protocol 自检清单引用 |

## 开放项与新观察

1. **运行时验证缺口**（继承，未变）：OpenCode 运行时可见性仍靠新会话人工确认。本季新增 1 个 skill（psql-access）、upstream 新增 2 个，均未见运行时实测记录。
2. **schema strict 收紧待 owner 裁决**（继承，未变）：收紧前的口径「schema 是最后防线、约束力在 helper warning + 吸收 SOP」持续有效；helper 现已登记为共享文件，受一致性检查约束。
3. **跨仓在途碰撞**（继承，未变）。
4. **`.openspec-target` 位置易误读**（新观察）：该标记是 `.agents/skills/` 下的单个目录级文件，不在各 openspec-*/ 目录内 ✓。AGENTS.md「OpenSpec skills」一节写「含 `.openspec-target` 标记文件」，可被读成每目录各有一个。措辞问题，无功能影响。
5. **验收记录文件名日期少一位**（新观察）：`references/governance-handoff-contracts-acceptance-2026113.md` 应为 `20261113`。现有 1 处引用：`skill-审计-2026-10.md` 开放项 4 的收口注记（`a841844`）✓；本报告落盘后为 2 处。改名需同步这两处。
   **2026-11-28 已修正**：`git mv` 改为 `…-20261113.md`，两处引用同批更新。
6. **adapter 证据日期集中**（事实，不作好坏判断）：56 条 capability 的 `verified_at` 分布为 2026-10-04 ×48、2026-10-26 ×6、2026-11-27 ×2 ✓。86% 停留在治理基线建立当日；**implemented 的 16 条 `verified_at` 全部为 2026-10-04，此后无一更新** ✓。按「capability implemented 红线」，升 implemented 需真实运行先例。**2026-11-28 逐条复核**：16 条能力全部仍成立，无需降级。其中 12 条的证据类型为「机制在位」（判定表、解析器、编译器仍在位即成立，不按日期失效）；2 条为入库事实（docs materials 文件存在）；1 条引用冻结快照；1 条含真实报价单。唯一随时间变化的是 requirement-evaluator × lnkcre 所记的基线项数（270 → 272），结论不变。
   复核发现 2 处记录问题：(a) pricing × lnkchatbi 的 evidence 把符号名写成 `LNKCHATBI_DATA`，代码中自始为函数 `build_lnkchatbi_data()`——capability 文件该处已同批改正（status 未动，钉线 10 passed）；同一名字在 5 份历史治理文档中出现 11 次（设计包 2 处含一条取证命令，O8 决策记录 1 处，O8 执行记录 6 处，建议包 1 处，backlog 盘点 1 处），属当时裁决的原始记录，原文未改；已在 `adapter-capability-decision-2026-10.md` §C 表后追加一条注记说明实情（Owner 选择保留历史原貌、以注记指路）；该注记自身提及此名 2 次，检索时需与历史 11 处区分。(b) 见下一条。
7. **核心文档体量**（事实）：product-prd-generator SKILL.md 960 行、troubleshooting.md 815 行（39 节）、25 个测试文件 250 个测试函数 ✓；material-importer SKILL.md 821 行；AGENTS.md 471 行。AGENTS.md 的「纯提示词 skill 的契约分层」原则要求 SKILL.md 只保留入口、契约正文放 references；上述两份 SKILL.md 是否符合该原则，本轮未逐节核对。
8. **一条 implemented 带着未完成项**（事实，不建议改状态）：pricing-generator × lnkcre 的 notes 写「私有化模式定价待补（SKILL.md 待办）」，该缺口至今未补——SKILL.md 仍标「私有化模式待补充定价」，`config/pricing/pricing-basis.yaml` 仅有 devkit_rate / devkit_cost_basis / tax_rate_default 三键，无私有化费率。标准报价链路有真实运行先例，status 符合 implemented 定义；但只读状态分布看不出私有化报价缺失，需点开 notes。补定价属定价内容，需 Owner 提供费率。

## 复现

```bash
bash references/scripts/check_skill_ecosystem.sh --ci                 # P0 32 / P1 20
COMPANY_BASE=/opt/code/docs/lanlnk LANLNK_BASE=/opt/code/docs/lanlnk \
  bash references/scripts/check_docs_consistency.sh                    # 44 pass
find skills -mindepth 3 -maxdepth 3 -name SKILL.md -type f | wc -l   # 32
find .agents/skills -mindepth 1 -maxdepth 1 -type d | wc -l          # 12
git log --oneline 93ae62d..HEAD | wc -l                              # 85
grep -rnE '^## (ADDED|MODIFIED|REMOVED) ' openspec/specs | wc -l     # 0
```
