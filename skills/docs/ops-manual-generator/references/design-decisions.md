# Design Decisions — ops-manual-generator

记录本 skill 的设计决策与开源调研结论。**记录"为什么"，不记录"是什么"**——"是什么"看 SKILL.md。

> **⚠️ 决策修订 v2（2026-06-29）**：本 skill 从「自动化 pipeline」转向「极简模板包」。
> 第 1-3、5-6 节仍然有效（开源调研、章节结构、与 doc-generator 协同、历史 SOP 处理）。
> 第 4 节（MVP 范围）、第 7 节（纯函数渲染）、第 8 节（待确认问题）**已废弃**——它们基于 pipeline 假设。
> 完整的 v2 决策见**第 9 节**（文末）。

## 1. 为什么新建 skill 而不扩展 doc-generator

doc-generator 的核心契约是「Playwright 截图 + 纯函数渲染」，整套 P0-P5 围绕 SPA UI 探测。维护手册完全不需要浏览器——输入源是 Dockerfile / docker-compose / CI workflow / k8s manifest / SQL migration / 监控配置 / 历史运维 SOP。

强塞进 doc-generator 会破坏它的：
- 优雅降级模型（playwright 不可用 → 占位符；维护手册没有"截图失败"概念）
- schema 契约（analysis.json 围绕 routes/elements/flows，维护手册围绕 services/commands/health-checks）
- 输入材料分类（references 作为风格指纹 vs 历史 SOP 作为内容来源）

**结论**：并列两个 skill，共享 RAG 输出哲学（chunks.jsonl schema + llms.txt 规范 + 输入输出目录分离），但 pipeline 独立。

## 2. 开源调研结论

| 项目 | 协议 | 能 fork? | 借鉴了什么 |
|------|------|---------|-----------|
| `borghei/Claude-Skills` → runbook-generator | **MIT + Commons Clause** | ❌ 否 | runbook 模板结构（deployment/database/monitoring 三类）、VERIFY 块格式纪律、staleness detection 思路 |
| `reaatech/agent-runbook-generator` → analyzer | TS monorepo，协议待确认 | ❌ 否（TS 不匹配 uv 惯例） | 8 维 stack detection **算法逻辑**（语言/框架/服务类型/结构/配置文件/入口点/外部服务/部署平台） |
| `kirin0198/aphelion-agents` → ops-manual-author | 未明确 | ❌ 否（agent 指令无脚本） | ITIL v4 Service Operation 7 章节结构、placeholder substitution 表 |

### 为什么一个都没 fork

1. **borghei 的 Commons Clause** 禁止"销售"软件本身。本 skill 可能打包进商业交付（商管系统、CRM 的客户运维文档），**法律风险**。且 borghei 的 stack detection 是 agent 手动跑 shell 命令（写在 references 里），不是自动脚本——我们要的是 `stack_detector.py` 自动化，必须重写。
2. **reaatech 是 TS monorepo（14 包）**，引入会破坏仓库 Python+uv 惯例。算法逻辑（文件扩展名统计、package files 关键字匹配、framework→service type 映射）用 Python 重写约 300 行，不值得跨语言依赖。
3. **aphelion 是 Claude agent 指令**（174 行 markdown），假设上游已有 OBSERVABILITY.md / OPS_PLAN.md（我们没有），单一 markdown 输出无 RAG。只学章节结构。

### 协议合规策略

**全部 Python 重写，不引入任何开源代码依赖。** SKILL.md 和 runbook-templates.md 注明"结构灵感来源"。stack_detector.py 的 detection 规则表是我们自己维护的（覆盖商管/CRM 常见栈：Vue/React 前端 + Java/Python/Node 后端 + MySQL/PostgreSQL + Redis + Nginx + Docker），不照抄任何一家的规则。

## 3. 维护手册章节结构决策

综合 aphelion 的 ITIL 7 章 + borghei 的 runbook 类型 + 商管/CRM 业务系统特点，定为 7 章：

| 章节 | 来源 | 为什么保留 / 去掉 |
|------|------|------------------|
| 一、系统概览 | aphelion §1 | 运维人员首要入口：架构、组件、端口、依赖、环境变量 |
| 二、部署与升级 | borghei deployment runbook | 商管系统频繁迭代，部署/升级/回滚是高频操作 |
| 三、启动与停止 | aphelion §2 | 客户现场首次上线、故障重启必需 |
| 四、数据库维护 | borghei database maintenance | 商管数据是核心资产，备份/恢复/迁移/清理不可少 |
| 五、监控与健康检查 | aphelion §3 + borghei monitoring | 日常巡检、故障预警 |
| 六、常见故障处理 | borghei incident（轻量化）| **不做完整 SRE incident response**，只做 top-N 故障 + 诊断 + 修复 |
| 七、联系与升级路径 | aphelion §7 | 客户不知道找谁时兜底 |

