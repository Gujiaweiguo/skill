# O5-lnkcrm-code 冻结线对账执行记录（路线 A，2026-10-04）

```text
STATUS: EXECUTED（已批准执行并已完成）
OWNER SIGN-OFF: NOT RECORDED（仅会话授权，无独立签署记录）
SCOPE: O5-lnkcrm-code reconciliation only（lnkcrm code 维度冻结线对账，路线 A）
```

> **记录性质（必读）**：本文件是对账**执行记录**，由执行会话本身落盘（非事后补录，
> 验证结果均为本会话实测）。它记录的事实是：**用户在本轮会话中明确批准执行
> lnkcrm 冻结线对账（O5-lnkcrm-code reconciliation，路线 A）**，并随附 owner 决定
> （会话授权，指令原文含「批准执行」、owner 决定核心、逐条允许/禁止边界，且明文
> 「授权来源为本轮用户会话明确授权；除非发现真实独立签署记录，否则 OWNER SIGN-OFF:
> NOT RECORDED」）。它**不是**、也**不得被引用为**一份独立签署的 owner 批准记录
> ——与 B1/B2/B5/B3 执行记录同口径（§3 事实区分）。本对账**仅 ratify lnkcrm code
> 维度**：不构成 registry 删除、O4 字段删除或 O5 其余子项批准。

---

## 1. 登记字段

