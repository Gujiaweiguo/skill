# Troubleshooting

诊断流程索引。按症状查找，按根因修复。

---

## doc_map：表格行没有提取到

**症状**：`parsed/current-doc-map.json` 中 feature 数量偏少，某些 xlsx 来源文档的表格行丢失。

**诊断步骤**：

1. **检查 `_TABLE_ROW` 正则是否带 `re.MULTILINE`**
   - 历史根因：缺少 `re.MULTILINE` 导致 `^$` 锚点不匹配跨行，整份文档一行都提取不到。
   - 修复：`re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|", re.MULTILINE)`

2. **检查表格 cell 是否被 markitdown 转成 int**
   - markitdown 可能将 "1" 转成 int 1，导致正则匹配失败。
   - 修复：`_TABLE_ROW` 的 group 总是返回 str，但如果上游 cell 是 int，需要 `_stringify_table` 统一转 str。

3. **检查 `_is_noise_heading` 是否误判**
   - `_NOISE_HEADING` 会过滤纯数字行（`\d+\.?\d*$`）、编号行（`[（(][一二三四五六七八九十\d]+[)）]`）。
   - 如果功能名恰好是纯数字或以编号开头，会被误杀。

---

## doc_map：图片证据全部挂到同一个标题

**症状**：某个标题下挂了 50+ 张图片，其他标题没有图片。

**诊断步骤**：

1. **检查 `_nearby_image_refs` 的 `span_end` 计算**
   - `span_end = text.find("\n#", heading_pos + 1)` 找下一个 `#` 标题。
   - 如果文档纯用 `**bold**` 当标题（如万达文档），`text.find("\n#")` 返回 -1，`span_end` 到文件末尾 → 所有图片都挂在第一个 bold 标题下。

2. **检查 `_collect_image_refs` 的 `seen` 去重**
   - `seen` set 用 `"image:{ref_str}"` 做 key，同一图片不应该重复出现。
   - 如果同一图片在不同 feature 里重复，检查 ref_str 是否因 resolve 路径不同而绕过去重。

---

## doc_map：`_media/` 目录的图片找不到

**症状**：`raw/foo_media/` 目录存在且有图片，但 doc_map 没提取到任何图片证据。

**诊断步骤**：

1. **检查 stem 匹配**
   - `foo.docx.md` → `md_path.stem` = `"foo.docx"` → media_dir = `"foo.docx_media"`
   - 但实际目录名可能是 `"foo_media"`（markitdown 去掉了 .docx 后缀）
   - 修复：双候选 `[md_path.stem, md_path.stem.rsplit(".", 1)[0]]` → `["foo.docx", "foo"]`

2. **检查 docs_root resolve**
    - `resolved.relative_to(docs_root)` 如果 docs_root 没 resolve 会抛 ValueError
    - 修复：函数开头 `docs_root = docs_root.resolve()`

---

## doc_map：合同条款分类把普通标题也吸进来了

**症状**：`需求清单.md` 里大量出现 `合同条款组` / `合同字段`，但实际只是“合同模板管理”“结算周期名称”这类派生标题。

**根因**：`_classify_requirement_kind()` 以前按“标题包含合同相关词”做宽松匹配，导致只要正文提到“合同”就会被误判成条款组。

**修复**：

1. **只对精确章节标题启用条款组**
   - 例如：`结算周期`、`账款条款`、`进场条款`、`免租条款`、`预存款条款`、`自定义条款`、`合同模板`、`合同保存草稿`。

2. **派生标题保持原样**
   - 例如：`合同模板管理`、`结算周期名称`、`合同编号`、`合同附件`（若不是独立章节）不要再被提升成条款组。

3. **必要时先看正文上下文**
   - 只有标题本身就是条款章节，且附近正文在描述条款字段/配置项时，才补充 `clause-path`。

---

## doc_map：多来源合同资料合并后海鼎没有压住其他来源

