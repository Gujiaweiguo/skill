# Verification — inspect-material-source-fragments

日期：2026-11-14。验收人：Orchestrator（apply 会话）。基线 skill HEAD：`1fc24ab`
（与 proposal 声明的规划基线 `1fc24ab1b3bf1824d904cde95541b671b446bd8f` 一致）。

## 1. 实施顺序（先补失败回归再实现）

1. **先写全部回归**（任务 1.1 + 2.1 两组，共 19 个用例）+ fixtures_registry 登记。
2. **红跑记录**（旧实现，2026-11-14，`uv run pytest tests/test_provenance_inventory.py
   -q -k "MaterialFragment"`）：**14 failed, 5 passed**（日志
   `/tmp/opencode/imsf/red-run.log`，失败历史保留不删）。
   - 14 个失败 = 待实现行为（片段字段/发现/rc3/repair 分支/排序/full-hash 观测）。
   - 5 个红跑即通过 = **兼容守卫**（旧实现本就正确，防回归）：字面#文件优先、
     四条描述性来源保持、none/缺来源保持、完整路径 stat 失败不回退（EACCES）、
     完整路径越界不回退。
3. 再实现 D1/D2/D3（仅 materials 局部 + 私有辅助，共享 `resolve_declared_source`
   未动），全部转绿。

### 实现过程中的两次修正（诚实记录，非事后美化）

- 红跑第 1 轮中 `test_restricted_syntax_guards` 的失败部分源于**测试编写缺陷**
  （控制字符用例用 `\n`，frontmatter 行级解析本就截断，改用 `\t` 才真实可达）。
- 零写入快照 `snapshot()` 对自环 symlink 抛 ELOOP → 新增 `snapshot_all()`
  （symlink 按链接目标记录）。
- 绿跑两轮修正实现：pathlib `resolve` 把 ELOOP 包成 `RuntimeError`（非 OSError，
  共享 resolver 语义不动）→ materials 局部承接为观察失败，并补 stat 探针取
  errno 证据（`errno 40 ELOOP`），维持不可验证清单的 errno 纪律。

## 2. 规格场景 ↔ 回归映射（8/8）

| # | Spec 场景 | 回归用例（tests/test_provenance_inventory.py） |
|---|---|---|
| 1 | 完整文件名含井号优先 | `MaterialFragmentSourceSyntaxTest::test_literal_hash_path_wins_over_truncated_container`（字面文件与截断容器同时存在 → 不拆、不查截断路径） |
| 2 | 容器存在而锚点未核验 | `test_jsonl_fragment_container_accessible_anchor_not_verified`（原整串保留、`anchor_verification=not-performed`、不再记 missing_original、独立发现 rc3）+ `test_anchor_only_finding_drives_rc3`（仅锚点未核验即 rc3；`scan.complete=true` 不代表锚点已核验） |
| 3 | 容器缺失与观察失败区分 | `test_container_missing_records_container_not_whole_string`（missing_original 记容器+保留原声明/fragment）/ `test_container_directory_not_usable`（目录不当可用容器、不判锚点无效）/ `test_container_stat_error_eloop_reported`（ELOOP 按 errno 依据单列，不冒充 missing） |
| 4 | 字面路径检查失败不得触发截断回退 | `test_full_literal_stat_error_no_truncation_fallback`（EACCES）/ `test_full_literal_boundary_no_truncation_fallback`（越界整串入报；哨兵文件字节不变） |
| 5 | 容器越界不读 | `test_container_symlink_cross_company_boundary_not_read`（跨公司 symlink → boundary-violation、`--full-hash` 也不产生容器哈希、不给解析路径）+ `test_dual_company_same_container_each_own`（双公司同名容器各观察各的） |
| 6 | 非受限片段与描述性声明保持现状 | `test_restricted_syntax_guards_keep_full_path_diagnosis`（空片段/非.jsonl/URL/scheme/片段空白/片段括注/片段分号/左侧分号/左侧括注/控制字符 10 例不拆）+ `test_four_descriptive_shapes_unchanged`（联友四条描述性来源同构：诊断逐字保持）+ `test_none_and_missing_source_unchanged` |
| 7 | 修复诊断不冒充已解析来源 | `test_repair_mode_fragment_diagnostics`（可访问/缺失/越界/stat失败 → fragment-not-verified / container-missing / boundary-violation / container-check-failed；不落 resolvable-in-base、无"无需修复"、无 reconvert、不进 repair_candidates） |
| 8 | 旧行为与零业务写入保留 | `test_mixed_legacy_and_fragment_in_one_run`（普通本地 match + raw 网页 external-url + none + 缺来源 + 片段同跑，source_nature 语义保持）+ 每个用例 `snapshot_all` 前后全树相等（覆盖基座外哨兵/双公司文件） |