```yaml
decision_id: O5-lnkcrm-code
decision_date: "2026-10-04"
record_date: "2026-10-04"
owner: "opc"
owner_basis: "本仓治理约定：一人公司，owner = opc（AGENTS.md；与既有决策记录口径一致）。owner 身份有依据，但 owner 独立签署记录不存在（见 §3）"
route: "A（承认 docs 仓已提交事实为现行基线）"
status: "已批准执行并已完成"
owner_decision: |
  承认 docs 仓已提交事实 c41a978 为现行基线：
    lnkcrm code_root = /opt/code/lnkcrm（revision 4323b8c…，source=company.yaml）；
    lnkcrm code authority.status = complete。
  其余冻结线不变：lnkgateway ontology=unresolved（不得跨产品 fallback）；
  lnkwebsite prd-only / ontology not-applicable。
  本决定只 ratify lnkcrm code 维度；不构成 registry 删除、O4 字段删除或
  O5 其余子项批准。
authorization:
  type: "session_consent"
  source: "本轮用户会话明确批准「批准执行 lnkcrm 冻结线对账（O5-lnkcrm-code reconciliation，路线 A）」的提示词（含 owner 决定核心、三、允许修改 / 四、严格禁止 / 五、验证 / 六、最终报告 逐条边界与命令清单）"
  not_claimed: "不存在独立签署的 owner 批准记录（无 verbatim 指令落盘、无签署块）"
ratified_fact:
  docs_commit: "c41a978a62f608aac83b67d8e32775519b5b7740（/opt/code/docs，JasonGu，2026-10-04 15:27:48 +0800）"
  commit_subject: "docs(lnkcrm): 登记代码仓与 S6 验收快照（42/105/0）"
  company_yaml_change: "lanlnk/config/company.yaml: lnkcrm code_root null → /opt/code/lnkcrm（prd_ready 保持 false）"
  live_verification: "2026-10-04 本会话实测 resolve_product('lnkcrm')：layers.code_root=/opt/code/lnkcrm、authority.code.status=complete、revision=4323b8c9f6f195dd82083348dd6e854e7360afa3（与 owner 决定 revision 4323b8c… 一致）"
new_baseline:
  lnkcrm_layers_code_root: "/opt/code/lnkcrm（company.yaml source）"
  lnkcrm_authority_code: "complete"
  unchanged_freeze_lines:
    lnkgateway_ontology: "unresolved（ontology_entry=null，无跨产品 fallback）——本会话实测保持"
    lnkwebsite: "prd-only / ontology not-applicable——本会话实测保持"
files_implemented:
  - path: "shared/product_context/tests/test_adapter_status_migration_gate.py"
    change: "FREEZE_LINES['lnkcrm'] 由 {'code': 'present-unconfirmed'} 改为 {'code': 'complete'}（含依据注释更新：company.yaml code_root=/opt/code/lnkcrm，docs c41a978 ratified）；test_lnkcrm_code_authority_stays_present_unconfirmed 改写为 test_lnkcrm_code_authority_complete_under_configured_root：断言 layers.code_root=Path('/opt/code/lnkcrm') + authority.code.status=complete + code.revision 非空（新增 revision 证据断言，强化）。lnkgateway / lnkwebsite / 无跨产品 fallback / capability≠authority / O4 白名单扫描断言全部保留未动"
  - path: "shared/product_context/tests/test_resolver.py"
    change: "test_lnkcrm_code_stays_present_unconfirmed 改写为 test_lnkcrm_code_root_configured_complete：断言 layers.code_root=Path('/opt/code/lnkcrm') + code.status='complete'（精确等值）+ code.path + code.revision 非空；ontology/prd complete 断言保留。旧断言允许 {present-unconfirmed, planned} 二值集合并断言 ≠complete——新断言更严，未弱化"
  - path: "skills/business/product-prd-generator/tests/test_paths.py"
    change: "B3 时期登记的既有失败测试 test_unconfirmed_lnkcrm_code_root_requires_explicit_override（断言 resolve_code_root('lnkcrm') 抛 MissingProductDataError）按新基线改写为 test_configured_lnkcrm_code_root_resolves_without_override：断言 resolve_code_root('lnkcrm') == Path('/opt/code/lnkcrm')（无显式覆盖）。这是 B3 执行记录 §5 登记的过时测试的正式处置（该记录判定其失败与 B3 无因果，留待归属会话或后续授权——本轮授权即该后续授权）"
  - path: "references/adapter-capability-owner-decision-lnkcrm-freeze-reconcile-2026-10-04.md"
    change: "本执行记录（新增）"
  - path: "references/product-registry-迁移审计-2026-10-04.md"
    change: "§4 追加「O5-lnkcrm-code 对账状态注记」（授权 §三.5 最小回写；B1-B7 各注记与 §1/§2 快照原文不重写）"
  - path: "references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md"
    change: "follow_up 追加一条 lnkcrm code 冻结线对账状态条目（授权 §三.5 最小回写；B1/B2 既有条目与其余内容不动）"
forbidden_unchanged:
  - "resolver 生产代码（shared/product_context/resolver.py、models.py 等，零改动——本对账只改测试断言）"
  - "company.yaml（docs 仓零改动；c41a978 为既有已提交事实，本轮只承认不修改）"
  - "30-products/**（docs 仓零改动）、产品代码仓（/opt/code/lnkcrm 等零改动）"
  - "product-registry.yaml（含数据区与头部，零改动；registry 删除 = 独立 owner 批准动作）"
  - "六份 adapter-capabilities.yaml 与任何 capability 文件（零改动；capability≠authority 边界维持）"
  - "O4 实际迁移（adapter_status 字段级迁移实施冻结维持）"
  - "O5 其余子项（五问其余项）、B4/B6/B7、O6-O11（全部未批准、未执行、冻结）"
  - "shared/product_context/README.md :52 冻结线 prose（不在授权清单，见 §6 遗留）"
  - "其余冻结线断言（lnkgateway / lnkwebsite / 无跨产品 fallback / capability≠authority——测试实测全绿即证）"
results:
  source: "本对账执行会话实测"
  shared_suite: "uv run python -m unittest discover -s tests -p 'test_*.py'（shared/product_context）：Ran 53 tests，OK（全绿，含 O4 门禁三条冻结线 + capability schema；与 B2/B5-R5 基线 53 passed 一致）"
  prdgen_suite: "uv run pytest -q（product-prd-generator）：169 passed / 3 skipped（B2 基线 169+3 恢复；B3 时 168 passed / 1 failed 的唯一失败即本轮改写的过时测试，已消除）"
  script_run: "bash references/scripts/check_docs_consistency.sh：FAIL=0 / WARN=0 / PASS=33（RESULT: PASS，与 B2/B3/B5-R5 基线一致）"
  format_checks: "git diff --check 通过（无 whitespace 错误）"
not_executed:
  - "O5 其余子项（五问其余项：deep 读码评估 / 实现级评估解锁等）未批准、未执行"
  - "O4 字段删除、registry 删除、B4/B6/B7、O6-O11 全部保持冻结"
version_control:
  committed: false
  pushed: false
  this_record: "untracked 新增文件"
  worktree: "工作区保留执行前全部既有未提交修改（25 个 M 文件 + 多处 untracked，执行前 git status 快照留档）；本轮未回退/未覆盖/未清理/未使用 git add -A"
```

