---
name: docs-archive-manager
description: 资料归档与备份治理 Skill。用于把"输入资料 + skill 生成资料 + 轻量索引 GitHub 仓库 + 百度同步盘完整资料库"分层管理。触发场景："整理备份策略"、"归档这些生成文件"、"扫描哪些该进 GitHub 哪些该进百度云盘"、"更新资料索引"、"同步百度云盘"、"做资料恢复演练"、"docs archive manager"。适合 /opt/code/docs 这类非代码型资料仓库，不负责生成业务内容。
compatibility: |-
  Pure prompt skill. No runtime dependency.
  Assumes Linux/WSL2 shell with git, rg, rsync, sha256sum.
  Default docs root: /opt/code/docs. Default Baidu Sync target: /mnt/d/BaiduSyncdisk/docs.
---

# Docs Archive Manager / 资料归档与备份治理

## 目标

把资料型工作区从“所有文件都尝试进 GitHub”调整为：

```text
GitHub        = 轻量索引、说明、提示词、配置、少量 Markdown
百度同步盘    = 完整资料库，保存输入文件、生成文件、大文件和交付件
本地工作区    = 当前编辑与生成现场
```

本 skill 不生成 PPT、Word、PRD、报告或代码；它只负责在资料生成前后做扫描、分类、索引、备份、校验和恢复演练。

## 触发场景

使用本 skill 当用户说：

- “整理备份策略”
- “归档这些生成文件”
- “扫描哪些该进 GitHub 哪些该进百度云盘”
- “更新资料索引”
- “同步百度云盘”
- “做资料恢复演练”
- “把这个资料目录治理一下”
- “docs archive manager”

尤其适用于 `/opt/code/docs` 这类目录：用户输入原始资料，调用 skill 生成 PPT/PDF/Markdown/图片/脚本，再需要归档和备份。

## 不触发场景

- 单纯生成业务内容：交给 PPT、Word、PRD、投标、手册等对应 skill。
- 代码项目的构建、测试、部署：交给项目自己的工程流程。
- 用户要求删除、清空、重写 Git 历史：本 skill 只能先做风险评估并等待明确确认。

## 核心原则

1. **GitHub 不做完整资料备份**：避免仓库超过容量、历史膨胀、clone/push 变慢。
2. **百度同步盘保存完整资料**：大文件、生成结果、输入资料、过程文件都可以放百度盘。
3. **GitHub 保存控制层**：`README.md`、`BACKUP.md`、`indexes/*.md`、提示词、流程、轻量配置。
4. **同步盘不是历史备份**：误删可能同步删除；重要节点建议做快照目录。
5. **不自动删除**：删除、清空、`rsync --delete`、Git 历史瘦身都必须二次确认。
6. **不 `git add .`**：只按分类显式 staging 轻量文件。
7. **先扫描再行动**：所有归档动作前先输出分类清单。

## 默认路径

```text
文档工作区：/opt/code/docs
百度同步盘：/mnt/d/BaiduSyncdisk/docs
百度快照目录：/mnt/d/BaiduSyncdisk/docs-snapshots/YYYY-MM-DD
GitHub 轻量索引目录：/opt/code/docs/indexes
```

如用户给出不同路径，以用户路径为准。

## 文件分类规则

### A. 适合进入 GitHub

```text
*.md
*.txt
*.yaml / *.yml
*.json（不含密钥/隐私/大数据样本）
*.toml
*.sh（轻量脚本）
*.js / *.py（用于复现生成流程的轻量脚本）
README / BACKUP / indexes / workflows / prompts
```

前提：文件体积小、无敏感信息、长期需要版本历史。

### B. 只进百度同步盘

```text
*.pdf
*.ppt / *.pptx
*.doc / *.docx
*.xls / *.xlsx
*.png / *.jpg / *.jpeg
*.mp4 / *.mov / *.m4v
*.zip / *.rar / *.7z / *.tar.gz
原始客户资料
最终交付大文件
skill 生成的完整输出
```

### C. 默认忽略或只进百度盘的过程产物

```text
tmp/
**/.build*/
**/.render*/
node_modules/
.venv/
.codegraph/
.omo/
.codex/
```

### D. 需要用户确认

```text
大量 deleted: 文件
目录改名或合并
疑似客户敏感资料
GitHub 历史清理
百度盘旧目录清空
rsync --delete
```

## 工作模式

### mode: scan（只读扫描）

目标：了解当前工作区状态，不改文件。

必须执行：

```bash
git status --short
git diff --stat
rg --files --hidden --no-ignore -g '!/.git/**' | wc -l
```

输出：

```text
1. 当前变更数量：M/D/??
2. 主要目录分布
3. 文件类型分布
4. 高风险项：大文件、删除、目录迁移、未忽略生成物
5. 下一步建议
```

禁止：修改文件、提交、同步、删除。

### mode: classify（分类建议）

目标：输出哪些该进 GitHub、哪些只进百度盘、哪些忽略、哪些需确认。

输出格式：

