# material-import-provenance Specification

## Purpose

material-importer 溯源生命周期契约：只读溯源体检的状态语义与报告边界、源变化检测与转换指纹、转换/回填入口守卫、历史溯源修复候选的分级边界、多公司基座隔离，以及图片/text-sparse/OCR 证据的共享边界。约束"发现 ≠ 判断"：观察、声明、推断、不可得四类信息不得互相冒充，机械新鲜度不得冒充人工审核结论。

## Requirements

### Requirement: 只读溯源体检 SHALL 状态分明且零业务写入

material-importer SHALL 提供可重复执行的只读溯源体检（inventory / dry-run）入口，覆盖 incoming 原件、raw Markdown/CSV/notes 边车、manifest 与 materials 的来源声明。每条来源链接 SHALL 区分四类状态：observed（实际观察到的事实）、declared（产物自称来源，须再验证可解析性与哈希）、inferred（路径结构或文件名候选推断）、unknown / unavailable（无权限、未挂载、缺二进制等无法观察的情形）。体检 SHALL 零业务写入，扫描不完整 SHALL 显式标记，报告 SHALL 字段明确且按路径稳定排序，退出码 SHALL 区分"完成无缺口 / 完成有发现 / 工具失败"。

#### Scenario: 声明来源可解析且哈希匹配

- **WHEN** 某产物声明 source 与 source_sha256，且该原件当前存在、当前字节哈希与声明一致
- **THEN** 报告 SHALL 记为 declared 且 hash-match，并保留 observed 的原件路径事实

#### Scenario: 声明哈希与当前原件不匹配

- **WHEN** 声明的 source_sha256 与原件当前字节哈希不一致
- **THEN** 报告 SHALL 记为 declared 且 hash-mismatch，SHALL NOT 自动判定哪一侧是权威或触发任何重写

#### Scenario: 路径推断不得升级为已验证身份

- **WHEN** 某产物的来源仅由目录结构或唯一文件名候选推断得出（含 `_index.json` 的 imported_from）
- **THEN** 报告 SHALL 记为 inferred 并附候选与依据，SHALL NOT 记为已验证原件身份，即便候选唯一

#### Scenario: 不可访问范围如实上报

- **WHEN** 体检遇到无权限目录、未挂载路径或缺失的可选二进制（如 libreoffice、OCR 后端）
- **THEN** 相关检查项 SHALL 记为 unknown / unavailable 并列入不可访问清单，SHALL NOT 记为"不存在"或"已验证无问题"；范围不完整时报告 SHALL 标记未扫描范围，SHALL NOT 给出全库完成结论

#### Scenario: 只读模式零业务写入

- **WHEN** 体检在完整基座上运行
- **THEN** 运行前后 `_index.json`、全部 manifest、materials、raw 产物 SHALL 字节不变

#### Scenario: 缺口发现与工具失败退出码可区分

- **WHEN** 体检发现来源缺失/歧义/损坏等缺口，或体检自身出错（如参数无效）
- **THEN** 前者 SHALL 以"完成且有发现"类退出码结束并输出缺口清单（含缺来源、缺哈希、缺原件、歧义匹配、manifest 损坏/记录冲突/产物缺失），后者 SHALL 以"工具失败"类退出码结束，二者 SHALL NOT 混用

### Requirement: 溯源修复候选 SHALL 分级且唯一候选不自动升级为历史事实

历史溯源修复 SHALL 仅以候选生成与 dry-run 报告形式规划，SHALL NOT 在未经 Owner 基于 dry-run 报告另行授权时执行任何历史资料写入。候选 SHALL 区分三级：candidate-association（补记当前候选关联）、recorded-at-conversion（转换时记录的来源声明，三要件与语义边界见场景）、reconverted（重新转换生成的新 provenance），三级 SHALL NOT 互相冒充；分级与哈希语义 SHALL 随产物持久化，SHALL NOT 仅存于一次性报告。verified-historical 为更高独立核验概念，SHALL NOT 由本 change 工具自动授予，本 change SHALL NOT 实现新历史审计器。以当前原件字节哈希补记的溯源 SHALL 显式标注为 backfill 时点哈希；读取旧回填记录 SHALL 保持回填性质或哈希语义未知，SHALL NOT 因沿用了旧字段名即升级为转换时已验证。已有 `source:` 的文件 SHALL NOT 被回填覆盖。