## 2. 日期与 owner 的确认依据

**decision_date = 2026-10-04**：对账执行会话日期（环境时区 Asia/Shanghai）；与前置链
（O1/O2 Batch 1、O3/Batch 2 audit、B1、B2、B5 系列、B3）同日。**owner = opc**：依据本仓
治理约定（AGENTS.md 一人公司）与既有决策记录一致口径。授权行为主体按该治理约定即
repo operator = opc。**但** owner 身份可确认 ≠ 存在 owner 独立签署记录——后者不存在
（授权提示词明文要求保持 NOT RECORDED）。

**被 ratify 事实的签署归属注意**：docs 提交 c41a978 的作者是 JasonGu，属 docs 仓
正常提交；本轮 owner 决定**承认该提交为现行基线**（路线 A = 承认既成事实），这不等于
为该提交补签。引用时不得表述为「c41a978 经 owner 签署」。

## 3. 事实区分（防误引）

| 命题 | 状态 | 依据 |
|---|---|---|
| 用户明确授权执行 O5-lnkcrm-code 对账路线 A（会话同意，含 owner 决定核心与逐条边界） | **成立** | 本轮用户会话批准；指令原文明文「授权来源为本轮用户会话明确授权；除非发现真实独立签署记录，否则 OWNER SIGN-OFF: NOT RECORDED」 |
| 存在独立签署的 owner 批准记录（verbatim 指令落盘 / 签署块 / SIGN-OFF: RECORDED） | **不成立，不得声称** | 全仓决策文档族中无本对账的独立签署记录；B1/B2/B5/B3 记录已确立同口径区分 |

引述规则：后续任何文档引用本对账授权时，只能表述为「lnkcrm code 冻结线经用户会话
授权对账（2026-10-04，路线 A，见本记录）」，不得表述为「经 owner 独立签署批准」。
**本对账完成亦不构成 registry 删除、O4 字段删除或 O5 其余子项批准**（各自需独立
owner 批准动作）。

## 4. 批准范围与实际实施对账

| 授权 §三 列出的目标 | 实施 | 载体文件 |
|---|---|---|
| 1. test_adapter_status_migration_gate.py lnkcrm 断言改新基线（其余断言不弱化） | ✅ FREEZE_LINES + 测试方法改写；lnkgateway/lnkwebsite/无跨产品 fallback/capability≠authority/O4 白名单扫描全部保留；新增 revision 证据断言 | shared/product_context/tests/test_adapter_status_migration_gate.py |
| 2. test_resolver.py lnkcrm 测试改新基线（同理不弱化） | ✅ 精确等值断言（complete + 路径 + revision），ontology/prd 断言保留；旧二值集+≠complete 断言被更严断言取代 | shared/product_context/tests/test_resolver.py |
| 3. test_paths.py 过时断言改写或删除 | ✅ 改写（非删除）：新断言 resolve_code_root('lnkcrm') == /opt/code/lnkcrm 无需显式覆盖 | skills/business/product-prd-generator/tests/test_paths.py |
| 4. 新增执行记录 | ✅ 本文件 | references/adapter-capability-owner-decision-lnkcrm-freeze-reconcile-2026-10-04.md |
| 5. 最小回写审计 / O3 follow_up 冻结线相关表述 | ✅ 审计 §4 追加对账状态注记（历史注记不重写）；O3 follow_up 追加一条状态条目 | references/product-registry-迁移审计-2026-10-04.md；references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md |

