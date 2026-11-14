# 实施与验证记录 — harden-material-import-provenance

- 记录时间：2026-11-14（apply 轮）
- 规划基线：`386eb52b47dd7a398317fd212a41bfc30e4fa49e`（apply 启动时 HEAD 与基线一致，本轮未前进）
- 实施方式：orchestrator 统一契约 + 三条并行实施 lane（A=provenance_inventory、B=转换指纹/守卫、C=backfill 语义）+ E2E lane + 三次对 A/B 的同会话修订（amend，不重开）；文档（4.1/4.3/4.4）与验收记录由 orchestrator 本人编写。
- 授权边界遵守：**未写任何真实公司资料（/opt/code/docs 下零业务写入，证据见 §5.6）；未执行任何历史回填/删除/清理/批量重转；未 commit / archive / push。**

## 1. 已完成任务与对应实现（30/30）

| 任务 | 实现 | 落点 |
|---|---|---|
| 1.1–1.4 | `provenance_inventory.py`（新建，纯 stdlib）：四类 link_state + 三维分维字段 + 退出码 0/1/2/3 + boundary-violation 单列 + `--repair-candidates` 三级候选 | scripts/provenance_inventory.py |
| 1.5 | 23 用例：中文/空格/方括号、无权限目录、损坏 manifest、歧义候选、`~$` 投影、前后快照零写入、退出码矩阵、D7 兼容读取 | tests/test_provenance_inventory.py |
| 1.6 | 双合成公司基座四场景（Python+CLI 双层） | tests/test_company_isolation.py |
| 2.1 | manifest record 扩展 `options`/`outputs[{path,sha256,bytes}]`/`backend`/`fingerprint_format:1`；旧字段/旧记录不动 | convert_excel.py |
| 2.2 | MD 内联 `output_body_sha256` + `output_digest_scope: post-provenance-header`；以 scope 标记行为头的确定性边界（markitdown 正文自身以注释行开头，按"连续注释段尾"会漂移——语义仍是"排除文首溯源头的正文范围"，实现层修正） | convert_doc.py |
| 2.3 | `_validate_manifest_records`/`_load_manifest` D8 三分类预写检查；半成功显式报错；批量汇总失败非零收尾 | convert_excel.py |
| 2.4 | `--check`/`--skip-up-to-date`/`--force-overwrite-modified`，矩阵由 `_fingerprint.py` 单点实现 | convert_doc.py / convert_excel.py / _fingerprint.py |
| 2.5 | `fingerprint_format` 与 `EXTRACTOR_VERSION` 分离；**两者均未 bump**（excel=3 / doc=2）：本改造不改产物正文内容语义（excel manifest 新字段、doc 头块新行均属指纹元数据域），金样例断言原样通过 → fixtures_registry.json 未改 | _fingerprint.py + 证据（§3） |
| 2.6 | orphan-outputs 双口径：`manifest-recorded`（record−expected）+ `disk-untracked`（磁盘 stem 家族−expected−本目录任何 record 的登记），重转后仍可盘点；永不删除 | convert_excel.py |
| 2.7/2.8 | 44+ 用例：验收场景 + 六态×三模式逐格（18 格命名用例 + 三态不折叠钉死）+ `--check` 字节快照零写入 | tests/test_conversion_fingerprint.py |
| 3.1 | 输入侧 `~$` 前缀守卫：convert_doc 单文件 exit 3（魔数检查前、不调 markitdown）；convert_excel 批量枚举先列 skipped；extract_images 单文件补守卫 exit 3 | 三个脚本 |
| 3.2/3.3 | 投影侧中部 `~$` → garbage-candidate 候选清单；NUL 抽样 sampled_bytes/sample_nul_count/nul_scope 显式口径；UTF-8 严格探测 encoding-invalid；短/空白文档不判垃圾 | provenance_inventory.py |
| 3.4 | 魔数守卫回归用例（非 PK .docx / 非 %PDF- .pdf → rc=1 不变） | test_convert_doc.py |
| 3.5 | 三测试文件补锁文件用例（合成 BadZipFile 字节形态）；批量遇锁其余全部产出；manifest 预写失败后已有输出字节不变 | test_convert_{doc,excel}.py / test_extract_images.py |
| 4.1 | `references/provenance-evidence-boundary.md`（唯一权威源）：三态/旧代际≠none/页级锚点/OCR=检索线索/fresh-clone 三项/图片缺失≠证据不存在/二进制归属不变/evidence_state 逐项映射表 | references/（orchestrator 亲写） |
| 4.2 | backfill 三新字段持久化（provenance_class + source_sha256_at_backfill + backfilled_at，新写不再用裸 source_sha256）；`classify_record` 兼容读取；wrong_source_suspects 仅建议 | backfill_source.py + test_backfill_source.py |
| 4.3 | SKILL.md：溯源生命周期专节（体检/矩阵/指纹/锁文件/多公司）+ change log v7 + 已知限制（R2、exit 3）+ 设计决策 6 条 + 维护规则 2 条；troubleshooting #16（manifest 预写检查）/#17（锁文件两侧） | SKILL.md / troubleshooting.md（orchestrator 亲写） |
| 4.4 | competitor-product-analyzer SKILL.md 边界规则改引用共享 reference（保留回看操作细节）；AGENTS.md Shared files 表 + check_docs_consistency.sh SHARED_FILES 同步登记 | 三处（orchestrator 亲写） |
| 4.5 | 人工协议逐条核对：见 §6 | — |
| 5.1–5.3 | `test_e2e_synthetic.py`（14 用例，全 subprocess CLI 级）：微型基座生命周期/双公司隔离 CLI/向后兼容 | tests/test_e2e_synthetic.py |
| 5.4 | **N/A**：本轮全部测试用临时目录合成样例，未引入新的驱动性外部金样例，fixtures_registry.json 无需登记 | — |
| 5.5 | 见 §3 | — |
| 5.6 | 见 §5 | — |

