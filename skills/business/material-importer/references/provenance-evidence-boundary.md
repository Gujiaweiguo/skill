# 溯源证据边界（图片 / text-sparse / OCR 投影）— 唯一权威源

> 地位：本文件是图片投影、text-sparse 页信号、OCR 投影的**公共证据边界规则的唯一权威源**
> （OpenSpec change `harden-material-import-provenance` 设计 D9）。
> 消费方（material-importer、competitor-product-analyzer 及后续任何 skill）通过**引用本文件路径**
> 获得规则，不得在自己的文档里内嵌第二份规则副本；操作细节（如何回看、用什么工具）留在各自
> skill，规则语义（什么算已验证、什么只能算线索）只在此处定义。
> 改动本文件须同步检查所有消费方的引用仍然成立（AGENTS.md「Shared files」表 +
> `references/scripts/check_docs_consistency.sh` 的 SHARED_FILES 数组双 source of truth）。

## 1. 检测三态语义

所有 advisory 检测（pptx_table_guard 表格检测、text-sparse 页扫描、图片提取核对等）只有三个合法结果态：

| 态 | 含义 | 严格边界 |
|---|---|---|
| **发现** | 检测成功且检出（附 slide/页号与原因） | 只描述"检测器看到了什么"，不解释业务含义 |
| **none** | 检测成功且无发现 | **仅** = 检测执行成功且零命中；任何检测失败都不得渲染成 none |
| **undetermined** | 检测失败（附原因，如 `detect-error: ...` / `python-pptx-unavailable`） | 失败就是失败；永不降级为 none，也永不升级为发现 |

禁止把三态压缩成布尔（"有问题/没问题"会吞掉 undetermined）。

## 2. 旧代际 ≠ none

旧代际产物（转换器版本早于某检测特性，如 v1 及更早的 raw md 没有 `pptx_text_sparse` 检测行），
该页检测状态 = **未检测（旧代际）**，语义上属于 undetermined 的"从未执行"分支：

- SHALL NOT 记为 none（成功无发现）——检测根本没跑过，不是跑了没发现；
- SHALL NOT 触发自动回填或强制重转（重转属 Owner 授权批次）；
- 报告表达建议：`not_scanned (legacy-generation: 检测行早于 vX 引入)`。

## 3. 页级锚点

OCR / 图片投影引用原页时，锚点 = **`source_sha256` + 页（slide N）/ 文件名**二元组：

- `source_sha256` 是**原件字节哈希**（不是投影文件哈希）——原件变更后旧锚点即失效，
  这是特性不是缺陷（防跨版本误挂）；
- slide 号从 1 起，与 pptx_table_guard / text-sparse 的页号同源；
- 只给文件名不给哈希 = 弱锚点，须标注；只给哈希不给页号 = 未定位，不能支撑"该页有 X"级主张。

## 4. OCR 文本 = 检索线索，不是已验证业务结论

OCR 投影文本（DeepSeek-OCR-2 / 任何 OCR 引擎产出）的合法用途边界：

- ✅ 页内/全库**实体名与关键词检索索引**（"哪几页出现过『铺位状态』"）；
- ✅ 定位候选（辅助回看）；
- ❌ 未经原页核验（原件或视觉回看）直接升级为"已验证业务结论"（功能存在、字段语义、
  流程规则、状态机……）；
- ❌ OCR 产物与原件正文、其他投影互当独立证据累计——同源只计一次（来源链）；
- OCR 转写可能有误（形近字、表格错位）：引用 sparse 页内容一律以视觉回看为准，
  OCR 仅作检索索引（2026-10-31 海鼎 73 页收尾实证：「清单型图可采信 OCR」假设被抽验推翻）。

## 5. 图片缺失 ≠ 证据不存在（fresh-clone 三项要求）

`raw/**/_media/` 与 `**/raw/` 被 gitignore，fresh clone 后图片不可得。此时：

- **SHALL NOT** 把"图片文件缺失"解释为"原证据从未存在"或"该主张无证据"；
- 依赖图片投影的重要业务主张，须携带**三项可分别核验在/缺**的要素：

| 要素 | 含义 | 在/缺如何核验 |
|---|---|---|
| **可读语义转录** | 该图承载的业务语义文字版 | 逐项存在与否可直接检查（有/无该字段且非空） |
| **源页锚点** | `source_sha256` + slide N（§3 格式） | 锚点字段存在且格式合法即"在"；原件在百度盘/Git LFS 外置库可寻回 |
| **可用恢复定位** | 指明从哪里恢复原图（百度盘路径 / 外置二进制库 / 原件持有者） | 定位描述存在且可执行即"在" |

