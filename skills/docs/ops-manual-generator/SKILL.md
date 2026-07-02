---
name: ops-manual-generator
description: |-
  系统部署与维护手册生成器 Skill。提供「部署手册」与「维护手册」两套章节模板，
  agent 读取项目的 IaC 文件（Dockerfile/docker-compose/nginx/.env）后按模板填内容，
  生成人类可读的 Markdown 手册。与 doc-generator（用户操作手册）并列，
  输出共存于 $USERGUIDE_BASE/{name}/。RAG 系统可直接读取生成的 Markdown，无需额外切块格式。
  触发场景："为这个系统写部署手册"、"生成运维文档"、"出一份维护手册"、
  "整理这个项目的运维 SOP"、"给客户写部署文档"、"生成数据库备份恢复手册"。
  当用户提供系统源码（含 IaC 文件）并要求生成部署/运维/维护文档时，触发此 skill。
  不触发：用户操作手册（用 doc-generator）；无源码无 IaC 的纯人工描述文档（直接对话写）。
compatibility: >
  Pure template skill — 无 Python 依赖、无脚本、无 uv sync。
  Agent 直接读取 references/ 下的模板文件。
  Requires `$USERGUIDE_BASE` env var (default `/opt/code/docs/lanlnk/UserGuide/`).
---

# Ops Manual Generator - 系统部署与维护手册生成器

为已开发的系统生成**部署手册**和**维护手册**两份运维文档。与 doc-generator（用户操作手册）并列——同一系统的用户手册、部署手册、维护手册共存于 `$USERGUIDE_BASE/{name}/`。

## 工作方式（模板填充，非 pipeline）

```text
1. agent 读项目 IaC 文件
   Dockerfile / docker-compose.yml / nginx.conf / .env.example / CI workflow
        ↓
2. 加载对应模板（references/部署手册-模板.md 或 维护手册-模板.md）
        ↓
3. 按模板逐章填写：
   - 【从X读取】标记 → agent 自动读 IaC 文件提取
   - 【需提供】标记 → 问用户或从源码/历史文档推断
   - 历史运维 SOP（用户提供的旧文档）→ 作为内容来源对齐合并
        ↓
4. 生成 Markdown 手册到 $USERGUIDE_BASE/{name}/（RAG 系统直接读取）
```

**为什么不用自动化 pipeline**：部署/维护手册的核心价值是**运维经验和人工知识**，不是 IaC 文件本身。自动化提取能覆盖 30-40%（端口、镜像、环境变量名），剩下 60-70%（部署步骤组织、故障处理经验、应急预案）必须靠 agent 智能 + 用户输入。所以 skill 定位为「模板包 + 提示词」，把重复劳动（章节结构、格式统一）固化，把内容填写交给对话。

**为什么不出 chunks.jsonl**：RAG 系统直接读取 Markdown 即可（LangChain TextLoader + MarkdownHeaderTextSplitter 标准 ingestion）。预切块的收益不足以抵消维护一套切分脚本的成本。

## 什么时候用这个 skill

- 为客户交付写部署/维护文档
- 已有系统的运维 SOP 整理与标准化
- 配合 doc-generator 的用户手册，补齐运维侧文档（三件套交付）
- 多个同类系统需要统一文档结构

## 什么时候不要用

| 场景 | 该用什么 |
|------|---------|
| 用户操作手册（怎么用功能） | doc-generator（playwright 截图） |
| 没源码也没 IaC 的系统 | 直接对话写（skill 自动化优势用不上） |
| 一次性临时文档 | 直接对话更快 |
| SRE incident response / on-call runbook | 这个 skill 不做（太重） |

## 两份模板

| 模板 | 用途 | 章节 |
|------|------|------|
| `references/部署手册-模板.md` | 给实施/运维看怎么装系统 | 环境要求 / 部署前准备 / 安装部署 / 升级 / 回滚 / 附录 |
| `references/维护手册-模板.md` | 给运维看日常怎么维护 | 系统概览 / 日常巡检 / 备份恢复 / 数据库维护 / 故障处理 / 升级维护 / 应急预案 / 联系方式 |

每个模板的每节都有【从X读取】或【需提供】标记，告诉 agent 该自动提取还是该问用户。