## 2. 多公司隔离验证（任务 1.6 + 5.2）

- 单元+CLI 双层：`tests/test_company_isolation.py`（4 用例）+ `tests/test_e2e_synthetic.py::DualCompanyIsolationE2ETest`（4 用例，全 subprocess）。
- 四场景证据：①同名原件不跨公司匹配（A unresolved + 报告 JSON 全文不含 B 基座路径子串）②相同相对路径产物/指纹不复用（A source-changed / B up-to-date 互不污染）③unset/无效 COMPANY_BASE → rc=1 + resolver 报错 + 无 `/opt/code/docs/lanlnk` 回退 ④symlink 跨基座声明 → boundary-violation + hash_check=not-applicable + B 文件字节不进报告（声明故意错误哈希仍 not-applicable = 未读目标的证明）。
- resolver 未改（`_company_base.py` 零改动），无硬编码公司清单。

## 3. 最终验证命令与结果（orchestrator 亲自复跑）

| 命令（cwd=skills/business/material-importer） | 退出码 | 结果 |
|---|---|---|
| `uv run pytest tests/ -q` | 0 | **277 passed / 0 failed / 0 skipped**（16.08s） |
| `bash references/scripts/check_skill_ecosystem.sh --quiet`（cwd=repo 根） | 0 | PASS（P0 32 / P1 20 / P2 0） |
| `bash references/scripts/check_docs_consistency.sh --quiet`（cwd=repo 根） | **1** | 37 PASS + **1 FAIL**：`provenance-evidence-boundary.md 存在但未被 git track`（Check 5）。**成因**：本 change 新增共享文件，本轮无 commit 授权故未入 git 索引；commit 时（git add 后）自动消解，pre-commit hook 届时按 staged 视角校验可通过。非治理回归 |
| `openspec validate harden-material-import-provenance --strict`（cwd=repo 根） | 0 | valid（见 §7） |

分文件计数：test_provenance_inventory 23 / test_company_isolation 4 / test_e2e_synthetic 14 / test_conversion_fingerprint 44+ / test_backfill_source 28 / test_convert_excel / test_convert_doc / test_extract_images / 金样例 6（外部金样例本机在位且 sha 匹配，真实执行未 skip）。

unknown 保留 / 人工修改保护 / manifest 失败保护（矩阵关键格）证据：
- unknown+已有输出：默认=覆盖（现状）、`--check`=报告零写入（字节快照）、`--skip-up-to-date`=保留旧输出+报告需显式重转；首转/output-missing 不被拦截（`test_cell_skip_unknown_with_output_kept` / `test_cell_skip_unknown_no_output_first_conversion`）。
- output-modified/conflict：全模式不覆盖（默认模式 MARKER-EDIT 保留断言在 e2e 生命周期用例）；`--force-overwrite-modified` 唯一例外且打印清单。
- manifest 预写：不可解析/结构非法/冲突 → 已有输出字节快照不变 + rc=1（6 用例）；半成功（mock OSError）显式报错。

## 4. 兼容性变化与残余风险

兼容性（旧产物零迁移）：旧 manifest（无新字段）→ unknown 零写入；旧 convert_doc v2 头 → unknown；旧 `_index.json` → imported_from 照常作 inferred 读取；既有调用行为不变（新语义全部 opt-in 旗标 + 仅对实施后新转换产物生效）。EXTRACTOR_VERSION 与 fixtures_registry 均未动。