#### Scenario: 唯一候选仅产生补记候选

- **WHEN** 某历史投影按文件名唯一匹配到一个现存原件
- **THEN** 工具 SHALL 产出"补记当前候选关联"（candidate-association）级候选（含该原件当前哈希与候选依据），SHALL NOT 产出 recorded-at-conversion 或更高级结论

#### Scenario: 候选分级随产物持久化

- **WHEN** 补记当前候选关联被授权执行并写入
- **THEN** 产物自身记录 SHALL 含 provenance_class 与 at-backfill 哈希语义字段，后续工具重跑读取时分类不丢失，一次性报告仅作汇总

#### Scenario: 旧 backfilled 记录不升级

- **WHEN** 读取旧记录且 extracted_by 含 backfilled 标记（无论哈希字段用旧名 `source_sha256` 还是新名）
- **THEN** 分类 SHALL 保持回填性质；既无转换器签名也无 backfilled 标记的旧哈希 SHALL 分类为哈希语义未知

#### Scenario: recorded-at-conversion 须齐备三要件且不越权表述

- **WHEN** 判定某记录为 recorded-at-conversion
- **THEN** SHALL 同时具备：转换器产出的 provenance 记录（含 extractor 签名与格式）、解析后落在同一公司基座内的来源路径、格式合法的转换时哈希记录；唯一文件名候选 SHALL NOT 触发该级；该级 SHALL 仅表述为存在转换时点的来源声明，SHALL NOT 表述为独立验证了历史真实性，SHALL NOT 要求当前原件哈希等于记录哈希（freshness 分维度）；verified-historical 更高级别 SHALL NOT 由本工具自动授予

#### Scenario: 已有 source 不被覆盖

- **WHEN** 目标文件已有 `source:` 字段（无论正确与否）
- **THEN** 回填模式 SHALL 跳过写入，仅在报告中给出该来源的可验证性评估与修复建议

#### Scenario: 歧义与无依据映射保持 unresolved

- **WHEN** 候选匹配存在多于一个同格路径，或 CSV 与 sheet/输出的映射缺乏可验证依据
- **THEN** 该条目 SHALL 保持 unresolved 并列出候选，SHALL NOT 选择其一写入，SHALL NOT 从 CSV 内容推算未验证的原始单元格坐标

#### Scenario: 损坏 manifest 阻止该项输出写入

- **WHEN** 转换目标目录的 `_manifest.json` 无法解析、可解析但结构非法（非记录数组/记录缺必需键）、或含同 source_path 重复且内容冲突的记录
- **THEN** 该项目 SHALL 在写出任何输出**之前**失败：manifest 原样保留、该目录已有输出字节不变，失败 SHALL 显式报告；批量 SHALL 继续处理目标 manifest 正常的其他独立项目并汇总失败；工具 SHALL NOT 进入"输出已写而 manifest 未更新"的半成功状态而不报错

### Requirement: 源变化检测 SHALL 基于转换指纹且不虚报 up-to-date

转换器 SHALL 定义并记录转换指纹：原件身份与字节哈希、转换器代际、影响内容的全部有效选项、可得时的后端版本、预期输出清单与各输出字节指纹；MD 产物内联指纹 SHALL 采用明确摘要范围（排除文首溯源头的正文范围）的范围哈希，SHALL NOT 声称文件内字段是包含自身的完整文件 SHA-256。`up-to-date` 仅当原件、有效配置、预期输出均未变时报告；原件/选项/转换器变化、输出缺失、输出被人工修改 SHALL 分别报告；旧产物缺指纹 SHALL 记为信息不足（unknown），不自动 up-to-date 也不强制重转。任何执行模式 SHALL NOT 静默覆盖已按指纹检出人工修改的输出（显式覆盖旗标除外）；`--check` SHALL 零业务写入。

#### Scenario: 同输入同配置且输出完整则可跳过

- **WHEN** 原件哈希、有效选项、转换器代际与上次一致，且预期输出全部存在且字节指纹未变
- **THEN** 状态检查 SHALL 报告 up-to-date，`--skip-up-to-date` 模式 SHALL 跳过重转换；旧默认模式 SHALL 按现状语义重转（幂等重写），行为与改动前一致

