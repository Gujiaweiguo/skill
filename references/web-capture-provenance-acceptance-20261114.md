# 实施与验证记录 — recognize-web-capture-provenance

日期：2026-11-14 ｜ 执行：Orchestrator（apply 流程）｜ 状态：实施完成，未提交/未推送/未归档（Owner 另行授权）

## 1. 实施范围（精确改动）

```
 M skills/business/material-importer/SKILL.md                              (+86/-6 行)
 M skills/business/material-importer/scripts/provenance_inventory.py       (+387)
 M skills/business/material-importer/tests/fixtures_registry.json          (+33)
 M skills/business/material-importer/tests/test_provenance_inventory.py    (+643)
?? openspec/changes/（本 change 目录，untracked，实施前已存在）
```

未改动：backfill_source.py / convert_doc / convert_excel / 索引重建 / 任何 /opt/code/docs 字节 / manifest / 既有报告。
`git diff --check` 干净；无 commit、无 push。

## 2. 规格场景覆盖矩阵

### Requirement: 网页抓取声明 SHALL 与本地来源分开识别

| # | 场景 | 测试 / 证据 |
|---|------|------------|
| 1 | 既有中文抓取头无需改写 | `test_chinese_head_url_and_capture_time`（真实锚点同构头）；真实体检：九篇 external-url、captured_at=2026-11-07 declared、零 missing_source/missing_original、无写回 |
| 2 | 显式source中的网页URL不走文件系统 | `test_old_source_field_http_url_external_branch`、`test_old_block_source_path_with_url`、`test_url_never_resolved_never_network`（resolve 守卫 + socket 哨兵双证） |
| 3 | URL只在声明位置识别 | `test_body_code_block_and_post_comment_urls_ignored`、`test_truncated_or_unclosed_comment_yields_no_source`、`test_malformed_url_declarations_diagnosed`、`test_unsupported_scheme_reported_not_relative_path` |
| 4 | 多项声明并存不被隐藏 | `test_duplicate_urls_grouped_all_positions_kept`、`test_conflicting_urls_reported_no_authority`、`test_mixed_local_and_url_keeps_local_diagnostics`、`test_bad_local_source_with_valid_url_not_masked` |
| 5 | 外部声明仍是未核验发现 | `test_url_only_rc3_scan_complete_external_not_performed`（rc=3 + scan.complete=True + not-performed）、`test_external_declaration_not_backfill_candidate`、`test_external_url_with_signature_hash_not_upgraded`（不升 recorded-at-conversion）、`test_wrong_source_suspects_external_branch` |

### Requirement: 本地网页存档 SHALL 作为独立候选关系观察

| # | 场景 | 测试 / 证据 |
|---|------|------------|
| 6 | 当前存档存在与声明哈希分列 | `test_archive_present_two_timepoint_hashes`（observed_at ≠ declared_observed_at；match-observed 不升级分级） |
| 7 | 存档缺失或读取失败与网页来源区分 | `test_archive_missing_keeps_external_unverified`、`test_archive_read_failure_reported`（errno 分类） |
| 8 | 存档越界不读取 | `test_archive_boundary_not_read`（绝对/`..`相对/符号链接三种；无 sha256_observed = 未读内容） |
| 9 | 无存档声明不推断匹配 | `test_no_same_name_html_inference`；真实体检：同名 html/ 存在但 findings=[]、无 local_archive_observations |
| 10 | 旧本地来源行为与业务字节保留 | 23 个既有用例全绿（本地分级/隔离/退出码语义原样）；每个新用例附 snapshot 前后相等断言；`test_cross_company_same_archive_path_not_reused` |
| 11 | 存档多声明与孤立哈希不任意绑定 | `test_archive_multi_declaration_conflict_unbound_hash`（archive-conflict + unresolved-hash-binding，哈希不挂接任何一条） |

## 3. 命令与退出码（2026-11-14 实测，非沿用历史结果）