独立原始回归输入 = 真实联友锚点（只读登记 `tests/fixtures_registry.json`
`lianyou-cert-fragment-source`：材料 SHA `eecc55a5…772689f`、容器当前观察哈希
`b4fe38de…a70c687`）；核心测试全部合成基座，不依赖真实公司文件。

## 3. 实际命令与退出码（任务 3.1/3.2，不沿用历史数字）

| 命令（cwd） | 退出码 | 结果 |
|---|---|---|
| `uv run pytest tests/test_provenance_inventory.py -q`（material-importer） | 0 | **91 passed**（72 旧 + 19 新） |
| `uv run pytest tests/ -q`（material-importer） | 0 | **380 passed**（历史 361 已过时） |
| `bash references/scripts/check_skill_ecosystem.sh --ci`（skill 根） | 0 | PASS（P0 0 / P1 0 / P2 0） |
| `bash references/scripts/check_docs_consistency.sh --quiet`（skill 根） | 0 | PASS（38 PASS / 0 FAIL / 0 WARN） |
| `openspec validate inspect-material-source-fragments --strict` | 0 | valid |
| `git diff --check` | 0 | 无空白错误 |

精确改动范围（`git status --porcelain` / `git diff --stat`）：
`skills/business/material-importer/` 下 4 文件 —— `SKILL.md`（+57/−4）、
`scripts/provenance_inventory.py`（+238/−11）、`tests/fixtures_registry.json`（+19）、
`tests/test_provenance_inventory.py`（+504）；与 proposal Impact 声明一致，
无范围外文件。`openspec/changes/`（本 change 目录）为 untracked 规划工件。

## 4. 可选真实联友只读扫描（任务 3.3）

- 旧实现基线报告：`/tmp/opencode/imsf/baseline-lianyou.json`（实施前生成，保留不覆盖）。
- 新报告：`/tmp/opencode/imsf/after-lianyou.json`、`/tmp/opencode/imsf/after-lianyou-full.json`
  （`--repair-candidates --full-hash`）。两次扫描 rc 均为 3。
- **证书诊断迁移**：`materials/02-qualifications/计算机软件著作权登记证书-溯源防控
  系统APP-V3.0.md` 从 `missing_original`（整串当路径误报）→
  `material_source_fragment_findings[kind=anchor-not-verified]` +
  `container_accessibility=accessible` + `hash_check=unknown-scope` +
  `anchor_verification=not-performed`；`--full-hash` 容器观察哈希
  `b4fe38de…a70c687` 与 fixtures_registry 登记一致。
- **其余四条 missing_original 逐字不变**（路径与条目内容字节级相等）；顶层其余节
  （boundary/unverifiable/外部未核验/声明冲突/存档发现等）前后完全一致；items
  计数 26=26。
- repair 侧：证书 → `fragment-not-verified`；四条描述性 → `source-missing` 保持；
  两条可解析材料 → `resolvable-in-base` 保持。
- **零业务写入**：materials + `raw/_index.json` + 全部 `_manifest.json`（16 文件）
  两次扫描（含 full-hash 模式）sha256 逐字节相等
  （`/tmp/opencode/imsf/lianyou-bytes-run{1,2}.txt` diff 为空）。