#### Scenario: 源/选项/转换器变化分别可识别

- **WHEN** 原件字节变化，或有效选项变化，或转换器代际变化
- **THEN** 状态检查 SHALL 分别报告 source-changed / options-changed / converter-changed，三者 SHALL NOT 互相折叠

#### Scenario: 缺指纹的旧产物保持 unknown 且检查零写入

- **WHEN** 旧产物没有任何指纹元数据，`--check` 对已有输出与缺元数据输出运行
- **THEN** 状态 SHALL 为 unknown（SHALL NOT 判 up-to-date、SHALL NOT 强制重转），且运行前后全部目标文件 SHALL 字节不变

#### Scenario: skip-up-to-date 遇 unknown 保留已有输出

- **WHEN** `--skip-up-to-date` 模式遇到无指纹元数据但已有输出的产物
- **THEN** SHALL 保留已有输出（SHALL NOT 自动转换），报告 unknown 与需显式重转；首次新输出与 output-missing 的补齐语义 SHALL 按重转补齐处理，SHALL NOT 被 unknown 规则扩张拦截；旧默认命令遇 unknown SHALL 保持改动前的现状覆盖语义

#### Scenario: 输出缺失或被人工编辑不虚报

- **WHEN** 预期输出中有文件缺失，或输出存在但字节指纹与记录不一致
- **THEN** 状态 SHALL 分别报告 output-missing / output-modified，SHALL NOT 报告 up-to-date

#### Scenario: 已检出人工修改时任何模式不静默覆盖

- **WHEN** 输出当前指纹与记录不一致（output-modified，或叠加源/选项/转换器变化构成 conflict），无论旧默认、`--check` 还是 `--skip-up-to-date` 模式
- **THEN** 该输出 SHALL NOT 被静默覆盖：转换类模式 SHALL 跳过该文件并报告（人工编辑保留，显式覆盖旗标为唯一例外），`--check` SHALL 仅报告 conflict/output-modified 及两侧证据

#### Scenario: 下游只标需复核不判失效

- **WHEN** 源变化检测判定某 raw 产物过期
- **THEN** 对 materials/PRD 的影响 SHALL 仅表达为"需复核/候选受影响"清单（路径引用），SHALL NOT 自动判定下游业务结论失效；机械新鲜度 SHALL 与既有人工 `needs_review` 字段分离，SHALL NOT 合并为单一布尔

#### Scenario: 路由与 sheet 变化可盘点残留且不自动删除

- **WHEN** 多 sheet、sheet 删除/改名或 MD↔CSV 路由变化使旧输出不再属于新预期
- **THEN** 状态检查 SHALL 盘点出旧输出残留（orphan-outputs），SHALL NOT 自动删除未知来源或人工文件

### Requirement: 转换与回填入口 SHALL 在调用后端前拦截 Office 锁文件

convert_doc（单文件）、convert_excel（批量枚举）、extract_images（单文件与批量）与回填/批量导入入口 SHALL 在格式转换或外部依赖调用之前按输入文件 basename 前缀 `~$` 识别并排除 Office 锁文件。单文件模式遇锁文件 SHALL 以明确 skipped 语义处理，批量模式 SHALL 列为 skipped 且不使整批失败。既有 OOXML（PK）、PDF（%PDF-）、OLE2（D0CF11E0）魔数守卫 SHALL 保持。入口与体检 SHALL 对 NUL 字节、非法编码、伪 Markdown 给出带证据的诊断（抽样读取时 SHALL 标明抽样范围与计数口径），SHALL NOT 将短文档、空白文档一概判垃圾；历史遗留垃圾 SHALL 仅进入候选清单。

#### Scenario: 批量模式锁文件跳过不阻断

- **WHEN** 批量目录中存在 `~$xxx.xlsx` 锁文件
- **THEN** 该文件 SHALL 在调用 openpyxl/libreoffice 之前被列为 skipped，其余文件 SHALL 正常处理，批量 SHALL NOT 因锁文件崩溃

#### Scenario: 单文件模式锁文件明确跳过语义

- **WHEN** 单文件入口被显式传入 basename 以 `~$` 开头的文件
- **THEN** 入口 SHALL 以 skipped 语义（专用退出码或显式 skip 标记）退出并说明原因，SHALL NOT 报告为格式错误，SHALL NOT 调用 markitdown

