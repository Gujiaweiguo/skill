# doc-generator

Web 应用操作手册生成器 Skill。基于 **运行时探测 + 源码 hint + Playwright 协作 + 纯函数渲染** 方案，为 Vue3/React/Next/Nuxt 等 SPA 应用自动生成图文并茂的操作手册，同时输出 LangChain RAG 友好的 `chunks.jsonl` 与 `llms.txt`。

## 核心能力

- **任意 SPA 框架**：Vue3 / React / Next.js / Nuxt / 其他（运行时优先，框架仅作 hint）
- **Playwright 自动截图**：调用内置 `playwright` skill，使用文本/角色定位器（不用 CSS 选择器）
- **双 RAG 输出**：`操作手册.md`（人类阅读）+ `chunks.jsonl`（LangChain Document 格式）+ `llms.txt`（llmstxt.org 规范）
- **风格参考支持**：传入参考手册影响输出风格（非内容来源）
- **增量更新**：复用 `analysis.json` 只重做变更模块
- **优雅降级**：Playwright / dev server 不可用时仍出手册（图位占位）

## 环境要求

| 项 | 要求 |
|---|---|
| Python | 3.10+ |
| 依赖管理 | uv（不用 pip） |
| 环境变量 | `$USERGUIDE_BASE`（默认 `/opt/code/docs/UserGuide/`） |
| 内置 skill | `playwright`（MCP，P3 阶段加载） |
| 目标应用 | 运行中的 SPA dev server（默认探测 5173/3000/8080） |

## 快速开始

```bash
# 1. 设置环境变量
export USERGUIDE_BASE=/opt/code/docs/UserGuide

# 2. 安装依赖（一次性）
cd /opt/code/skill/skills/docs/doc-generator
uv sync --extra dev

# 3. 启动目标应用的 dev server（在另一个终端）
cd /opt/code/your-vue-app
npm run dev

# 4. 触发 skill（在 OpenCode 对话中）
# 直接说："为 /opt/code/your-vue-app 生成操作手册"
```

## 输入输出布局

```
$USERGUIDE_BASE/
├── _input/                                 ← 输入（首次运行 skill 自动创建）
│   └── {软件名}/                           ← 与输出软件名一一对应
│       ├── references/                     ← 参考资料目录（任意格式）
│       │   ├── 阿里云RDS操作手册.md
│       │   └── urls.txt                    ← 一行一个URL
│       ├── config.yaml                     ← 可选：per-app 配置
│       └── .auth.json                      ← 自动生成：登录凭据（gitignored）
│
└── {软件名}/                               ← 输出（skill 生成）
    ├── 操作手册.md                         ← 人类阅读 + 标准 LangChain ingestion
    ├── chunks.jsonl                        ← 高质量 RAG ingestion（LangChain Document）
    ├── llms.txt                            ← llmstxt.org 规范的 LLM 摘要
    ├── manifest.json                       ← 截图执行日志
    ├── analysis.json                       ← P1 应用结构发现结果
    └── imgs/                               ← 所有截图
```

**软件名发现优先级**：`package.json:name` → 源码目录名 → 用户指定 → 兜底询问。

## 软件名命名规则

- `package.json` 的 `"name": "mysqlbot"` → 使用 `mysqlbot`
- `@scope/mysql-bot` → 去掉 scope，使用 `mysql-bot`
- 含空格/大写 → 转 kebab-case：`MySQL Bot v2` → `mysql-bot-v2`

## CLI 参数（agent 调用时使用）

| 参数 | 说明 |
|---|---|
| `--port <N>` | 指定 dev server 端口（跳过自动探测） |
| `--no-auth` | 跳过登录流程（只截图公开页面） |
| `--auth-user <user>` | CI 场景：直接传用户名（不写入 .auth.json） |
| `--auth-pass <pass>` | CI 场景：直接传密码 |
| `--full` | 强制全量重做（不询问增量 vs 全量） |

## 参考资料传入

三种方式并存：

| 方式 | 位置/语法 | 何时用 |
|---|---|---|
| **A. 文件** | `_input/{name}/references/*`（任意格式：md/docx/pdf/pptx/html） | 长期参考、团队共享 |
| **B. URL** | `_input/{name}/references/urls.txt`，一行一个 | 在线文档、官方 help center |
| **C. 对话内联** | 对话里说"参考 https://..."或粘贴片段 | 一次性灵感 |

支持的文件格式：`.md` / `.txt` / `.html`（直读）、`.docx` / `.pptx`（markitdown）、`.pdf`（pypdf）、URL（webfetch）。其他格式跳过并警告。

## 凭据安全

首次运行时，agent 会询问登录凭据并写入：

```
$USERGUIDE_BASE/_input/{name}/.auth.json    # mode 0600
```

**必须加入 `.gitignore`**：

```gitignore
# 在你的仓库根 .gitignore 中加入
$USERGUIDE_BASE/_input/**/.auth.json
# 或者如果你的 $USERGUIDE_BASE 在仓库外（推荐），无需配置
```

二次运行复用同一份 `.auth.json`，不再询问。

## RAG 集成示例

### 标准 LangChain 加载（用 Markdown）

```python
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter

loader = TextLoader("$USERGUIDE_BASE/mysqlbot/操作手册.md")
docs = loader.load()

splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
)
chunks = splitter.split_text(docs[0].page_content)
```

### 高质量 RAG（用预切块）

```python
from langchain_core.documents import Document
import json

docs = []
with open("$USERGUIDE_BASE/mysqlbot/chunks.jsonl") as f:
    for line in f:
        d = json.loads(line)
        docs.append(Document(page_content=d["page_content"], metadata=d["metadata"]))

# 直接进向量库
vector_db.add_documents(docs)
```

每个 chunk 自带丰富元数据：`module` / `subsection` / `step` / `page_url` / `screenshots[]` / `element_texts[]`，召回时前端可据此渲染对应截图。

## 开发

### 运行单测

```bash
cd /opt/code/skill/skills/docs/doc-generator
uv run pytest scripts/ -v
```

### 单独调用 renderer（纯函数）

```bash
uv run python scripts/render_manual.py \
  --analysis examples/analysis.example.json \
  --manifest examples/manifest.example.json \
  --style-fingerprint examples/style-fingerprint.example.json \
  --output-dir /tmp/render-output
```

## 限制（MVP）

- iframe 嵌入的微前端页面不发现/不截图
- 多语言手册（en/zh）— MVP 仅中文
- 自定义 per-app Jinja2 模板不支持
- 图像 captioning（多模态 RAG）不支持
- OAuth/SSO 登录流程不自动处理（仅 username/password 表单）
- WebSocket 依赖的 UI 可能无法稳定截图

完整限制清单与 v2 路线图见 `references/limitations.md`。

## 目录结构

```
skills/docs/doc-generator/
├── SKILL.md                    ← 主指令文档（agent 执行时读取）
├── README.md                   ← 本文件
├── pyproject.toml              ← Python 依赖（jinja2 + pytest）
├── references/                 ← Schema 与模板（8 个文件）
│   ├── analysis-schema.md
│   ├── screenshot-plan-schema.md
│   ├── manual-template.md
│   ├── chunks-jsonl-schema.md
│   ├── llms-txt-format.md
│   ├── style-fingerprint.md
│   ├── config-yaml-schema.md
│   └── limitations.md
├── scripts/
│   ├── render_manual.py        ← 纯函数渲染器
│   └── test_render_manual.py   ← pytest 单测
└── examples/                   ← 示例输入文件
    ├── analysis.example.json
    ├── screenshot-plan.example.json
    ├── manifest.example.json
    └── style-fingerprint.example.json
```