## 5. 边界与未做

- 未归档、未提交、未推送（另行授权）；未修改任何真实公司资料（联友仅只读扫描，
  报告只写 /tmp）。
- 共享 `resolve_declared_source` / `safe_exists` 原语义未动；raw 分支行为未动。
- 重复 frontmatter source 字段等既有解析边界未扩展（design D3 明示不处理）。

## 6. 复核有界修复（2026-11-14 第二批，先红后绿）

主代理复核发现两处实证缺陷，本轮有界修复（tasks 4.1/4.2），失败历史与
第 1–5 节验收记录原样保留。

### 6.1 问题与修复

1. **materials 完整字面 source 的 RuntimeError 未承接**：materials 分支
   `resolve_declared_source` 调用处（原约 1504 行）只承接 OSError；
   pathlib `Path.resolve` 将 ELOOP 自环包成 `RuntimeError`（Python 3.12
   实证：`RuntimeError: Symlink loop from ...`），自环 symlink 字面路径
   （如 `raw/a.jsonl#image.png` 自环）直接 crash `run_inventory`。
   修复：新增 `resolve_declared_source_guarded`（materials 局部包装，
   stat 探针补 ELOOP errno 证据；`_observe_material_fragment` 原内联
   catch 重构为复用同一包装），完整字面路径 resolve 失败 → 观察失败
   （unverifiable_sources，reason 含 `errno 40 ELOOP`），不回退、不崩溃、
   不冒充缺失，其余条目继续；共享 `resolve_declared_source` 未动。
2. **`--full-hash`+repair 容器字节读取失败假装成功**：原实现 stat 存在 +
   read EACCES 时 `container_accessibility` 仍 accessible、finding
   `anchor-not-verified`、repair `fragment-not-verified`。修复：实际读取
   失败（任意 OSError：EACCES/EIO/…，经 `stat_error_detail` 保留 errno）
   与 stat 存在分开表达——`container_accessibility` 仍记 stat 观察，新增
   `container_hash_check=not-completed`，`hash_check=not-applicable`，
   `container_hash_error` 保留 errno；finding kind 与 repair
   verifiability 一致为 `container-check-failed`；不产生容器哈希
   （container_sha256_observed/container_observed_at 缺席），
   `anchor_verification=not-performed` 不被抹去。

### 6.2 实际命令与退出码（红→绿）

| 命令（cwd=material-importer） | 退出码 | 结果 |
|---|---|---|
| 红跑 `uv run pytest tests/test_provenance_inventory.py -q -k "GuardedResolveFix or read_failure_listed"`（旧实现） | 1 | **3 failed**, 90 deselected（日志 `/tmp/opencode/imsf/red-run-fix2.log` 保留） |
| 绿跑同上（修复后） | 0 | **3 passed**, 90 deselected |
| `uv run pytest tests/test_provenance_inventory.py -q`（修复后全文件） | 0 | **93 passed**（91 旧 + 2 新增 `MaterialFragmentGuardedResolveFixTest`；日志 `/tmp/opencode/imsf/green-run-fix2.log`） |
| `git diff --check`（skill 根） | 0 | 无空白错误 |

新增/调整用例：`MaterialFragmentGuardedResolveFixTest::
test_full_literal_eloop_selfloop_no_crash`（片段形态 + 普通完整路径自环 +
正常材料继续 + snapshot_all 零写入）、`test_full_hash_container_read_
oserror_check_failed`（patch `Path.read_bytes` 注入 EACCES+EIO，全合成
基座零写入）；既有 `test_full_hash_container_read_failure_listed` 按新口径
更新（repair 断言移入 chmod 窗口内）。全文件 93 passed 即本轮守卫通过
（既有 91 用例无一回归）。

### 6.3 本轮改动范围