## agent 执行流程（详细）

### Step 1: 识别 IaC 文件

扫描项目根（深度 3，忽略 node_modules/.git/dist/build/target/.venv）：
- `Dockerfile` / `Dockerfile.*`
- `docker-compose.yml` / `docker-compose.yaml` / `compose.yml`
- `nginx.conf` / `*.nginx.conf` / `conf.d/*.conf`
- `.env.example` / `.env.sample`
- `.github/workflows/*.yml` / `.gitlab-ci.yml` / `Jenkinsfile`
- `migrations/` / `db/migrate/` / `*.sql`

**全部缺失时**：告知用户至少提供 Dockerfile 或 docker-compose，否则无法生成有事实依据的手册（变成纯编造）。

### Step 2: 选择模板

- 用户说"部署"→ `references/部署手册-模板.md`
- 用户说"维护"/"运维"→ `references/维护手册-模板.md`
- 用户说"都要"/"全套"→ 两份都生成

### Step 3: 逐章填充

对模板每一节：
1. 看到【从X读取】→ 读对应 IaC 文件，提取事实填入
2. 看到【需提供】→ 评估能否从源码/历史文档推断；不能则向用户提问（**批量收集问题，不要逐个打断**）
3. 看到【标准内容】→ 直接用模板里的标准段落（如 Docker 安装命令）
4. 历史运维 SOP（用户提供的旧 docx/pdf/md）→ 读内容，对齐到对应章节，过时部分标 `[已过时，待人工确认]`

**脱敏铁律**：环境变量值、连接串、密码**永不写明文**，用 `$ENV_VAR` 或 `<from .env>` 占位。

**命令纪律**：所有命令 copy-paste 可执行；破坏性命令（DROP/TRUNCATE/DELETE/`rm -rf`）带 `--dry-run` 或确认提示。

**Markdown 格式要求**（便于 RAG ingestion）：
- 用标准 ATX 标题（`#` / `##` / `###`），RAG 的 MarkdownHeaderTextSplitter 按标题层级切分
- 每个操作步骤用有序列表或 `**步骤 N：**` 加粗
- 代码块标注语言（```bash / ```sql / ```yaml）便于 RAG 元数据提取
- 表格用标准 Markdown 表格语法（`| col |` + `|---|`）

### Step 4: 生成 Markdown（双输出：交付版 + 知识库版）

每个手册产出两份，分目录存放：

| 版本 | 路径 | 用途 | 特征 |
|------|------|------|------|
| 交付版 | `$USERGUIDE_BASE/{name}/{手册名}.md` | 给人看 | 含完整内容、格式化、可转 Word/PDF |
| 知识库版 | `$USERGUIDE_BASE/{name}/知识库版/{手册名}.md` | 给 RAG | 去除图片引用、加版本标注头 |

**为什么分目录**：RAG 系统只需索引 `知识库版/` 子目录，无需在主目录中区分哪些文件该索引。交付版含截图引用对 RAG 无价值（图片路径在向量库里是噪音）。

**知识库版生成规则**：
1. 复制交付版内容
2. 删除所有图片引用行（`![xxx](yyy)`）
3. 保留 `> 图示：xxx` 等文字描述（对 RAG 有语义价值）
4. 文件头插入标注：`> **知识库版** — 已去除图片引用，适用于 RAG 系统上传。完整版见上级目录同名文件。`

agent 生成交付版后，用以下命令批量生成知识库版（部署/维护手册图片少，但仍遵守统一约定）：

```bash
mkdir -p $USERGUIDE_BASE/{name}/知识库版
for f in 部署手册.md 维护手册.md; do
  [ -f "$USERGUIDE_BASE/{name}/$f" ] || continue
  {
    echo "> **知识库版** — 已去除图片引用，适用于 RAG 系统上传。完整版见上级目录同名文件。"
    echo ""
    sed '/^!\[/d' "$USERGUIDE_BASE/{name}/$f"
  } > "$USERGUIDE_BASE/{name}/知识库版/$f"
done
```

软件名发现（4 级优先级）：CLI 指定 > `package.json:name` / `pom.xml:artifactId` / `pyproject.toml:name` > 源码目录名 > 问用户。

RAG 集成示例（用户侧，索引知识库版目录）：
```python
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter

# 只索引知识库版目录（无图片噪音）
loader = DirectoryLoader("$USERGUIDE_BASE/mi/知识库版/", glob="**/*.md")
docs = loader.load()
splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
)
chunks = splitter.split_text(docs[0].page_content)
```

## 与 doc-generator 的协同

同一系统 `$USERGUIDE_BASE/{name}/` 可并存三份手册，**交付版与知识库版分目录**：

```
$USERGUIDE_BASE/{name}/
├── 操作手册.md              ← doc-generator（交付版，含截图）
├── 部署手册.md              ← 本 skill（交付版）
├── 维护手册.md              ← 本 skill（交付版）
├── imgs/                   ← doc-generator 的截图（仅交付版引用）
└── 知识库版/                ← 给 RAG 的统一目录（两 skill 共用）
    ├── 操作手册.md          ← 去图片引用版（doc-generator 产出）
    ├── 部署手册.md          ← 去图片引用版（本 skill 产出）
    └── 维护手册.md          ← 去图片引用版（本 skill 产出）
```

**分工**：
- **交付版**（主目录）：给人看，含截图、格式完整，可转 Word/PDF 给客户
- **知识库版**（子目录）：给 RAG，纯文本无图片，RAG 系统只索引此目录

两个 skill 都遵守「主目录交付版 + `知识库版/` 子目录」的双输出约定。

## 配置

### 环境变量

| 变量 | 默认值 | 作用 |
|------|--------|------|
| `$USERGUIDE_BASE` | `/opt/code/docs/lanlnk/UserGuide/` | 文档根目录 |

无 CLI flags、无 per-app config.yaml、无 Python 依赖——agent 直接对话收集所有变量输入。

## 使用示例

### 示例 1：生成部署手册

> 用户："为 /opt/code/mi 写部署手册"

```text
Agent:
   1. 扫描 /opt/code/mi → 发现 Dockerfile + docker-compose.yml + nginx.conf + .env.example
   2. 加载 references/部署手册-模板.md
   3. 逐章填充：
      - 环境要求：从 compose 读出 MySQL 8.0 + Redis 7 + 端口 8080/3306/6379
      - 环境变量：从 .env.example 读出 12 个变量名（脱敏）
      - 安装步骤：从 compose 的 depends_on 推断启动顺序
      - 【需提供】批量问用户：SSL 证书来源？域名？最小硬件配置？
   4. 用户回答后 → 生成 $USERGUIDE_BASE/mi/部署手册.md
   5. 交付：列出文件路径 + 提示"维护手册可用同一方式生成"
```

### 示例 2：用历史 SOP 生成维护手册

> 用户："整理 mi 项目的运维 SOP"，且提供了厂商交付的运维 docx

```text
Agent:
   1. 读历史 SOP（markitdown 转 md）+ 扫描 IaC 文件
   2. 加载 references/维护手册-模板.md
   3. 逐章对齐：
      - 备份恢复：历史 SOP 的脚本（事实核对 compose 的 DB 镜像版本）
      - 故障处理：历史 SOP 的经验（高价值，原样采纳）
      - 日常巡检：从 nginx location + healthcheck 端点推断 + SOP 补充
   4. 冲突处理：compose 显示 MySQL 8.0，SOP 写 5.7 → 以 compose 为准，SOP 的 5.7 命令标 [已过时]
   5. 生成 维护手册.md
```

## 边界（明确不做）

- **不自动执行运维命令**：生成文档，不执行
- **不做 SRE incident response**：故障处理只做"常见故障 FAQ"，不做完整 on-call 流程
- **不做 K8s/Cloud 平台**：MVP 只覆盖 Docker/compose + Nginx + MySQL/PG + Redis
- **不做 AST 代码分析**：文件读取 + agent 智能足够
- **不生成 Word/PDF/chunks.jsonl**：输出纯 Markdown；需要 Word 时用 word-master 二次渲染；RAG 直接读 md

## 设计决策

详见 `references/design-decisions.md`，记录了从开源调研到方案选型、从自动化 pipeline 转向极简模板、去掉 chunks 输出的完整思考。