**去掉的**：
- aphelion §6 Maintenance Windows —— 商管系统不需要严格变更窗口流程，合并到「二、部署与升级」的注意事项
- aphelion §5 Incident Response（完整版）—— 太重，SRE on-call 场景；商管客户要的是"出问题怎么办"的轻量 FAQ，用「六、常见故障处理」替代

## 4. MVP 范围决策

**MVP 只做 3 类 stack 的 runbook**（覆盖蓝联客户 90% 场景）：
- 前端：Vue3 / React（SPA）
- 后端：Java（Spring Boot）/ Python（FastAPI/Django）/ Node（Express/NestJS）
- 数据库：MySQL / PostgreSQL
- 缓存：Redis
- 部署：Docker / docker-compose / Nginx

**不做**：
- Kubernetes（v2）：蓝联客户多为单机/小集群部署，K8s 是 over-engineering
- Cloud 平台（Vercel/Fly/AWS）：客户私有化部署为主
- Incident Response 完整流程：用轻量"常见故障处理"替代
- 多语言手册：MVP 仅中文

## 5. 与 doc-generator 的关系

| 维度 | doc-generator | ops-manual-generator |
|------|---------------|---------------------|
| 视角 | 终端用户（怎么用功能） | 运维人员（怎么部署维护） |
| 输入 | 运行中 SPA + 源码 + 登录凭据 | 源码 + IaC + 历史运维 SOP |
| 探测方式 | Playwright 运行时截图 | 文件系统扫描 + IaC 解析 |
| 智能来源 | DOM 探测 + 源码 hint | stack detection + LLM 补全 |
| 输出 | 操作手册.md + chunks.jsonl + llms.txt | 维护手册.md + 维护手册-chunks.jsonl + 维护手册-llms.txt |
| 输出目录 | `$USERGUIDE_BASE/{name}/` | `$USERGUIDE_BASE/{name}/`（**同一目录并存**） |

**关键协同**：两个 skill 对同一软件的输出**放在同一目录**（`$USERGUIDE_BASE/{name}/`），用户手册和维护手册并存，RAG 召回时统一索引。chunk schema 字段对齐（`manual_type: "user" | "ops"` 区分），前端可统一渲染。

## 6. 历史 SOP 作为「内容来源」而非「风格参考」

doc-generator 把 references 当**风格指纹**来源（提取 5 维风格特征，不复用内容）——这对用户手册是对的（UI 风格统一即可）。

ops-manual-generator 把历史 SOP 当**内容来源**——客户给的旧版运维文档（厂商交付、历史交接）里的具体步骤（备份脚本、迁移命令、故障处理经验）是要继承的资产。LLM 做对齐合并：

```
源码扫描事实（stack detection + IaC 提取）
    ↓ 权威（实际部署配置）
历史 SOP 内容（references/ 里的 .md/.docx/.pdf）
    ↓ 包装（人类可读的步骤组织、故障经验）
    ↓ LLM 对齐合并：以事实为骨架，以 SOP 包装为血肉
维护手册.md
```

**冲突解决**：源码事实 > 历史 SOP。例如源码检测到 MySQL 8.0，但历史 SOP 写的是 MySQL 5.7 配置，以源码为准，SOP 的过时部分标记 `[已过时，待人工确认]`。

## 7. 纯函数渲染原则（继承 doc-generator D7）

`render_ops_manual.py` 是纯函数：仅读 JSON 输入，仅写 md/jsonl/txt 输出。无网络、无 LLM、无文件系统扫描。所有智能前移到 P1-P3。

理由同 doc-generator：可测试、可重放、可缓存。风格调整只重跑 P4，不重做探测。

## 8. 待确认的开放问题（已废弃，见第 9 节）

> 以下问题基于 v1 pipeline 假设，v2 转向极简模板后不再适用。

- [ ] ~~历史 SOP 的 LLM 合并策略~~ → v2 由 agent 对话处理，不做 pipeline 合并
- [ ] ~~「常见故障处理」的 top-N 故障来源~~ → v2 由模板标准内容 + 历史 SOP + 用户输入三者组合
- [ ] ~~增量更新~~ → v2 不做增量，每次全量生成

---

## 9. 决策修订 v2：从自动化 pipeline 转向极简模板包

### 触发原因

用户反馈"感觉做得有点复杂"，并澄清两个关键事实：