残余风险/限制：
1. **R2（设计明示）**：convert_doc 内联指纹不保护头块自身；头块被手工改写不可内联检出。
2. **orphan 误报护栏边界**：disk-untracked 按"不在本目录任何 record 登记"排除他源产物；同 stem 异扩展名（t.xlsx/t.xls）共存且其一无 record 时理论上仍可能漏报（保守方向，不误删）。
3. **manifest 写失败的真实 OSError** 未做文件系统级注入（root 环境 chmod 不可靠），以 mock 验证半成功报错路径。
4. **.xls 路由检查**依赖 soffice；不可得 → backend-unavailable（不整体失败）。本机 soffice 在位但无 .xls fixture，该分支未专项覆盖。
5. convert_excel MD 头（source_path:/extractor:）与 convert_doc 头（source:/extracted_by:）两种 provenance 形态体检均已识别（真实跑验证）；若未来出现第三种写入方形态需扩 `parse_raw_md_provenance`。

## 5. 真实基座只读体检（任务 5.6）

- **命令**（唯一写入=报告文件，落在 change 目录）：
  `cd skills/business/material-importer && uv run python scripts/provenance_inventory.py --base /opt/code/docs/lanlnk --report openspec/changes/harden-material-import-provenance/inventory-lanlnk-20261114.json`
- **报告**：`openspec/changes/harden-material-import-provenance/inventory-lanlnk-20261114.json`（31MB，items 按路径稳定排序，可重复 diff）。
- **执行历史（如实）**：三次尝试——①首跑 rc=1 工具失败（真实基座存在 >255 字节文件名声明来源，`Path.exists()` Errno 36 崩溃；已修复+回归用例）；②二跑 rc=3 但 raw 收集兜底分支误收 `_media`/散落二进制（21193 条 encoding-invalid 假阳性；已修复+回归用例）；③**终跑（上表证据）rc=3 完成且有发现**。三次均为只读，前两次报告被终跑覆盖。
- **零业务写入核验方式**：运行前后 `/opt/code/docs/lanlnk` `git status --porcelain` 完全一致（75 条均为本轮之前已存在的脏条目，逐字节 diff 为空）+ `raw/_index.json` sha256 前后一致 + 无任何 `_manifest.json`/raw 文件 mtime 变化（find -newer 核查为空）。
- **终跑发现摘要**（详细逐条在报告 JSON）：items 9489；scan complete=True；`_media` 如实标注 out-of-scope（范围外≠无问题）；gaps：missing_original 649 / missing_source 152 / no_manifest_coverage 769（=686 CSV+83 notes 边车，与规划期证据精确吻合）；garbage_candidates 1（=已知中部 `~$` 锁文件投影，455B）；unverifiable_sources 1（Errno 36 超长描述性"来源"声明）；boundary_violations 0；hash_mismatches 0；invalid_projections 0；provenance_class：recorded-at-conversion 165 + candidate-association(backfill) 390（≈557 带 source_sha256 的 raw md 规划期计数，自洽）。
- **限制**：默认抽样口径（前 64KiB）与默认哈希策略（仅有声明哈希对象）；未跑 `--full-hash`/`--repair-candidates`（不在 5.6 授权表述内，属 OQ-1 后续批次输入）；**蓝联≠全部公司**——本结果仅为 lanlnk 基座体检，不概括其他公司基座状态。历史回填/删除/重转仍属后续 Owner 授权批次（OQ-1/OQ-3）。

## 6. 人工协议检查（任务 4.5，纯协议条目）

由实施方 orchestrator 在 reference 文本层面逐条核对（Owner 复核待 review）：
1. 检测三态（发现/none/undetermined）语义完整，失败永不渲染 none ✓（reference §1）
2. 旧代际未检测 ≠ none，不触发回填/重转 ✓（§2）
3. 页级锚点 = source_sha256 + slide N，弱锚点须标注 ✓（§3）
4. OCR 仅检索线索，未经原页核验不升级业务结论、同源不重复计数 ✓（§4）
5. 图片缺失 ≠ 证据不存在；fresh-clone 三项（语义转录/源页锚点/恢复定位）逐项可核验在/缺、不合并布尔、恢复定位≠业务语义 ✓（§5）
6. 装饰图/动画承载页/未回看页如实表达（not_scanned/图形态缺失），不判"无信息" ✓（§6）
7. 二进制归属不变 ✓（§7）
8. evidence_state 映射逐项附语义依据；语义不满足者（mismatch/歧义候选/unknown/garbage-candidate）保留原生字段不强行映射 ✓（§8，与 D10 一致）
9. 边界规则单点维护、消费方引用不复制 ✓（§9 + competitor-product-analyzer SKILL.md 两处引用）

