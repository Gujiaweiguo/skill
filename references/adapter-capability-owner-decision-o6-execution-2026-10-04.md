# O6 执行记录 —— 正祥 CRM_DATA 归属登记（historical evidence，行为零改动）（2026-10-04）

```text
STATUS: COMPLETED（CRM_DATA 归属注释 + capability lnkcrm evidence/notes 更新 + backlog 注记，
  pytest 19/19、shared 53/53、check_docs_consistency 0/0/33、两层冒烟通过；行为与 docs 仓零改动）
RESIDUAL: 无（B 路线六要素留档另案；OPC 统一安排合并提交批）
OWNER SIGN-OFF: RECORDED (OPC)（引用自决策记录 :36，非本文件自立）
AUTHORIZATION: references/adapter-capability-owner-decision-o6-2026-10-04.md
               （decision: register-as-historical-evidence，方案 A；approved_changes :15-19；
               forbidden_changes :24-28）
SCOPE: O6 only —— 不追认 lnkcrm 正式报价基线；不触 pricing-basis.yaml；不写 docs 仓；
  O7-*/O9/O10-*/O11、删除动作、lnkreport 定价不在本轮范围
```

> **记录性质**：本文件是 O6 的执行记录，由执行会话落盘，验证结果均为本会话实测。
> 它不构成 B 路线（追认正式基线）、O7-*/O9/O10-*/O11、删除动作、lnkreport 定价或
> 其他任何 O 项的批准。

## 1. owner 决策记录核验（执行前，当前磁盘版本复核）

对象：`references/adapter-capability-owner-decision-o6-2026-10-04.md`。

| 核验项 | 要求 | 实测（文件:行） | 结果 |
|---|---|---|---|
| status | decided | `:8 status: decided` | ✅ |
| decision | register-as-historical-evidence | `:9 decision: register-as-historical-evidence（方案 A；不追认 lnkcrm 正式报价基线）` | ✅ |
| owner | OPC | `:5 owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）` | ✅ |
| OWNER SIGN-OFF | RECORDED (OPC) | `:36 OWNER SIGN-OFF: RECORDED (OPC)` | ✅ |
| 授权效力声明 | 存在 | `:37 OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署` | ✅ |
| forbidden_changes 含 CRM_DATA 行为红线 | 是 | `:28 CRM_DATA 数据结构 / 数值 / env 逻辑 / 生成行为改动（本轮仅注释与登记措辞）` | ✅ |
| approved_changes 四条 | 是 | `:16-19`（注释登记 / capability evidence/notes / backlog 注记 / 执行记录落盘） | ✅ |

**核验结论：通过。** owner=OPC 且记录在盘，按闸门规则执行。

## 2. generate_quote.py CRM_DATA 归属注释（仅注释行）

文件：`skills/business/pricing-generator/generate_quote.py`。

- **前**：`:280 CRM_DATA: dict[str, Any] = {` 定义处无归属注释（仅 :338 附近
  `modules_xlsx` 键的受管副本来源行内注释）。
- **后**：`:280-288` 新增 9 行归属注释块，`:289 CRM_DATA: dict[str, Any] = {` 定义不变。

注释内容四要素（对齐 approved_changes :16）：正祥单一客户历史成交证据 ✓；
受管副本来源（materials/03-products/CRM功能清单.xlsx，相对路径按公司基座解析）✓；
「不是 lnkcrm 标准价、正式基线走 B 路线六要素另案」✓；引 O6 决策记录 ✓；
另含「不得从 lnkcre 复制价格顶替」与「仅注释，数据结构/数值/env 逻辑/生成行为零改动」。

### 2.1 行为零改动实证（逐 hunk）

本轮工作树中该文件仅 **1 个 hunk**（`@@ -277,6 +277,15 @@`）：+9 行、-0 行；
程序化判定（`git diff -U0 | grep '^+' | grep -v '^+ *#'`）输出
**PROVEN: all added lines are comment lines**。
执行前 `git status` 该文件无未提交改动——O8 相关改动已在此前提交 `3fcb00a` 入库，
与本轮 hunk 无交叠；本轮在该文件上的全部 diff 即上述注释 hunk（O6 独占）。

## 3. capability lnkcrm 条目 evidence/notes 更新

文件：`skills/business/pricing-generator/references/adapter-capabilities.yaml:28-37`。