**症状**：合同模块里相同条款/字段在不同来源都出现，但输出里看起来像是平均融合，海鼎的章节骨架不够稳定。

**根因**：合并阶段如果仍按“深度更大就覆盖”处理，其他来源会把海鼎的结构冲掉。

**修复**：

1. **来源优先级固定**
   - 海鼎（`02-competitors/海鼎`）最高。
   - 当前产品基线次之。
   - 客户需求和其他竞品只做补充。

2. **去重时保留更强结构**
   - 同名条款冲突时保留海鼎条目，并把其他来源的证据合并进去。

3. **不要把合并理解成平均值**
   - 合同模块以海鼎骨架为模板，其他来源是补丁，不是同权输入。

4. **华侨城、锦和属于海鼎家族变体**
   - 这两类资料虽然会出现在客户目录里，但合同/蓝图结构仍和海鼎同源（锦和蓝图由"上海海鼎信息科技有限公司"编写）。
   - 处理时按"海鼎家族"优先，不要把它们当成全新模板族。
   - 代码中 `_source_family()` 扫描整个路径段（不限于 `/02-competitors/`），所以 `01-customer-requirements/上海锦和/` 和 `01-customer-requirements/深圳华侨城/` 也能命中家族优先级。

5. **家族变体标题归一**
   - 三家文档风格不同：海鼎用"结算周期""账款条款"，锦和用"固定租金计算方式""进场管理业务说明"，华侨城用表格行"正式合同""结算管理"。
   - `_FAMILY_CLAUSE_ALIASES` 把变体标题精确映射到海鼎标准条款名，使三家在合并时自然对齐到同一骨架。

---

## reconcile：所有 capability 都带 "spec has no doc evidence yet" gap

**症状**：明明 doc_map 有匹配的 feature，但 reconcile 结果里每个 capability 都有这个 gap。

**诊断步骤**：

1. **检查 `normalized_term` 是否和 spec ID 一致**
   - term-aliases.yaml 必须把中文 heading 映射到**英文 spec ID**（如 `CONTRACT_MANAGEMENT`）。
   - 如果映射缺失，doc feature 的 `normalized_term` 是中文（如"合同管理"），spec ID 是英文（`CONTRACT_MANAGEMENT`），`by_id[term]` 匹配失败。
   - 修复：在 term-aliases.yaml 补充映射。

2. **检查 `stale_markers` 是否包含过时 gap 文本**
   ```python
   stale_markers = ("spec has no doc evidence yet", "doc gap: code has it but doc does not mention it")
   ```
   - 如果改了初始 gap 文本，这里也要同步更新。

---

## reconcile：unmatched 需求全是噪音

**症状**：`_add_unmatched_customer_requirements` 产出的 missing capabilities 里出现编号、元数据、公司名等垃圾。

**诊断步骤**：

1. **检查 noise 正则**
   - `_add_unmatched_customer_requirements` 里的 noise 正则过滤纯数字、编号（`FW01`、`GC01`）、公司名（`.*公司`）、通用描述（`.*管理$`）等。
   - 新出现的噪音模式需要加到正则里。

2. **检查 depth 过滤**
   - `depth > 3` 的 feature 被跳过。如果客户文档层级很深，调高阈值。
   - 但调高阈值会引入更多噪音，需要平衡。

3. **常见噪音示例**（已过滤）
   - 纯编号：`FW01`、`L02-01`、`GC-003`
   - 元数据：`文档编号`、`版本`、`密级`、`修改原因`
   - 公司名：`某某科技`、`某某集团`
   - 通用章节：`前言`、`目录`、`附录`、`审核`

---

## reconcile：unmatched 需求超过 80 条被截断

**症状**：客户实际提了 100+ 个不同功能点，但 missing 只显示 80 条。

**诊断步骤**：

1. **封顶逻辑在 `sorted_terms[:80]`**
   - 排序：深度优先（depth 1-2 优先）+ 客户数倒序。
   - 如果想看全部，临时改成 `sorted_terms` 或调大阈值。
   - 但超过 80 条会导致 PRD 过长且充满噪音，80 是经验值。