范围对账结论：实际实施 = 批准范围，无超出。授权 §四 禁止项全部未触碰（resolver
生产代码 / company.yaml / 30-products / 产品代码 / registry / capability 文件 /
O4 / O5 其余子项 / B4/B6/B7 / O6-O11 / 其余冻结线断言 / 既有未提交修改）。

## 5. 与 B3 既有失败登记的闭合

B3 执行记录 §5 与审计 §4-B3 注记登记的既有失败
（`test_unconfirmed_lnkcrm_code_root_requires_explicit_override`，DID NOT RAISE，
根因 docs 侧 company.yaml 已配置 lnkcrm code_root）即本轮授权处置对象：该测试已按
新基线改写为 `test_configured_lnkcrm_code_root_resolves_without_override` 并通过。
历史注记（B3 记录 §5、审计 §4-B3 注记原文）按仓惯例保留当时判断，不重写；其处置
状态由审计 §4 新增对账注记承载。

## 6. 遗留与同步事项

1. **shared/product_context/README.md :52 冻结线 prose 过时**：该行仍描述
   「lnkcrm code `present-unconfirmed`」。该文件不在本轮授权清单（§三 未列），未触碰。
   属文档级迁移候选（同 B5 批次的口径），待后续授权对齐。
2. **O3 follow_up 的 B3 状态条目仍未同步**：B3 执行记录 §6.1 登记的同步缺口不属于
   冻结线表述，本轮 follow_up 回写仅追加 lnkcrm 对账条目，不代行 B3 补记（需独立授权）。
3. **revision 漂移预期**：lnkcrm 代码仓活跃开发（ad6f0c0b → 1d5ebb6b → 4323b8c），
   `revision` 将持续前进。本轮测试断言只钉 status=complete + 路径 + revision 非空，
   **不钉具体 revision 值**（authority 语义与 revision 前进无冲突；O5 暂缓原由
   「revision 漂移 = 不稳定基线」已被 owner 路线 A 决定取代，本记录仅登记该语义变化）。
4. **test_product_authority_fixtures.py lnkcrm 旧 reason 字符串**（"no repo yet (planned)"
   等，:114/:180）：自包含 fixture 数据（B3 基线已实证不与 live resolver 对比），不在
   授权清单，未触碰；如需对齐属后续授权。
5. **B4、B6、B7 保持冻结**；O5 其余子项（五问其余项）、O6-O11 保持冻结；各自需独立授权。
6. **版本控制**：本记录 untracked；全仓未提交、未推送；既有未提交工作树修改原样保留。

## 7. 证据路径索引（均已实物核验存在）

- `/opt/code/docs` 提交 `c41a978a62f608aac83b67d8e32775519b5b7740`（lanlnk/config/company.yaml diff：lnkcrm code_root null → /opt/code/lnkcrm）
- `/opt/code/docs/lanlnk/config/company.yaml`（products 块 lnkcrm `code_root: /opt/code/lnkcrm`，`# --- products-end ---` marker 前后；docs 仓，零改动）
- `/opt/code/lnkcrm`（实际 checkout，`git rev-parse --short HEAD` = 4323b8c；产品仓，零改动）
- `references/product-registry-迁移审计-2026-10-04.md` §4-B3 注记（既有失败登记，历史原文）、§4 新增对账注记
- `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md` follow_up（新增对账条目）
- `references/adapter-capability-owner-decision-b3-execution-2026-10-04.md` §5（既有失败登记，闭合对象）
- `shared/product_context/tests/test_adapter_status_migration_gate.py`（O4 门禁，冻结线钉死处）
- `shared/product_context/tests/test_resolver.py`（八产品 live 回归）
- `skills/business/product-prd-generator/tests/test_paths.py`（resolve_code_root 行为回归）
