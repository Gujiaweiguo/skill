---
name: docs-archive-manager
description: |-
  资料归档预审与漂移修复 Skill。补 backup.sh 体系的两个交互缺口：
  (1) classify——提交前分类预审，对抗 git add -A 的语义盲提交；
  (2) drift-fix——解析 check-drift.sh 报告并给出索引修复方案。
  纯编排型，不重复 backup.sh / check-drift.sh / snapshot.sh / restore.sh 的脚本职责。
  触发场景："提交前帮我分类"、"这次改动该不该一把梭 git add -A"、"check-drift
  说有新目录未索引"、"X 目录该建索引吗 / 该进 git 吗"、"漂移怎么修"、"backups
  该怎么处理"、"docs archive manager"。
  不触发场景：单纯跑备份/快照/恢复（直接调对应脚本）；生成业务内容（交给 PPT/Word/
  PRD/投标等 skill）；删除/清空/Git 历史瘦身（本 skill 只做风险评估，等用户确认）。
compatibility: |-
  Pure prompt skill. No runtime dependency.
  Depends on: scripts/backup.sh, scripts/check-drift.sh, scripts/snapshot.sh,
  scripts/restore.sh, BACKUP.md, indexes/, .gitignore
  Default docs root: /opt/code/docs. Default Baidu Sync target: /mnt/d/BaiduSyncdisk/docs.
---

# Docs Archive Manager / 资料归档预审与漂移修复

## 定位（先读这段）

本 skill 是 backup.sh 体系的**编排补丁**，不是替代。项目的备份/校验/快照/恢复能力
已全部沉淀进 scripts/，本 skill 只补两个脚本做不了的交互缺口：

| 你想做的事 | 调什么 | 本 skill |
|---|---|---|
| 扫描工作区状态 | `bash scripts/check-drift.sh` + `git status` | 不重复 |
| 更新 checksum + 百度盘 + git 提交 | `bash scripts/backup.sh` | 不重复 |
| 做百度盘快照 | `bash scripts/snapshot.sh` | 不重复 |
| 恢复 / 演练 | `bash scripts/restore.sh` | 不重复 |
| **提交前想看清哪些该进、哪些不该进** | — | **classify mode** |
| **check-drift 报了漂移，想知道怎么修** | — | **drift-fix mode** |

`backup.sh` 默认 `git add -A` + 二进制守卫，适合"我就想把当前状态全部备份"。
但当你想**语义清晰地分批提交**（比如本次改动混了 ADR 文档 + 临时脚本 + 配置，应分开），
或 check-drift 报了**未索引的新目录**（比如 `backups/`）需要决定怎么登记时，用本 skill。

## 核心原则

1. **先扫描再行动**：任何 mode 第一步都是 `git status --short` + `bash scripts/check-drift.sh`，不要凭记忆。
2. **不自动 staging**：classify 只输出清单；staging 动作交给用户或显式确认后执行。
3. **不与 backup.sh 冲突**：classify 的产出是"建议"，不否定 backup.sh 的 `git add -A` 设计；两种风格并存，按场景选。
4. **drift-fix 必须给可执行方案**：不只说"建索引"，要给出索引文件路径、内容草稿、应登记到哪些文档（indexes/README.md、BACKUP.md §7）、check-drift.sh 是否要加白名单。
5. **不自动删除**：删除/清空/`rsync --delete`/Git 历史瘦身必须二次确认。

## 文件分类规则（classify 用）

### A. 适合进 GitHub（轻量控制层）
`*.md` `*.txt` `*.yaml` `*.yml` `*.json`(无密钥) `*.toml` `*.sh` `*.js` `*.py`(轻量脚本) / README / BACKUP / indexes / prompts
前提：体积小、无敏感信息、需长期版本历史。

### B. 只进百度同步盘（大文件/交付件）
`*.pdf` `*.ppt(x)` `*.doc(x)` `*.xls(x)` `*.png` `*.jpg` `*.jpeg` `*.mp4` `*.mov` `*.zip` `*.rar` `*.7z`
原始客户资料 / 最终交付大文件 / skill 完整输出。
（项目已用 `.gitignore` 兜底；classify 主要识别"漏网"或"误加"。）

### C. 默认忽略或只进百度盘（过程产物）
`tmp/` `**/.build*/` `**/.render*/` `node_modules/` `.venv/` `.codegraph/` `.omo/` `.codex/`
`lanlnk/**/raw/` `lanlnk/**/input/` `lanlnk/**/parsed/`

### D. 需要用户确认
大量 `deleted` / 目录改名或合并 / 疑似客户敏感资料 / GitHub 历史清理 / 百度盘旧目录清空 / `rsync --delete`

---

## mode: classify（提交前预审）

**目标**：在 `git add` 之前，把当前改动按 A/B/C/D 分档，输出可执行 staging 建议。

必须先执行：
```bash
cd /opt/code/docs
git status --short
git diff --stat
```