- 三项**逐项独立表达**，不得合并成单一布尔；缺任何一项 = 该主张降级为待补强，不是删除主张；
- **恢复定位 ≠ 业务语义**：知道"图在百度盘哪条路径"不能替代"图上画的是什么"；
- Git/百度盘二进制归属不变：不因本规则批量把二进制纳入 git。

## 6. 如实表达限制（不判"无信息"）

以下情形状态 SHALL 如实表达，SHALL NOT 判"无信息/垃圾"：

- **跨页装饰图**：同一 media 文件逐页重复出现（如页脚 logo、固定装饰条）——回看选图时剔除，
  但不据此判该页无信息（信息可能在正文文本里）；
- **动画承载页**：信息由 PPT 动画承载、无静态信息图（OCR 零命中）→ 标
  `not_scanned（图形态缺失）`，需人工播放动画记录——**不得判「无信息」**；
- **未回看页**：被 text-sparse 标记但尚未回看 → 状态就是"未回看"，不得预填结论；
- text-sparse 信号本身 = **回看该页原件的复核提示**（仅此而已）：不自动触发 OCR、
  不自动判业务域、不做封面/目录页型豁免。

## 7. 二进制归属不变

raw 投影、_media 图片、原件二进制的存放归属（git 文本 / 百度盘二进制 / 外置库）是既有契约，
本边界文件不改变任何归属；fresh-clone 缺图场景的补救是补齐三项要素（§5），不是迁移二进制。

## 8. evidence_state 逐项映射表

共享词表 `source-reference.schema.json` 的 `evidence_state`
（`observed | inferred | not_found | not_scanned | inaccessible | conflicting | not_applicable`）
**仅在语义确实满足时逐项引用**；映射依据成文如下，语义不满足的项保留本工具原生字段、不强行映射
（不建第二套契约，也不无中生有映射）：

| material-importer 原生表达 | → evidence_state | 语义依据 | 备注 |
|---|---|---|---|
| accessibility=accessible（直接观察到文件/读取成功） | `observed` | 观察事实来自本次直接读取 | 保留 observed 的路径事实 |
| source_nature/link_state=inferred（路径结构、文件名、`_index.json` imported_from 推断） | `inferred` | 来源身份由推断得出，未验证 | 唯一候选也不升级 |
| accessibility=missing（声明来源路径已查找且不存在） | `not_found` | 查找已执行且未命中 | 原生产物仍标 declared，两维并存 |
| accessibility=permission-denied（无权限读取） | `inaccessible` | 物理不可访问 | — |
| not-scanned（扫描范围未覆盖：目录不可进入、范围未枚举） | `not_scanned` | 本次未扫描该范围 | — |
| backend-unavailable（可选后端缺失，如 libreoffice/OCR） | `not_scanned` | 该检查项本次未执行 | 原生 backend-unavailable 字段**保留**，映射仅用于跨契约对齐 |
| 旧代际未检测（§2） | `not_scanned` | 检测从未执行（历史代际早于特性） | 附 legacy-generation 注记 |
| source: "none"（authored 内容） | `not_applicable` | authored 内容无外部来源链接 | — |
| hash_check=mismatch（声明哈希 ≠ 当前原件哈希） | **不映射** | freshness 维度问题，两侧观测不构成"记录内容互斥" | 保留原生 mismatch + 两侧值 |
| 歧义候选（多候选 unresolved） | **不映射 conflicting** | schema 的 conflicting 指记录内容互斥；多候选是证据不足 | 保留原生 unresolved + 候选清单 |
| unknown（缺指纹/缺元数据） | **不映射** | 检查已执行、结论是信息不足，非"未找到"亦非"未扫描" | 保留原生 unknown |
| garbage-candidate / encoding-invalid（投影候选线索） | **不映射** | 候选线索不是证据状态 | 保留原生候选清单表达 |

## 9. 消费方清单与引用方式

当前登记消费方（与 AGENTS.md「Shared files」表、`check_docs_consistency.sh` SHARED_FILES 同步）：

- **material-importer**（owner）：SKILL.md 证据边界章节引用本文件；
- **competitor-product-analyzer**：SKILL.md 边界规则段落引用本文件（保留其回看操作细节）。

新消费方接入 = 引用本文件路径 + 在上述两处登记，不复制规则文本。
