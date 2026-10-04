# B7 执行记录 —— docs 侧跨仓引用对齐（2026-10-04）

```text
STATUS: COMPLETED（C1 最小修改；C2 verified-no-change）
OWNER SIGN-OFF: NOT RECORDED（仅会话授权，无独立签署记录）
AUTHORIZATION: MECH-BATCH-STANDING（一次性批量放行，用户会话授权）
SCOPE: B7 only（docs 仓两处 registry 跨仓引用对齐）
```

> **记录性质（必读）**：本文件是 B7 的**执行记录**，由执行会话落盘，验证结果均为本会话
> 实测。授权来源 = `references/adapter-capability-owner-decision-mechanical-batch-standing-2026-10-04.md`
> （MECH-BATCH-STANDING，session_consent）。它不是、也不得被引用为独立签署的 owner
> 批准记录（与 B1/B2/B5/B3/B4/B6/lnkcrm-freeze-reconcile 同口径）。B7 完成**不构成**
> registry 删除、adapter_status 删除或 O4 字段删除批准。

## 1. 依据

- 迁移审计 §1-C1（`30-products/external-owner-decisions-2026-10-02.md:5` 回填通道
  描述）、§1-C2（`domain-architecture-migration-2026-09-26.md:33` 历史注记）、§4-B7。

## 2. 工作区重叠检查（本会话实测）

```bash
cd /opt/code/docs
git status --short -- lanlnk/30-products/external-owner-decisions-2026-10-02.md \
  "lanlnk/30-products/lnkcre/reconciliation/domain-architecture-migration-2026-09-26.md"
# 输出为空（exit 0）——两目标文件与既有未提交修改零重叠
```

docs 仓既有未提交修改（BACKUP.md / indexes / lnkcre INDEX / PRD 增量 v0.2 系列等
M + untracked）均不涉及两目标文件 → **无 blocked-by-worktree-overlap**，两目标可
独立应用。

## 3. C1：回填通道描述对齐（最小修改）

文件：`/opt/code/docs/lanlnk/30-products/external-owner-decisions-2026-10-02.md`（仅 :5
一行）。

原文：

```markdown
> 回填通道：`product-registry-feedback.yaml`（docs）→ `product-registry.yaml` + `_paths.py`（skill，已同步，提交走 skill 治理线）。
```

改为（单行替换，git diff 单 hunk 单行）：

```markdown
> 回填通道（2026-10-04 B7 对齐）：`product-registry-feedback.yaml`（docs）→ 当前有效目标 = `company.yaml` products（唯一产品台账，经 onboarding 契约 `scripts/onboard.sh product` 维护）+ skill 侧 resolver `_paths.resolve_product_paths()`（经 shared.product_context）+ `30-products/<产品>/` 产品治理记录。2026-10-02 时点原通道目标 `product-registry.yaml` + `_paths.py` 已自 2026-10-04 起降级为迁移期兼容元数据/历史镜像（B2/B3/B4 迁移，见 skill 仓 `references/product-registry-迁移审计-2026-10-04.md`）；当时「已同步，提交走 skill 治理线」为历史事实保留。
```

文案依据（均为本轮会话实物核验）：

- `COMPANIES.md`（docs 仓）§2/§5：`scripts/onboard.sh product <company> <pid>` →
  company.yaml products 台账（唯一产品台账；`onboard.sh` 实物存在）；
- skill 仓 AGENTS.md：Check 4 产品目录对账面 = company.yaml products（B2 迁移后）；
- `product-registry.yaml` 头部规则 1（B3：onboarding 契约为注册入口）与本日 B4 后
  规则 6（resolver 为路径解析唯一权威源，registry 为迁移期兼容元数据/历史镜像）；
- 历史证据指针保留：`product-registry-feedback.yaml`（docs）、原通道两目标名、
  「已同步，提交走 skill 治理线」时点事实均未删除，仅标注为历史。

## 4. C2：历史注记（verified-no-change）

文件：`/opt/code/docs/lanlnk/30-products/lnkcre/reconciliation/domain-architecture-migration-2026-09-26.md:33`：

```markdown
- skill 仓 `references/product-registry.yaml` 的 `ontology_note`（描述 20-architecture 指向）将过时：描述性注记，skill 会话自理。
```

判定 **verified-no-change**：

- 属带日期（2026-09-26）历史记录的「未迁移项（另行裁定）」节，记录当时状态与预测；
- 该预测已发生并被解决——现行 registry lnkcre `ontology_note` 已指向
  `30-products/lnkcre/ontology/README.md`（新布局，本会话读 registry :76 实证），
  不存在「当前仍会误导维护者的机制描述」；
- 按 B7 规则 2：只是历史事实、无现行机制误述 → 不为追求统一重写历史记录，零改动。

## 5. 验证（本会话实测）

- `git diff --check`（docs 仓）：通过；
- `git diff --name-only`（docs 仓）：本轮仅新增
  `lanlnk/30-products/external-owner-decisions-2026-10-02.md` 一个 M（单行 hunk），
  其余 M/untracked 与执行前快照完全一致；C2 目标文件不在 diff 中（零改动实证）；
- skill 侧全 suite 复核（同一会话实测，见 B4/B6 记录 §5）：shared 53 OK /
  prd-gen 169 passed / 3 skipped / check_docs_consistency.sh FAIL=0 WARN=0 PASS=33
  ——docs 侧改动不影响 skill 侧任何测试。

## 6. 未触碰的冻结范围

`/opt/code/docs/lanlnk/config/company.yaml`、`30-products/**` 的产品内容（C1 目标为
治理决策记录文档，非产品内容；C2 零改动）、`/opt/code/lnkcrm/**`、任何产品代码仓、
resolver 生产逻辑、product-registry.yaml（B7 未触碰 skill 仓任何文件）、O4 字段删除、
O5 其他子项、O6-O11、docs 仓既有未提交修改（全部原样保留）。未提交、未推送、未使用
git add -A。

## 7. 状态

**completed**（C1 实际修改 + 验证完成；C2 verified-no-change）。授权来源
MECH-BATCH-STANDING（用户会话授权），独立 owner 签署不存在（OWNER SIGN-OFF:
NOT RECORDED）。