#### Scenario: 前缀规则只作用于输入侧

- **WHEN** 某历史投影（raw/materials 产物）文件名**中部**含 `~$`（如 `..._~$1 招标管理培训.md`）
- **THEN** 体检 SHALL 将其作为无效投影候选线索报告（提示疑似锁文件投影），SHALL NOT 套用输入侧前缀拦截规则，SHALL NOT 据此单独判定该文件为垃圾

#### Scenario: 既有魔数守卫不弱化

- **WHEN** 非 `~$` 前缀但字节非法的文件（非 PK 的 .pptx/.docx、非 %PDF- 的 .pdf、OLE2 误标）进入转换入口
- **THEN** 既有魔数守卫 SHALL 照常拒绝并报错，行为与改动前一致

#### Scenario: NUL 抽样诊断如实标口径

- **WHEN** 诊断仅抽样读取文件字节（如前 64 KiB）
- **THEN** 诊断 SHALL 报告 sampled_bytes 与 sample_nul_count（标明抽样口径），SHALL NOT 冒充全文件 NUL 计数；全文件计数 SHALL 仅在完整读取时报告

#### Scenario: 历史垃圾只进候选清单

- **WHEN** 体检或守卫发现历史遗留的锁文件投影/无效投影
- **THEN** 该文件 SHALL 进入只读候选清单供 Owner 裁决，本轮 SHALL NOT 删除、移动或重写它

### Requirement: 图片/text-sparse/OCR 证据边界 SHALL 由唯一共享 reference 承载

material-importer SHALL 维护唯一的证据边界 reference 文件，承载图片、text-sparse 页与 OCR 投影的公共边界规则。检测三态 SHALL 沿用既有语义（发现 / none=成功无发现 / undetermined=检测失败），旧代际产物未检测 SHALL NOT 视为 none。OCR/图片投影 SHALL 保留原件哈希与页级锚点（source_sha256 + slide/页号）。text-sparse SHALL 仅为回看提示；OCR 文字 SHALL 仅作检索线索，未经原页核验 SHALL NOT 升级为已验证业务结论。图片缺失 SHALL NOT 被解释为原证据从未存在。消费方 SHALL 通过引用该 reference 连接规则，SHALL NOT 复制第二份规则文本。

#### Scenario: 旧代际未检测不等于 none

- **WHEN** v1 及更早转换的旧 raw 产物没有 text-sparse 检测行
- **THEN** 该页检测状态 SHALL 表达为未检测/旧代际，SHALL NOT 记为 none（成功无发现），也 SHALL NOT 触发回填或强制重转

#### Scenario: OCR 文本不自动升级业务结论

- **WHEN** OCR 投影文本含某业务名词
- **THEN** 该文本 SHALL 仅作页内检索线索，未经原页（原件或视觉回看）核验 SHALL NOT 升级为已验证业务结论

#### Scenario: 图片缺失时逐项核查锚点/转录/恢复定位

- **WHEN** 某图片引用指向 gitignore 的 `_media` 目录而 fresh clone 中不可得
- **THEN** 报告 SHALL 分别核查并表达源页锚点、可读语义转录、可用恢复定位三项各自的在/缺，SHALL NOT 预设它们已存在，SHALL NOT 判定为原证据不存在；Git/百度盘二进制归属 SHALL NOT 改变，SHALL NOT 批量纳入二进制

#### Scenario: fresh clone 仅文本时主张须三项齐备

- **WHEN** 重要业务主张所依赖的图片投影不可得
- **THEN** 该主张 SHALL 携带可读语义转录、源页锚点与可用恢复定位三项，且三项 SHALL 可分别核验在/缺；恢复定位 SHALL NOT 代替业务语义

#### Scenario: 装饰图、动画承载页与未回看页如实表达限制

- **WHEN** 被标记页的图片为跨页装饰图、信息由动画承载（无静态信息图）或尚未回看
- **THEN** 状态 SHALL 如实表达（如 not_scanned/图形态缺失），SHALL NOT 判"无信息"，text-sparse 信号 SHALL 保持回看提示语义且不自动触发 OCR

#### Scenario: 边界规则单点维护消费方引用