---

## word_export：`ModuleNotFoundError: docx`

**症状**：word_export 调用 word-master 时报 `ModuleNotFoundError: No module named 'docx'`。

**诊断步骤**：

1. **不要直接用 `python3` 调用 word-master**
   - word-master 有自己的 `.venv`，直接调用会用错误的 venv。
   - 正确调用：
     ```python
     subprocess.run(
         ["uv", "run", "python", "-m", "src.main", content_path, "--output", output],
         cwd=word_master_dir,
     )
     ```

2. **检查 word-master 目录是否 `uv sync` 过**
   - `cd skills/word/word-master && uv sync`

---

## word_export：内容包路径找不到

**症状**：word-master subprocess 报 `FileNotFoundError: xxx.word-content.md`。

**诊断步骤**：

1. **内容包路径必须是绝对路径**
   - `render_docx` 用 `content_path.resolve()` 转绝对路径再传给 subprocess。
   - 原因：subprocess 的 `cwd` 切换到 word-master 目录后，相对路径失效。

---

## word_export：`int` object has no attribute `startswith`

**症状**：构建 `.word-content.md` 时报 int 相关 AttributeError。

**诊断步骤**：

1. **检查表格 cell 类型**
   - markitdown 可能将数字 cell 转成 int。
   - 修复：`_stringify_table` 函数统一把所有 cell 转成 str。

---

## 全局：`pip install` 安装包失败或被纠正

**症状**：用 `pip install xxx` 安装包，被用户纠正。

**根因**：本项目强制使用 `uv`，不允许 `pip` 或直接 `python3`。

**正确做法**：
```bash
cd skills/business/product-prd-generator && uv sync
cd skills/word/word-master && uv sync
```

添加新依赖：`uv add xxx`（不要 `pip install`）。

---

## 需求提取：总需求数突然暴增或暴跌

**症状**：重跑后需求数从 ~5000 变成 ~50 或从 ~50 变成 ~5000。

**诊断步骤**：

1. **检查 dedup key**：`extract()` 中 requirements 的 dedup key 必须是 `(normalized_term, source_file)`，**不是 `normalized_term` 单独**。宽泛 alias 会把不同 heading 归一化到同一 term，单 key dedup 会坍缩到只剩 ~1 条/能力。

2. **检查 alias 长度排序**：`_normalize_term` 必须按 alias 长度降序匹配。不排序会导致 "合同"（2字）抢匹配 "合同模板"（4字）。

---

## 需求提取：噪音太多（图片路径、table 残留、JSON 块）

**症状**：需求清单里出现 `| ---`、`![image](data:image/png;base64,...)`、`{"data": {...}}` 等。

**诊断步骤**：

1. **检查 `_is_noise_text`**：这个函数过滤 table artifacts（`^\|`）、image paths（`!\[`）、JSON blocks（`^\{`）、sentence-like text（含 `。！？`）。如果遗漏新噪音类型，在这里加 pattern。

---

## Word 导出：`ValueError: All strings must be XML compatible`

**症状**：word-master 报 control character 错误。

**根因**：`nearby_text` 从 markdown 提取，可能含 `\x00-\x1f` 控制字符。

**修复**：`word_export.py` 的 `_sanitize` 函数用 `re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)` 清除。所有写入 docx 的文本都必须过 `_sanitize`。

---

## 匹配率：两阶段匹配没有提升

**症状**：实现两阶段匹配后，匹配率持平或微降。

**这是正常的。** 两阶段匹配提升**精确度**（匹配到正确业务域），不提升**召回率**。召回率瓶颈在 ontology 术语覆盖率（当前 482 术语）。提升匹配率的唯一路径是扩 ontology 术语。

---

## Ontology 文件缺失：匹配率从 17% 降到 12%

**症状**：匹配率突然从 17% 降到 ~12%。