| 命令（cwd=skills/business/material-importer） | 结果 | exit |
|---|---|---|
| `uv run pytest tests/test_provenance_inventory.py -q` | 54 passed（既有 23 + 新增 31） | 0 |
| `uv run pytest tests/ -q` | **343 passed**（上一批 312 之后全量重跑） | 0 |
| `bash references/scripts/check_skill_ecosystem.sh --ci`（cwd=skill 根） | PASS（P0=32 P1=20，failures 0） | 0 |
| `bash references/scripts/check_docs_consistency.sh --quiet`（cwd=skill 根） | PASS（38，WARN 0） | 0 |
| `openspec validate recognize-web-capture-provenance --strict` | valid | 0 |
| `git diff --check`（cwd=skill 根） | 干净 | 0 |

既有失败：无（全部检查一次全绿，无新增失败）。TDD 红阶段证据：任务 1.1 批次 12 failed/23 passed（原版把 URL 当本地路径 → missing_original 误分类），任务 2.1 批次 wrong_source_suspects 误记 resolvable-in-base（KeyError source_kind），任务 3.1 批次 9 failed（无存档观察）。

## 4. 零业务写入证据

- 每个新用例断言 `{relpath: sha256}` 快照前后完全相等（含 --repair-candidates / --report 模式）。
- CLI --report 均写基座外（tmpdir / /tmp/opencode）。
- 真实基座体检：18/18 文件（9 md + 9 html）sha256 前后一致（before/after 对照文件：/tmp/opencode/recognize-web-capture-provenance/*.sha256）。
- /opt/code/docs `git status` 中 gdcreia/30-products/ 的 M 条目为**其他会话遗留**（PRD 工作区，实施前已存在），与本 change 无关且不在任何扫描写入路径内（本工具零写入，测试钉死）。

## 5. 真实协会只读体检（附加证据，/opt/code/docs 仅作只读输入）

- 前置：fixtures_registry.json 登记 18 文件哈希，运行前复核 18/18 一致。
- 命令：`uv run scripts/provenance_inventory.py --base /opt/code/docs/gdcreia --report /tmp/opencode/recognize-web-capture-provenance/gdcreia-inventory.json` → rc=3（未核验外部声明计入发现，符合规格）。
- 结果：九篇 md 全部 `source_kind=external-url`、`captured_at=2026-11-07 (declared)`；不再出现 missing_source/missing_original；同名 html/ 未被自动认作存档（local_archive_findings=[]）；`external_verification=not-performed`、`scan.complete=true`；结束后 18/18 字节不变；未运行任何历史补丁、未覆盖旧报告。

## 6. 遗留与边界

- 旧报告（/tmp 下历史体检 JSON）未重写；本 change 不含 materials frontmatter URL 处理、fragment/复合来源解析（设计 Non-Goals，留独立范围）。
- 归档/提交/推送：Owner 另行授权（Workflow follow-up 约定）。

## 7. 独立复核修复验收（第二批，2026-11-14）

状态：实施完成，未提交/未推送/未归档（Owner 另行授权）。前六节为第一批记录，原样保留（含失败历史）。

### 7.1 独立复核五类发现与修复对应

复核证据：独立探针 `/tmp/opencode/probe_rv/`（company1 四文件 + report.json）、
复核扩展探针 `/tmp/opencode/probe_rv2/`。原五类清单文本不可复得（会话未落盘），
以下按探针证据 + 规格逐条重建，每条钉住 spec 场景：

| # | 类别 | 修复前行为（复核实证） | 修复后 | 规格依据 |
|---|------|----------------------|--------|----------|
| C1 | 游离存档哈希零路径静默 | probe_rv/03.md：URL+合法游离哈希 → 零发现、observations 键缺失；非法格式（probe_rv2/h6）同样零发现 | `unresolved-hash-binding`（declared_paths=[]）与 `invalid-hash` 覆盖零路径；`local_archive_observations` 键一致存在 | 场景11「游离哈希…报告未解决绑定」 |
| C2 | 多值哈希冲突首条静默绑定 | probe_rv/04.md：两条不同 sha256_observed → 首条静默为比对基准（match 可掩盖冲突零发现） | `declared-hash-conflict`（逐值分列）；hash_check=`unresolved-declared-hash`，不按首条判 match/mismatch | 场景4/11「不将一个哈希静默应用」 |
| C3 | 多值观察时间/抓取时间冲突静默 | probe_rv2/h3/h4：首条静默采用，无冲突发现 | `observed-at-conflict`；多条抓取时间 → `source_declaration_conflicts`(kind=captured-at)，外部条目不带单一权威时间 | 场景4「多项声明并存不被隐藏」 |
| C4 | local_archive 值非法形态被当路径解析 | probe_rv2/h5：URL 形态 → in-base 假 missing；h7：空值 → 解析成基座目录 EISDIR 假 read-error | `invalid-archive-declaration`（issue=empty-value/url-shaped），不 resolve/stat/读字节，不猜路径 | 场景3 原则「不猜测文件路径」 |
| C5 | SKILL.md 文档漂移 | 文档承诺 unresolved-hash-binding 但零路径不触发；缺多值冲突/值形态规则 | SKILL.md v8.1 条目 + hash_check 枚举 + 发现清单 + 多声明段 + 值形态规则对齐 | 任务 1.3/2.3/3.3 文档一致纪律 |

### 7.2 TDD 证据（先失败后修复）

- 新增回归类 `IndependentReviewFixRegressionTest`（9 用例，每例含零写入快照断言）。
- 红阶段（修复前实测）：`uv run pytest tests/test_provenance_inventory.py -q -k IndependentReviewFixRegression`
  → **9 failed**, 54 deselected（pytest rc=1；每例断言即 7.1 修复前行为）。
- 绿阶段：同命令 → 9 passed；全文件 `uv run pytest tests/test_provenance_inventory.py -q` → **63 passed**（54 既有 + 9 新增，既有用例零回归）。
- 实现中缺陷自纠：首批绿跑暴露 `distinct_hashes` 空列表 IndexError（7 failed）→ 当日修正为空列表守卫后全绿（失败不隐藏，如实记录）。

### 7.3 命令与退出码（2026-11-14 实测）

| 命令 | 结果 | exit |
|---|---|---|
| `uv run pytest tests/test_provenance_inventory.py -q`（cwd=material-importer） | 63 passed | 0 |
| `uv run pytest tests/ -q`（cwd=material-importer） | **352 passed**（第一批 343 + 新增 9） | 0 |
| `bash references/scripts/check_skill_ecosystem.sh --ci`（cwd=skill 根） | PASS（P0=32 P1=20，failures 0） | 0 |
| `bash references/scripts/check_docs_consistency.sh --quiet`（cwd=skill 根） | PASS | 0 |
| `openspec validate recognize-web-capture-provenance --strict` | valid（无 delta 变更：修复使实现符合既有场景 3/4/11） | 0 |
| `git diff --check`（cwd=skill 根） | 干净 | 0 |

### 7.4 真实基座只读回归（/opt/code/docs 仅作只读输入）

- gdcreia：运行前后 18/18 文件（9 md + 9 html）sha256 完全一致
  （对照文件 `/tmp/opencode/recognize-web-capture-provenance/fix2-{before,after}.sha256`）；
  `--report` 写基座外；rc=3（既有发现）。报告画像与第一批产出逐项相同
  （items 454 / external 9 / 各发现节 0 / gaps missing_source 1），九篇 external-url、
  captured_at=2026-11-07 (declared) 不变——修复在真实锚点上零新增误报。
- lianyou：只读运行 rc=3；items 26、gaps（missing_source 1 + missing_original 5）与
  复核轮一致；新发现节全零（该基座无 local_archive/多值声明）。
- 复核探针复跑：probe_rv 四文件与 probe_rv2 八文件修复后输出均符合 7.1 预期
  （报告 `/tmp/opencode/probe_rv*/report-fixed.json`）。

### 7.5 本批改动范围与边界

```
 M skills/business/material-importer/SKILL.md                              （v8.1 条目 + 三段对齐）
 M skills/business/material-importer/scripts/provenance_inventory.py       （D3 重构 + captured-at 冲突，只做加法发现）
 M skills/business/material-importer/tests/test_provenance_inventory.py    （+9 回归用例）
 ?? openspec/changes/recognize-web-capture-provenance/（untracked；本批追加 tasks.md §5 与本文件 §7）