- **WHEN** 消费方 skill（如 competitor-product-analyzer）需要图片/text-sparse/OCR 边界规则
- **THEN** 其文档 SHALL 引用唯一共享 reference 的路径，SHALL NOT 内嵌第二份规则副本

### Requirement: 溯源工具 SHALL 维持多公司基座隔离

溯源体检、候选匹配与指纹记录 SHALL 以单一公司基座为隔离边界：匹配索引与指纹 SHALL 仅在当前基座内构建与适用，同名原件、同名输出或相同相对路径 SHALL NOT 跨公司匹配或复用。缺少或无效公司上下文 SHALL 沿用既有 resolver 的失败语义（无静默默认公司，SHALL NOT 回退 lanlnk）。来源声明解析后落在当前基座之外（绝对路径越界或符号链接解析进入其他公司）SHALL 默认报告边界问题，SHALL NOT 自动跟随读取另一公司。工具 SHALL 复用既有公司基座 resolver，SHALL NOT 内置硬编码公司清单。

#### Scenario: 同名原件不跨公司匹配

- **WHEN** 基座 A 体检时某未溯源产物在基座 A 内无候选，而基座 B 存在同格同名原件
- **THEN** 该产物 SHALL 保持 unresolved，工具 SHALL NOT 读取或匹配基座 B 的文件

#### Scenario: 相同相对路径的指纹不复用

- **WHEN** 两个公司基座存在相同相对路径的产物与 manifest
- **THEN** 一方的指纹/manifest/索引 SHALL NOT 适用、填充或覆盖另一方，报告中的身份 SHALL 按基座限定

#### Scenario: 缺少或无效公司上下文直接失败

- **WHEN** 未设置 COMPANY_BASE（及兼容变量）或所设路径未通过 `config/company.yaml` 校验
- **THEN** 工具 SHALL 以既有 resolver 的报错与非零码退出，SHALL NOT 回退任何默认公司路径

#### Scenario: 声明来源越界只报告不跟随

- **WHEN** 某产物的声明来源是基座外绝对路径，或为解析（含符号链接）后落在其他公司基座内的路径
- **THEN** 体检 SHALL 报告边界问题（boundary-violation）并停止该来源验证，SHALL NOT 读取目标文件内容

### Requirement: 体检报告 SHALL 分维表达且共享词表引用须有据

体检报告 SHALL 将来源性质（declared / inferred / none）、可访问性（accessible / missing / permission-denied / not-scanned 等）、哈希校验结果（match / mismatch / not-applicable / no-declared-hash / unknown-scope）作为独立字段分维表达，SHALL NOT 压缩为单一合并状态。共享 `evidence_state` 词表（source-reference.schema.json）SHALL 仅在语义确实满足时逐项引用，映射依据 SHALL 成文；SHALL NOT 建立无依据的一对一映射或新建第二套契约。纯读体检 SHALL NOT 要求安装 OCR、libreoffice 等可选后端；后端不可用 SHALL 仅影响真正依赖该后端的检查项（标记 backend-unavailable），其余检查 SHALL 照常完成。

#### Scenario: 缺原件分维表达

- **WHEN** 某声明来源的路径当前不存在
- **THEN** 报告 SHALL 记 来源性质=declared、可访问性=missing、哈希校验=not-applicable，SHALL NOT 合并为单一"缺失"状态而丢失其余两维信息

#### Scenario: 后端不可用只影响依赖项

- **WHEN** 宿主机未安装 libreoffice 或 OCR 后端
- **THEN** 纯读体检 SHALL 正常运行并完成全部不依赖该后端的检查，仅依赖项（如 .xls 重转换需求核查）SHALL 标 backend-unavailable，工具 SHALL NOT 整体失败

#### Scenario: 词表映射逐项有据

- **WHEN** 报告输出需与共享 evidence_state 词表对齐
- **THEN** 每一项映射 SHALL 在共享 reference 中给出语义依据（如 permission-denied→inaccessible），语义不满足的项 SHALL 保留本工具原生字段，SHALL NOT 强行映射

### Requirement: 网页抓取声明 SHALL 与本地来源分开识别