`skills/business/material-importer/` 3 文件：`scripts/provenance_inventory.py`
（+guarded 包装/2 处调用点/读取失败分支/repair 分支）、
`tests/test_provenance_inventory.py`（+1 测试类 2 用例、1 用例更新）、
`SKILL.md`（v8.3 条目与报告/修复描述一致性 +3 处）；另
`openspec/changes/inspect-material-source-fragments/{tasks.md,verification.md}`
追加修复条目与本节。未动共享 `resolve_declared_source`、raw 分支、fixtures。
全套测试/生态/文档审计由主代理最终统一执行（本轮定向执行，未跑全套）。


## 7. 中断后主代理独立续验（2026-11-14）

- fixer 子任务以额度耗尽错误终止；主代理读回实际改动与§6，不将任务错误当作未留工件，也不将其测试摘要当最终证据。§6红绿命令为子任务留档，本节为中断后独立执行。
- `uv run pytest tests/ -q`（cwd=skills/business/material-importer）退出码0：**382 passed in 16.81s**。
- 追加只读合成probe：完整字面自环返回含ELOOP的结构化观察失败，不回退fragment；容器read EACCES/EIO均为container_hash_check=not-completed、hash_check=not-applicable，无容器哈希，finding与repair均container-check-failed。三组断言通过，命令退出码0。
- `bash references/scripts/check_skill_ecosystem.sh --ci`退出码0（P0=32/P1=20，零失败/警告）；`bash references/scripts/check_docs_consistency.sh --quiet`退出码0（38 PASS，零FAIL/WARN）；`openspec validate inspect-material-source-fragments --strict`退出码0；`git diff --check`退出码0。均cwd=skill根。
- 本轮测试与probe均为合成临时基座，未重新运行真实公司体检；之前真实扫描属于§4的历史证据，不冒充本节重跑。公司资料没有写入。
- 两项复核发现已独立复现修复效果；本轮未归档、提交或推送。


## 8. Archive closeout (2026-11-14)

- 本记录逐字节保留change内verification.md原内容；本节为归档收尾追加，不将历史结果冒充新时点复跑。
- 本轮只同步规格、保存长期记录并归档；最后有效实施验证为§7的382 passed、生态52 PASS、文档一致性38 PASS，未再次运行全套测试。
- 主规格追加1条要求、8个场景，原有9条要求与Purpose保持不变。
- 归档目标：openspec/changes/archive/2026-11-14-inspect-material-source-fragments/。
- 本节写入时归档与规格校验尚待完成，结果后续追加；未提交、未推送、未写公司资料。

### 收尾结果

- 主规格`openspec validate material-import-provenance --type spec --strict`退出码0。
- `openspec validate --specs`退出码0：18 passed / 0 failed；仍有cross-layer-reconciliation和prd-handoff-traceability两项既有>500字符警告，两文件与HEAD字节一致，未改动；不宣称全仓strict全绿。
- 已移动至上述归档路径，.openspec.yaml随目录保留；同步块逐字一致，无剩余delta头或TBD；未跟踪的change工件未造成tracked删除。
- 本轮未提交或推送；实施4文件、主规格及本长期记录仍为未提交状态。


## 9. 授权发布前复验（2026-11-14）

- Owner 在归档收尾后明确授权精确提交与普通推送，范围为实施4文件、主规格及本记录，共6文件。
- `git fetch origin`退出码0；发布前`git rev-list --left-right --count origin/main...HEAD`为`0 / 0`，共同基线为`1fc24ab1b3bf1824d904cde95541b671b446bd8f`；暂存集原为空。
- `uv run pytest tests/ -q`（cwd=skills/business/material-importer）退出码0：**382 passed in 18.62s**。
- `openspec validate material-import-provenance --type spec --strict`退出码0；`openspec list --json`确认active changes为空；`git diff --check`退出码0。
- 本节记录发布前事实；提交与推送结果以会话中的实际SHA、远端查询和同步计数为准，不提前宣称发布成功。此前各节“未提交/未推送”为各自时点记录，原样保留。