## 7. 未解决问题与未独立验证项

- **check_docs_consistency.sh rc=1（唯一未绿项）**：新共享文件未 git track——本轮无 commit 授权的必然结果，commit 时自动消解（见 §3）。
- E2E lane 曾报告两项观察：①convert_excel MD 头与体检解析不互通（已修复，真实跑无 missing_source 假阳性）；②orphan 为 manifest 相对口径（已按任务 2.6 语义修复为双口径含 disk-untracked）。
- soffice/.xls 分支、真实 OSError 注入：见 §4 残余风险 3/4。
- `--report` 路径写入模式无独立单测（默认 stdout 路径已充分覆盖；真实跑即为 --report 模式的成功实证）。

## 8. 停止位置

实施与验证完成，**已停在下述动作之前：commit / archive / push**（均未执行，待 Owner）。工作区改动清单见 git status（12 个修改 + 8 个新文件 + change 目录工件：tasks.md 勾选、inventory 报告、本记录）。

---

# Review 修复轮（2026-11-14 apply 后追加）

Owner review 提出 8 项发现，按原 lane 归属修复（同会话修订，无新增写范围；不 commit、不写真实资料、未重复扫描真实基座——全部修复用临时目录合成样例验证）。

## 逐项修复证据

| # | 发现 | 修复 | 测试证据 |
|---|---|---|---|
| 1 | backfill mapping 边界 | `resolve_in_base()` 守卫：materials/raw 两条 mapping 分支在 is_file/read_bytes 前校验（绝对路径/`..`/跨公司 symlink 三形态）；越界 → 新报告清单 `mapping_target_out_of_base` + unmatched，零读取零写入；索引侧越界 symlink 剔除并记 discovery_errors；OSError → resolve-error 观察失败（与越界分开） | `MappingBoundaryTest` 4 用例（含 symlink 指向第二合成基座、目标机密标记串不出现在报告） |
| 2 | 坏编码与逐项失败 | `read_strict()`：写回只允许严格解码文本，**移除 raw 分支 errors="replace" 产物落盘的破坏路径**；逐文件 try/except（encoding-invalid/read-error/process）→ `failed` 清单 + 继续汇总；written/failed 分开计数，单文件失败不吞此前结果 | `EncodingFailureTest` 2 用例（坏字节原文件快照不变、其余照常 written==2；权限失败 skipIf root） |
| 3 | frontmatter EOF | FM_RE 接受闭合 `---` 位于 EOF 无尾换行；追加改为 close 前纯字符串插入（跟随原块换行风格，读写走 bytes 防 CRLF 规范化），废弃整块 FM_RE.sub 重排；不再产生第二块 | `FrontmatterEOFTest` 5 用例（EOF 块内追加字节级断言、CRLF 保留、CLI 级单块） |
| 4 | 来源观察异常分类 | 分类矩阵成文（docstring）：boundary=resolve 成功落基座外 / unresolvable·permission-denied·inaccessible=观察动作自身失败带 errno / missing=观察成功且不存在，三者互斥；`stat_error_detail`/`accessibility_for_error`（EACCES/EPERM→permission-denied，其余→inaccessible）；`sha_of` 读失败 not-applicable+errno 绝不冒充 mismatch/missing；全库裸调用扫描补齐 | EACCES 文件/目录 2 用例（skipIf root，本机非 root 实跑）+ 三分类互斥断言 1 用例；超长名用例对齐新矩阵 |
| 5 | unknown 已有输出保护 | `_observed_for()`：has_existing_output = record outputs/artifacts 命中 ∪ `_disk_stem_family` 磁盘保守候选；「record 存在但 outputs/artifacts 缺失或为空 + 磁盘有旧产物」→ --skip-up-to-date 保留+需显式重转；无盘 → 首转补齐；默认模式不变 | `UnknownExistingOutputGuardTest` 4 用例（skip 保留字节/检查零写入/默认覆盖/无盘首转） |
| 6 | 多输出叠加诊断 | `evaluate_detail()` → {state, missing_paths, modified_paths}（evaluate 兼容包装）；Decision/check_file 携带双侧清单；modified 非空（含 conflict）任何模式不转换补缺失，note 提示需显式重转；缺失信息不再被主状态吞掉 | `DecisionDiagnosticsTest` 5 + `ModifiedPlusMissingProtectionTest` 3（check 双侧+零写入/默认不覆盖不补齐/skip 同保护） |
| 7 | 多输出部分写入失败 | `ConversionFailure` 结构化报告：{source, stage: write\|hash\|manifest, error, written_paths, possibly_affected=全部预期输出（首写即败也不凭成功计数宣称零影响）, manifest_updated, recovery}；半成品不删不回滚、不宣称回滚；批量继续+汇总+rc=1 | `StagedWriteFailureTest` 3（第二输出失败全字段/首写失败全列/批量继续）；manifest 失败 mock 用例收紧为 ConversionFailure 字段断言 |
| 8 | 参数组合拒绝 | `--skip-up-to-date` + `--force-overwrite-modified` → 两 CLI 一致 rc=2 + 同文案提示（用默认转换模式加 force）；`decide_action` skip+force → ValueError 防御；help 同步；--check 零写入不变 | `FlagCombinationTest` 4（两 CLI subprocess rc=2+文案、单旗标回归）+ decide_action ValueError 单测 + convert_doc 2 用例 |