只读体检 SHALL 识别raw MD有界首部注释中的中文“来源 URL”“抓取时间”及source_url字段，并保留原字段、值、位置与声明性质。HTTP(S)来源 SHALL 不经文件路径解析且不访问网络，表达为declared、not-scanned、unknown-scope；SHALL NOT 因未联网而报告missing_source、missing_original或本地missing_hash，SHALL NOT 将声明抓取日期当作已核验历史事实。

#### Scenario: 既有中文抓取头无需改写

- **WHEN** raw MD首部注释含合法来源URL及抓取时间，正文或索引没有额外来源证据
- **THEN** 工具 SHALL 保留URL及抓取时间声明，标明external-url与未联网核验，不输出该项missing_source或missing_original，不写回MD

#### Scenario: 显式source中的网页URL不走文件系统

- **WHEN** source或source_path的完整值为合法HTTP(S)URL
- **THEN** 工具 SHALL 进入外部声明分支，不调用本地来源存在性或哈希检查，不报告该URL为缺失文件

#### Scenario: URL只在声明位置识别

- **WHEN** 正文、代码块或非首部注释中出现来源URL文字，或声明值不是合法HTTP(S)URL
- **THEN** 工具 SHALL 不将其自动认定为有效网页来源；对首部畸形或不支持协议的URL声明列出诊断并保留原值，不尝试网络访问或猜测文件路径

#### Scenario: 多项声明并存不被隐藏

- **WHEN** 本地source、网页URL及多条URL声明同时存在
- **THEN** 工具 SHALL 分别保留并校验本地来源和外部声明；相同URL可按去首尾空白后的精确值归组但保留全部位置，不同URL列声明冲突，不推断哪条更权威，也不以有效URL掩盖本地来源缺失或越界

#### Scenario: 外部声明仍是未核验发现

- **WHEN** 一项仅有网页来源声明且未联网核验
- **THEN** 工具 SHALL 在独立外部来源未核验清单中稳定排序输出，发现退出码为3；该项不自动生成本地来源回填候选，不自动升级recorded-at-conversion或verified-historical

### Requirement: 本地网页存档 SHALL 作为独立候选关系观察

只读体检 SHALL 仅在存在明确local_archive声明时读取该关系，按当前公司边界检查路径并分开记录声明值、可访问性及当前哈希。网页URL、存档身份与存档哈希语义 SHALL 不互相替代；当前哈希 SHALL 标明观察时点，不冒充抓取时或转换时哈希。无明确关联声明时 SHALL NOT 按同名文件自动建立存档关系或写入元数据。

#### Scenario: 当前存档存在与声明哈希分列

- **WHEN** 明确local_archive在本公司内存在且可读
- **THEN** 工具 SHALL 记录其当前路径、字节哈希和观察时点；如含local_archive_sha256_observed及观察时间，保留为既有声明并单列当前比对结果，哈希一致也只证明当前字节一致，不提升网页来源真实性

#### Scenario: 存档缺失或读取失败与网页来源区分

- **WHEN** 外部URL已声明但local_archive缺失、无权限或读取失败
- **THEN** 工具 SHALL 分别保留外部未核验状态与存档检查失败原因，列为发现，不将本地存档问题解释成网页原件不存在

#### Scenario: 存档越界不读取

- **WHEN** local_archive为跨公司路径、基座外绝对路径或越界符号链接
- **THEN** 工具 SHALL 报告边界问题且不读取目标内容，不复用其他公司的同名存档或哈希

#### Scenario: 无存档声明不推断匹配

- **WHEN** raw MD含来源URL，附近有同名HTML但没有明确local_archive声明
- **THEN** 工具 SHALL 仅报告已声明URL，不自动将同名HTML列为已确认存档，不新增写入或转换时溯源分类

#### Scenario: 旧本地来源行为与业务字节保留

- **WHEN** 新版工具扫描原有本地source记录、旧backfilled记录及两家公司同名素材
- **THEN** 原有本地分级、错误及公司隔离语义 SHALL 保留，全部公司业务文件字节不变；新增URL或存档声明不得隐藏原有本地缺口、伪造转换器签名或触发回填写入

#### Scenario: 存档多声明与孤立哈希不任意绑定

- **WHEN** 同一头部含不同local_archive路径，或只有游离的存档哈希而缺少可唯一绑定的路径
- **THEN** 工具 SHALL 保留全部声明并报告冲突或未解决绑定，不选择首条存档为权威，不将一个哈希静默应用于多条存档