| 字段 | 前 | 后 |
|---|---|---|
| status | partial | **partial（不在 diff 中，零改动）** |
| evidence | 2 条（CRM_DATA 来源 + 设计包 §3.3.C） | 3 条（新增 O6 裁决登记项，:34） |
| notes | 「…对应关系**未登记**（O6 pending：是否追认为 lnkcrm 报价基线）…」 | 「O6 已裁决（2026-10-04 decided-A / evidence-registered）：CRM_DATA 归属**已登记**为正祥单一客户历史成交证据…**不是 lnkcrm 标准价**；正式报价基线未建，未来若建走 B 路线六要素另案…不得从 lnkcre 复制价格顶替。」（:37） |

- status 保持 partial：diff 中无 status 行变更；`yaml.safe_load` 复核
  `status == 'partial'` ✅，evidence 3 条且含 O6 项 ✅。
- 其他 7 个产品条目（lnkcre/lnkchat/lnkchatbi/lnkreport/lnkvision/lnkgateway/lnkwebsite）
  零触碰（diff 上下文仅含 lnkchat 条目头作为未改动的上下文行）。
- YAML 合法性：`yaml.safe_load` 解析通过。

## 4. backlog 盘点报告注记

文件：`references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md`
末尾新增 `## 12. 状态更新（2026-10-04 O6 执行后追加）`：
O6 frozen → decided-A / evidence-registered（引决策记录 + 执行记录；
§3.2 行「当前状态 frozen」为落盘时快照）；其余维持冻结清单同步移除 O6
（「O7-*/O9/O10-*/O11、删除动作、lnkreport 定价」）。

## 5. 冒烟（不落 docs 仓）与验证输出

### 5.1 数据层断言（uv run python -c，pricing-generator venv）

CRM_DATA 关键字段全断言通过：product_name/product_label、standard_items 序号
1.1-1.4、optional_items 2.1-2.3、standard_first_year_total=100000、
standard_next_year_total=30000、modules_xlsx 路径、modules=8 组、service_notes=5 条、
**sum(standard_items 首年价)=100000 == standard_first_year_total**、
plans 方案 A（100000/30000）与方案 C（130000/30000）。

### 5.2 CLI 冒烟（临时基座 /tmp/opencode/o6-smoke/base，COMPANY_BASE 重定向）

- 临时基座仅含只读副本：pricing-basis.yaml、materials/03-products/CRM功能清单.xlsx
  + 最小 company.yaml stub；**COMPANY_BASE 指向 /tmp**，docs 仓零写入。
- 命令：`COMPANY_BASE=/tmp/opencode/o6-smoke/base uv run python generate_quote.py
  --customer O6SMOKE --product CRM --mode SAAS` → **rc=0**。
- 输出：`/tmp/opencode/o6-smoke/base/out/proposals/O6SMOKE/报价单_CRM_SAAS_O6SMOKE_20261005.xlsx`
  （Sheet1=CRM报价 33 行；Sheet2=CRM功能清单 156 行，xlsx 受管副本来源）。
  注：CLI 打印一条 lnkcre feature-baseline WARN——临时基座缺 30-products 基线文件的
  预期降级（渲染层设计行为，与 CRM 链路无关）。
- openpyxl 读回断言：序号 1.1-1.4/2.1-2.3/3.1-3.3 全在；金额 60000/20000/100000/
  30000/130000/10000 全在；**合计 130000 = 标准 100000 + 对接全选 30000** 一致。
- docs 仓对照：`git -C /opt/code/docs/lanlnk status --short` 冒烟前后 **byte-identical**
  （22 行既有脏项不变），`out/proposals/` 无 O6SMOKE 目录。

### 5.3 验证套件（全绿）

| 验证 | 命令 | 结果 |
|---|---|---|
| pricing-generator | `uv run pytest -q` | **19 passed**（0.16s） |
| shared resolver | `uv run python -m unittest discover -s tests`（shared/product_context） | **Ran 53 tests — OK** |
| 生态一致性 | `bash references/scripts/check_docs_consistency.sh` | **FAIL 0 / WARN 0 / PASS 33 — RESULT: PASS** |
| git 卫生 | `git diff --check` | 干净（rc=0） |
| 变更面 | `git status --short` / `git diff --name-only` | 恰为 3 个允许修改文件（M）+ 1 个既有未跟踪决策记录（??） |

## 6. 边界与冻结确认

- 允许清单外零改动：`git diff --name-only` = {generate_quote.py,
  adapter-capabilities.yaml, backlog 盘点报告}，与本执行记录（新增）一一对应；
  O8 已提交改动（`3fcb00a`）原样共存未回退未重写。
- 冻结维持：O7-*/O9/O10-*/O11、删除动作（D1/D2）、lnkreport 定价——未触碰。
- 未正祥价标注为 lnkcrm 标准价、未从 lnkcre 复制价格、未写 docs 仓任何文件。
- **未 git add、未提交、未推送**（OPC 随后统一安排合并提交批）。