1. **目的**：为已开发好的业务系统（商管/CRM）写部署/维护手册，不是做 SRE on-call runbook
2. **RAG 方式**：用户的 RAG 系统直接读取 Markdown 文件（TextLoader + MarkdownHeaderTextSplitter），不需要预切块的 chunks.jsonl

重新审视后发现 v1 方案错配了场景：

| v1 假设（错配） | 实际场景 |
|---------------|---------|
| 云原生多平台（K8s/Vercel/AWS） | 私有化部署（Docker/compose + Nginx） |
| SRE on-call incident response | 客户运维人员的日常 SOP |
| 需要自动化提取大量事实 | IaC 文件简单，自动化提取只能覆盖 30-40% |
| 需要 RAG 预切块输出 | RAG 直接读 md，预切块是多余的 |

### 新方案：极简模板包

skill 变成 **SKILL.md（提示词）+ 两份模板（部署/维护）+ design-decisions.md**。无脚本、无 Python 依赖、无 pipeline。

agent 工作流：
1. 读 IaC 文件
2. 加载模板
3. 按模板的【从X读取】/【需提供】/【标准内容】标记逐章填内容
4. 生成 Markdown
5. 完（RAG 直接读 md）

### 砍掉的东西

| v1 组件 | v2 处理 | 理由 |
|--------|---------|------|
| `stack_detector.py`（8 维自动检测） | 删除 | agent 读 package.json/pom.xml/compose 文件 3 秒就能判断栈，不值得写 300 行检测脚本 |
| `iac_extractor.py`（IaC 解析） | 删除 | agent 读 Dockerfile/compose 直接提取，不需要专门解析器 |
| `render_ops_manual.py`（纯函数渲染） | 删除 | agent 直接生成 markdown，不需要 Jinja2 渲染器 |
| `md2chunks.py`（markdown→chunks） | 删除 | RAG 直接读 md，不需要预切块 |
| chunks.jsonl / llms.txt 输出 | 删除 | 同上 |
| `analysis-schema.md` 等 7 个 schema 文档 | 删除 | 没有 JSON 中间产物，不需要 schema |
| P0-P5 pipeline | 删除 | 替换为 4 步模板填充流程 |
| pyproject.toml / uv sync / .venv | 删除 | 纯 markdown 模板，无 Python 依赖 |

### 保留的设计原则（v1→v2 不变）

1. **与 doc-generator 并存**：同目录 `$USERGUIDE_BASE/{name}/`，文件名区分（操作手册.md / 部署手册.md / 维护手册.md）
2. **开源调研结论有效**：borghei（Commons Clause 不 fork）/ reaatech（TS 不匹配）/ aphelion（章节结构借鉴）的判断不变
3. **维护手册章节结构**：8 章（系统概览/日常巡检/备份恢复/数据库维护/故障处理/升级维护/应急预案/联系方式）不变
4. **事实 > SOP**：IaC 文件事实权威，历史 SOP 作为包装，冲突标 `[已过时]`
5. **脱敏铁律**：环境变量值/连接串/密码永不写明文
6. **命令纪律**：copy-paste 可执行，破坏性命令带 dry-run

### 新增的设计决策（v2 独有）

1. **模板标记体系**：每节用【从X读取】/【需提供】/【标准内容】标记，告诉 agent 该自动提取、该问用户、还是直接用标准段落。这是"模板填充"模式的核心——把 agent 的注意力引导到正确的地方。
2. **标准内容兜底**：模板里预置了 Docker 安装命令、MySQL/PG 备份恢复命令、Redis 故障处理等标准内容。agent 生成时直接采用，保证最低质量基线。这些标准内容是**我们自己写的**，不 fork 任何开源代码。
3. **Markdown 格式要求**：明确要求 ATX 标题、代码块标注语言、标准表格——确保 RAG 的 MarkdownHeaderTextSplitter 能正确切分。
4. **批量提问**：模板的【需提供】标记让 agent **批量收集问题后统一问用户**，而不是逐节打断对话。提升体验。

### 为什么这个方案更好

- **开发成本**：v1 需要 3 天写 3 个脚本 + 7 个 schema 文档；v2 只需写 2 个模板（已完成）
- **维护成本**：v1 改章节要改 Jinja2 模板 + renderer + schema 三处；v2 只改模板 markdown 一处
- **灵活性**：v1 的 pipeline 锁死了输出结构；v2 的 agent 可以根据项目特点灵活调整
- **用户控制**：v1 的自动化让用户感觉是黑盒；v2 的对话式填充让用户全程可见可干预