```

（fixtures_registry.json 的 M 为第一批既有改动，本批未触碰。）

未改：规格 delta（无变更）、fixtures_registry.json、backfill/转换器/索引、
任何 /opt/code/docs 字节、既有报告。未 commit、未 push、未归档。

## 8. 复核遗漏补充验收（第三批，2026-11-14）

状态：实施完成，未提交/未推送/未归档（Owner 另行授权）。前七节为第一/二批记录，
原样保留（含失败历史）。

### 8.1 上一轮修复清单遗漏（本轮补充范围）

第二批五类发现（C1-C5）未覆盖以下两类输入形态，独立探针
`/tmp/opencode/probe_rv3/probe.py` 对修复前（第二批后）实现复现：

| # | 类别 | 修复前行为（探针实证，第二批实现） | 修复后 | 规格依据 |
|---|------|----------------------------------|--------|----------|
| G1 | 文首两条旧 source/source_path 一 URL 一本地路径（两种顺序） | `parse_raw_md_provenance` 只取先出现的一条，另一条整条静默丢弃：URL 在前 → 本地路径不解析、缺失零报告（source_kind=external-url）；本地在前 → URL 不进外部未核验清单（source_kind=local） | 双方都保留：URL（限文首区）进声明表与 external_sources_unverified，本地取先出现非 URL 命中照常解析，source_kind=mixed，本地缺失照常进 missing_original | 场景4「多项声明并存不被隐藏…不以有效URL掩盖本地来源缺失」 |
| G2 | 正文/围栏代码块/后置注释中的旧 source/source_path URL | INLINE/BLOCK 正则对 4000 字符头全文检索，正文命中被当外部声明：三例全部 source_kind=external-url 且进外部未核验清单 | 非文首区 URL 形态命中不是有效网页来源：不进外部清单、不进本地解析、也不当缺失文件（无 missing_source 之外的假缺口，URL-only 时如实 missing_source）；修复未收紧本地路径既有全头检索兼容（正文本地 source 命中仍有效，两条守卫用例钉死） | 场景3「URL只在声明位置识别」 |

### 8.2 TDD 证据（先失败后修复）

- 新增回归类 `ReviewGapFixRegressionTest`（9 用例：G1×3 + G2×4 + 兼容守卫×2，
  每例含零写入快照断言）。
- 红阶段（修复前实测，第二批实现）：`uv run pytest tests/test_provenance_inventory.py
  -q -k ReviewGapFixRegression` → **7 failed, 2 passed**（pytest rc=1；7 个失败即
  8.1 两类缺陷，2 个通过为"本地路径兼容不收紧"守卫——修复前后都必须绿，属约束钉
  而非缺陷回归）。
- 绿阶段：同命令 → 9 passed；全文件 `uv run pytest tests/test_provenance_inventory.py
  -q` → **72 passed**（第二批 63 + 新增 9，既有用例零回归）。
- 探针复跑：probe_rv3 五文件（m1/m2 双顺序 + b1/b2/b3 三种非法位置）修复后输出
  均符合 8.1 预期（`/tmp/opencode/probe_rv3/probe-fixed.txt`）。

### 8.3 实现要点（只做加法，不收紧既有规则）

- `parse_raw_md_provenance` 新增加法键 `source_hits`（全部命中含原位置，去重口径
  不变）；`source`/`declared_via`/`source_pos`（先出现者）语义不变。
- 新增 `head_comment_region_end()`（与 `iter_head_comment_blocks` 同口径：文首空白
  后连续已闭合注释区）。
- 主循环分流：文首区 URL 命中 → 声明表（field/via 原值）+ 外部清单；非文首区 URL
  命中 → 忽略（不是有效网页来源）；本地命中（不限位置，兼容不变）→ 取先出现者
  照常 resolve/stat/hash，诊断（missing_original/boundary/unverifiable）照常输出。
- `declared_via`/`declared_source` 改为按有效命中在分流处回填（非文首区 URL 命中
  不再从 prov 顶层带入悬空值）；外部分支声明取首个文首 URL 命中。

### 8.4 命令与退出码（2026-11-14 实测）

| 命令 | 结果 | exit |
|---|---|---|
| `uv run pytest tests/test_provenance_inventory.py -q`（cwd=material-importer） | 72 passed | 0 |
| `uv run pytest tests/ -q`（cwd=material-importer） | **361 passed**（第二批 352 + 新增 9） | 0 |
| `bash references/scripts/check_skill_ecosystem.sh --ci`（cwd=skill 根） | PASS | 0 |
| `bash references/scripts/check_docs_consistency.sh --quiet`（cwd=skill 根） | PASS | 0 |
| `openspec validate recognize-web-capture-provenance --strict` | valid（无 delta 变更：修复使实现符合既有场景 3/4） | 0 |
| `git diff --check`（cwd=skill 根） | 干净 | 0 |

### 8.5 真实基座只读回归（/opt/code/docs 仅作只读输入）

- gdcreia：运行前 fixtures_registry 18/18 锚点哈希一致；`--report` 写基座外
  （fix3-gdcreia-inventory.json）rc=3（既有发现）；报告与第一批产出**逐项相同**
  （仅时间戳差异：items 454 / external 9 / 各发现节 0 / gaps missing_source 1，
  九篇 external-url、captured_at=2026-11-07 declared 不变）；运行前后 115 个
  md/html 文件 sha256 完全一致（fix3-{before,after}.sha256）。
- lianyou：只读运行 rc=3；报告与复核轮**逐项相同**（items 26、gaps missing_source 1
  + missing_original 5）。
- 本轮修复在两个真实基座上零新增误报、零字节写入。

### 8.6 本批改动范围与边界

```
 M skills/business/material-importer/SKILL.md                              （v8.2 条目 + URL 规则/多声明两段）
 M skills/business/material-importer/scripts/provenance_inventory.py       （source_hits + head_comment_region_end + 主循环分流）
 M skills/business/material-importer/tests/test_provenance_inventory.py    （+9 回归用例）
 ?? openspec/changes/recognize-web-capture-provenance/（untracked；本批追加 tasks.md §6 与本文件 §8）