主动统一（Fix B 偏差申报）：convert_excel 的 `--check + 单旗标` 互斥退出码 1→2（用法错误类），无既有测试依赖，已补用例钉死。

## 修复后最终验证（orchestrator 亲自复跑）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `uv run pytest tests/`（cwd=material-importer） | 0 | **312 passed / 0 failed / 0 skipped**（19.18s；历史时点：apply 轮 277 passed 保留于上表 §3，本轮 +35） |
| `check_skill_ecosystem.sh --quiet` | 0 | PASS（P0/P1 全绿） |
| `check_docs_consistency.sh --quiet` | 1 | 仍为**同一且唯一** FAIL：新共享文件未 git track（无 commit 授权的必然结果，如实保留；commit 时自动消解；未改检查器、未暂存） |
| `openspec validate harden-material-import-provenance --strict` | 0 | valid |

分文件：test_backfill_source 39（28+11）/ test_provenance_inventory 23（19+4）/ test_conversion_fingerprint+test_convert_excel+test_convert_doc 133 / 其余不变。

## 修复轮残余风险与说明

- 坏编码文件被跳过不回填（保留原字节）——修复属 Owner 授权批次；failed 清单即后续输入。
- mapping 越界条目未回填（unmatched），处置待 Owner。
- manifest 写失败真实 OSError 仍 mock 注入（root 环境 chmod 不可靠，沿用 §4.3）。
- 真实基座体检报告（inventory-lanlnk-20261114.json）未因本轮重跑——本轮修复均为合成场景可验证，真实报告的结论不受影响（观察分类细化只影响报告字段表达，不改缺口事实；如 Owner 需要按新分类口径刷新报告，属下次只读体检授权）。
- 真实资料回填/删除/重转及 commit/archive/push 仍未授权、未执行。


## 归档前收尾检查点（2026-11-14 追加）

- 本记录由 change 内 implementation-record.md 复制至 references/，原始检查点与失败历史保留；不将旧证据改述为新时点复跑。
- 实施提交：`32149d4a0066ee60757613ddae3a79e6e20b41db`（20 文件，+6189/−175）。
- 独立 review 后复跑：`uv run pytest tests/ -q` 退出码 0，312 passed；生态检查退出码 0（52 PASS）；change strict validate 退出码 0；`git diff --check` 通过。
- 精确暂存 20 文件后：`bash references/scripts/check_docs_consistency.sh --quiet` 退出码 0，38 PASS、零 FAIL/WARN；原未跟踪共享文件失败已在该时点消除。提交 hook 生态检查通过。
- 本轮仅同步主规格、保存验收记录并归档；本追加写入时归档尚待完成，最终结果以会话核验为准；未新增提交、未推送。
- 31MB 只读体检明细随 change 留在本地 gitignored archive；本记录保留其扫描范围、摘要、失败尝试及限制，不声称 fresh clone 包含该明细。
- 历史公司资料回填、删除、清理和重转换均未执行，仍须独立授权；蓝联仅为本次真实扫描样例。

### 归档结果

- 已归档至 `openspec/changes/archive/2026-11-14-harden-material-import-provenance/`，7 条 requirement 逐字同步；Purpose 逐字保留，无 TBD 或 delta 头残留。
- `openspec validate material-import-provenance --type spec --strict` 退出码 0。全仓 `openspec validate --specs --strict` 退出码 1（16 passed / 2 failed）：cross-layer-reconciliation 与 prd-handoff-traceability 各有既存 >500 字符警告；两文件与实施提交树逐字节一致，未修改，不报告全仓全绿。
- 归档前确认 change 目录无 tracked 交付物；验收记录已另存，未跟踪任何大报告。主规格与本验收记录尚未提交，未推送。