```text
GitHub 候选：
- path/to/file.md：原因

百度同步盘：
- path/to/file.pptx：大文件/交付件

忽略：
- tmp/...：临时生成物

需要确认：
- deleted path/...：疑似删除或迁移
```

禁止：自动 staging 全部文件。

### mode: index（更新索引）

目标：维护 `indexes/` 下的人类可读索引。

推荐结构：

```text
indexes/
  README.md
  aitalks.md
  creaiskill.md
  lanlnk.md
  opencode.md
```

每个索引至少包含：

```markdown
# <资料域> 索引

## 百度路径
- `/mnt/d/BaiduSyncdisk/docs/<path>`

## GitHub 管理内容
- 说明文档
- 提示词
- 轻量脚本

## 百度盘保存内容
- 输入资料
- 生成结果
- 大文件交付件

## 重要文件
| 文件 | 类型 | 说明 | 是否进 GitHub |
|---|---|---|---|
```

更新索引前必须扫描对应目录；不要凭记忆写。

### mode: backup（备份到百度同步盘）

目标：更新校验清单并同步完整资料到百度盘。

默认安全命令：

```bash
cd /opt/code/docs
rg --files -0 --hidden --no-ignore \
  -g '!/.git/**' \
  -g '!/.venv/**' \
  -g '!/.codegraph/**' \
  -g '!/.codex/**' \
  -g '!/.omo/**' \
  -g '!/**/node_modules/**' \
  -g '!/checksums.sha256' \
  -g '!/.nvimlog' \
  | sort -z \
  | xargs -0 sha256sum > checksums.sha256

sha256sum -c checksums.sha256

rsync -a \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.codegraph/' \
  --exclude '.codex/' \
  --exclude '.omo/' \
  --exclude 'node_modules/' \
  /opt/code/docs/ /mnt/d/BaiduSyncdisk/docs/

cd /mnt/d/BaiduSyncdisk/docs
sha256sum -c checksums.sha256
```

默认禁止 `--delete`。只有用户明确要求“镜像同步并删除百度盘多余文件”时才可讨论使用。

### mode: snapshot（快照）

目标：防同步盘误删扩散。

建议命令：

```bash
SNAPSHOT=/mnt/d/BaiduSyncdisk/docs-snapshots/$(date +%F)
mkdir -p "$SNAPSHOT"
rsync -a /mnt/d/BaiduSyncdisk/docs/ "$SNAPSHOT"/
```

快照频率建议：

- 每周一次普通快照。
- 每个重要交付前后各一次。
- 大规模整理/删除前必须一次。

### mode: restore-drill（恢复演练）

目标：验证“GitHub 轻量仓库 + 百度完整资料”可恢复。

流程：

```bash
rm -rf /tmp/docs-restore-git-baidu
git clone <repo-url-or-local-repo> /tmp/docs-restore-git-baidu
rsync -a /mnt/d/BaiduSyncdisk/docs/ /tmp/docs-restore-git-baidu/
cd /tmp/docs-restore-git-baidu
sha256sum -c checksums.sha256
```

通过标准：

```text
restore-checksum-ok
关键索引文件存在
抽样打开 Markdown/PDF/PPT/图片正常
```

## Git 提交流程

只提交轻量控制层：

```bash
git add BACKUP.md .gitignore checksums.sha256
git add indexes/*.md workflows/*.md prompts/*.md
git status --short
git commit -m "docs: 更新资料归档索引"
```

禁止：

```bash
git add .
git add <大资料目录>/
```

若有目录迁移，单独提交；若有 `.gitignore` 调整，先提交 `.gitignore` 再 staging 新目录。

## 决策规则

### 是否清空 GitHub 仓库？

默认不清空、不重写历史。先从当前时间点开始轻量化。只有仓库已经无法 push/clone，才单独讨论 `git filter-repo` 历史瘦身。

### 是否清空百度同步盘？

默认不清空。若要切换结构，先建 `docs-v2/` 或 `docs-snapshots/YYYY-MM-DD/`，跑通恢复演练后再决定是否归档旧目录。

### 大量 deleted 怎么办？

先判断：

1. 是否目录改名？
2. 是否内容迁移到新目录？
3. 是否只是被 `.gitignore` 排除了？
4. 百度盘是否已有完整副本？

确认后再分批提交删除；不要混进普通文档更新。

## 输出模板

每次执行后用下面格式汇报：

```text
归档治理结果

模式：scan/classify/index/backup/snapshot/restore-drill
GitHub 候选：N
百度盘候选：N
忽略候选：N
需确认：N

已执行：
- ...

未执行/需确认：
- ...

建议下一步：
- ...
```

## 已知限制

- 百度同步盘是同步工具，不是严格版本备份；必须配合快照降低误删风险。
- `checksums.sha256` 只证明文件内容一致，不证明目录策略合理。
- 旧 Git 历史中的大文件不会因为 `.gitignore` 变小；历史瘦身是独立高风险任务。
- Windows/WSL2 路径大小写、空格和中文文件名可能影响脚本；命令中路径必须加引号。