```

（fixtures_registry.json 的 M 为第一批既有改动，本批未触碰。）

未改：规格 delta（无变更——修复使实现符合既有场景 3/4，未新增 Requirement）、
fixtures_registry.json、backfill/转换器/索引、任何 /opt/code/docs 字节、既有报告
（/tmp 下历史体检 JSON 未重写）。未 commit、未 push、未归档。

## 9. 收尾前复核（2026-11-14 归档/提交前最终时点重跑）

工作区与 §8.6 范围完全一致（material-importer 4 文件 M + 本 change 目录，无其他会话改动混入），全套检查重跑实测：

| 命令 | 结果 | exit |
|---|---|---|
| `uv run pytest tests/test_provenance_inventory.py -q`（cwd=material-importer） | 72 passed | 0 |
| `uv run pytest tests/ -q`（cwd=material-importer） | 361 passed | 0 |
| `bash references/scripts/check_skill_ecosystem.sh --ci`（cwd=skill 根） | PASS（P0=32 P1=20，failures 0） | 0 |
| `bash references/scripts/check_docs_consistency.sh --quiet`（cwd=skill 根） | PASS（38） | 0 |
| `openspec validate recognize-web-capture-provenance --strict` | valid | 0 |
| `git diff --check`（cwd=skill 根） | 干净 | 0 |

主规格 `openspec/specs/material-import-provenance/spec.md` 现存 7 个 Requirement，与本 change 两个 ADDED Requirement（网页抓取声明分开识别 / 本地网页存档独立观察）无同名冲突，归档同步为纯追加，不触碰既有 7 条。本节为收尾前时点证据；实施/归档提交 SHA 与推送状态见文末「最终收尾状态」。

## 记录元信息

- 规划基线：`476dd34020487ef83312132f0d24403168ebce6b`（apply 启动时 HEAD；上方 §1-§8 全部工作落在其工作区之上，三批 TDD 失败历史原样保留，未删改任何失败记录）。
- 实施方式：第一批任务 1-4（规划→apply）+ 第二批独立复核修复（tasks §5 / §7，C1-C5 五类）+ 第三批复核遗漏补充（tasks §6 / §8，G1/G2 两类）。
- 零业务写入边界：/opt/code/docs 全程只读输入（多轮 18/18、115 文件 sha256 前后对照全等）；CLI 报告全部写基座外（tmpdir / /tmp/opencode）；未运行历史补丁、未重写既有报告、未改 fixtures 之外任何公司资料。
- 本件为 git tracked 长期验收记录（`openspec/changes/archive/` 为 gitignored 本地历史，change 目录内 verification.md 随归档移入）；「最终收尾状态」在归档提交后另行追加。