输出格式：
```
分类预审（共 N 项变更）

A 进 GitHub（轻量控制层）：
- path/to/file.md  原因

B 只进百度盘（应被 .gitignore 兜底；若出现在暂存区是异常）：
- path/to/file.pptx  ⚠ 检查 .gitignore

C 忽略/过程产物（不应进 git）：
- tmp/...

D 需确认：
- deleted path/...  疑似迁移？

建议 staging 方式（二选一）：
[1] 一把梭：直接 bash scripts/backup.sh（git add -A + 二进制守卫兜底）
[2] 分批提（推荐本场景，因为 XXX）：
    git add <A 档文件清单>
    git commit -m "..."
    # B/C/D 档处理说明
```

决策提示：
- A 档全是同一主题 → `backup.sh` 一把梭即可
- 混了多个无关主题（如本次：ADR 文档 + 临时脚本 + 配置）→ 推荐分批
- D 档任何一项未确认 → 阻断，等用户

---

## mode: drift-fix（漂移修复编排）

**目标**：解析 `check-drift.sh` 报告，给出索引修复的可执行方案。

必须先执行：
```bash
cd /opt/code/docs
bash scripts/check-drift.sh
```

识别报告里的两类漂移：

### 漂移类型 1：新目录未建索引
报告形如：`⚠ 新目录未建索引：- backups`

逐项目录，给出**定位 → 处理方式 → 可执行 diff**：

**步骤 1 · 定位目录语义**：
- 查 `.gitignore` 是否已排除（排除 = 不进 git，仅本地/百度盘）
- 查 `BACKUP.md §7` 目录结构是否已登记
- 查目录现有内容推断用途
- 若空目录：推断为预留位，需要用户确认预期用途

**步骤 2 · 决定处理方式（四选一）**：

| 方式 | 适用 | 动作 |
|---|---|---|
| (a) 建独立索引 | 资料域级新目录，会持续沉淀内容 | 建 `indexes/<dir>.md` + 登记 indexes/README.md 资料域表 + BACKUP.md §7 |
| (b) 归并到父索引 | 是某资料域的子目录 | 在父 `indexes/<parent>.md` 加一节，不动 README/BACKUP |
| (c) 不建索引 + 注明 | 纯本地运行产物（gitignored，非资料域） | BACKUP.md §7 注明"本地临时，不进 git/不建索引"；check-drift.sh 加白名单过滤 |
| (d) 删除 | 误建空目录 | `rmdir <dir>` |

**步骤 3 · 给出可执行 diff**：每个要改的文件都写清楚新增内容草稿，让用户一眼能确认。

### 漂移类型 2：索引记录的目录已不存在
报告形如：`⚠ 索引记录的目录已不存在：- oldname`

修复：
1. 确认是改名还是删除（`git log --oneline -- <path>` / `git log --diff-filter=R`）
2. 改名 → `indexes/<old>.md` 重命名为 `indexes/<new>.md` + 更新 README 资料域表 + BACKUP.md §7
3. 删除 → 删 `indexes/<old>.md` + 更新 README 资料域表 + BACKUP.md §7

输出格式：
```
漂移修复方案

报告摘要：
- 新目录未索引：backups
- 索引目录已消失：（无）

逐项方案：

【backups】
定位：.gitignore 第 46 行已排除 → 不进 git 的本地目录；当前为空
建议处理：方式 (c) —— 不建独立索引 + BACKUP.md §7 注明 + check-drift.sh 白名单
理由：<给出理由>

需要修改的文件：
1. BACKUP.md §7 目录树，加一行：
   backups/               本地临时备份归档（gitignored；不进 git/不建索引/不单独同步百度盘）
2. indexes/README.md "维护规则" 补一条：
   - backups/ 等纯本地目录不建索引（避免漂移噪声）；check-drift 报告时按 drift-fix 方式 (c) 处理
3. scripts/check-drift.sh 的 ACTUAL_DIRS 过滤加白名单：
   ! -name 'backups'

请确认后我执行。
```

---

## 决策规则

### 是否清空 GitHub 仓库？
默认不清空、不重写历史。从当前时间点轻量化即可。仓库已无法 push/clone 时才单独讨论 `git filter-repo`。

### 是否清空百度同步盘？
默认不清空。切结构时先建 `docs-v2/` 或 `docs-snapshots/<日期>/`，跑通 `restore.sh --target` 再决定。

### 大量 deleted 怎么办？
先判断：①目录改名？②内容迁移？③只是被 `.gitignore` 排除？④百度盘是否有副本？
确认后分批提交删除，不要混进普通文档更新。

---

## 输出模板

```
归档编排结果

模式：classify / drift-fix
扫描输入：N 项变更 / M 项漂移
A 进 GitHub：N
B 百度盘：N
C 忽略：N
D 需确认：N

已执行：
- ...

未执行/需确认：
- ...

建议下一步：
- ...
```

## 已知限制

- 百度同步盘是同步工具不是版本备份；重要节点必配合 `snapshot.sh`。
- `checksums.sha256` 只证内容一致，不证策略合理。
- classify 依赖 `.gitignore` 准确；`.gitignore` 漏配时 B 档会误判。
- drift-fix 不能替用户决定"这个目录该不该存在"，只给方案让用户拍板。
- check-drift.sh 白名单是"承认它是本地目录、不再报告"的正式方式，比"反复 dismiss"更干净。