**根因**：`$LANLNK_BASE/knowledge/business-ontology.yaml` 文件缺失或路径错误。

**诊断步骤**：
1. 检查环境变量：`echo $LANLNK_BASE`
2. 检查文件存在：`ls $LANLNK_BASE/knowledge/business-ontology.yaml`
3. doc_map 的 `_load_aliases` 会优雅退化到纯 term-aliases 匹配（不报错），但匹配率降低。

---

## YAML OrderedDict 序列化导致 yaml.safe_load 报错

**症状**：`yaml.safe_load()` 报 `ConstructorError: could not determine a constructor for the tag 'tag:yaml.org,2002:python/object/apply:collections.OrderedDict'`。

**根因**：Python 代码中用 `OrderedDict` 构建数据结构，然后 `yaml.dump()` 写入文件时序列化为 `!!python/object/apply:collections.OrderedDict` tag。`yaml.safe_load()` 不认识这个 Python 特有 tag。

**修复（写入侧——预防）**：

**永远不要把 OrderedDict 直接 yaml.dump 到文件**。先转普通 dict：

```python
# WRONG
from collections import OrderedDict
data = OrderedDict([("a", 1), ("b", 2)])
yaml.dump(data, f)  # 写入 !!python/object/apply:collections.OrderedDict

# CORRECT
data = {"a": 1, "b": 2}  # Python 3.7+ dict 保序
yaml.dump(data, f)
```

如果必须用 OrderedDict 构建逻辑，dump 前递归转换：

```python
def to_plain(obj):
    if hasattr(obj, 'items'):
        return {k: to_plain(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_plain(i) for i in obj]
    return obj

yaml.dump(to_plain(data), f)
```

**修复（读取侧——恢复）**：

如果文件已经被污染，用 `yaml.unsafe_load()` 读取，转 dict 后重写：

```python
data = yaml.unsafe_load(open(path, encoding='utf-8'))
data = to_plain(data)  # 递归转普通 dict
yaml.dump(data, open(path, 'w', encoding='utf-8'), ...)
```

---

## YAML 重命名后正文残留旧名称

**症状**：YAML 中 entity key 已改（如 `租赁条件 → 条件报批`），但 PRD 正文里多处仍显示旧名称。

**根因**：`dict[new_key] = dict.pop(old_key)` 只改了 key，**不改 value 中的字符串引用**。旧名称出现在：document name、field desc、constraints、sources、scenario、workflow 等 string 字段中。

**修复**：

重命名时必须递归替换所有 string value：

```python
def replace_in_dict(d, old, new):
    if isinstance(d, dict):
        return {k.replace(old, new) if isinstance(k, str) else k: replace_in_dict(v, old, new)
                for k, v in d.items()}
    elif isinstance(d, list):
        return [replace_in_dict(i, old, new) for i in d]
    elif isinstance(d, str):
        return d.replace(old, new)
    return d

mfs = replace_in_dict(mfs, "租赁条件", "条件报批")
```

**验证**：替换后全文搜索确认零残留（排除 codebase-features.json，那是代码扫描结果反映实际代码用词）。

---

## field-specs YAML 丢失实体

**症状**：PRD 渲染后某些 entity 变成空壳（只有 `- ✅ capability` 一行），之前有完整字段定义。

**根因**：
1. OrderedDict 序列化失败（见上条）导致 yaml.safe_load 无法读取文件→部分数据丢失
2. Python 脚本中 `mfs["招商管理"] = dict(new_zs)` 覆盖时遗漏了某些 key

**诊断步骤**：

```python
import yaml
mfs = yaml.safe_load(open('module-field-specs.yaml', encoding='utf-8'))
for mod in mfs:
    for k, v in mfs[mod].items():
        docs = v.get('documents', {}) if isinstance(v, dict) else {}
        if not docs:
            print(f"  ❌ {mod}/{k}: 空")
```

**预防**：每次大改 YAML 后运行此检查。entity 有 sub_function 但无 documents = 空 = 误导用户。
