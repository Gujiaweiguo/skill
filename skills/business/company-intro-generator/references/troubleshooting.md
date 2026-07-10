# Troubleshooting

诊断流程索引。按症状查找，按根因修复。

---

## 目录/分节页项数或选中状态不一致

**症状**：复用参考 PPT 后，目录页（P02）和分节页（P10/P37/P56）出现以下问题之一：
- 项数不一致（有的页 3 项，有的页 4 项）
- 选中状态不符合分节页语义（第 N 章分节页应高亮第 N 项，实际高亮了第 1 项）
- 新增项的字体颜色/加粗/下划线和未选中项不一致

**根因**：参考 PPT 原本存在设计 bug——
- P02/P10/P37 只有 3 项目录（缺第 4 项"项目实施服务建设方案"），P56 才有 4 项
- P37/P56 高亮了第 1 项，不符合分节页语义

**诊断步骤**：

1. **提取所有目录/分节页的项数和选中状态**：
   ```python
   from pptx import Presentation
   prs = Presentation(target)
   for page_idx in [1, 9, 36, 55]:  # P02, P10, P37, P56
       slide = prs.slides[page_idx]
       texts = [s.text_frame.text.strip() for s in slide.shapes if s.has_text_frame and s.text_frame.text.strip()]
       print(f"P{page_idx+1:02d} ({len(texts)} 项): {texts}")
   ```

2. **检查项数**：4 个目录/分节页应该都是 4 项（1.公私域数字营销规划 / 2.会员数字营销解决方案 / 3.公司简介与客户案例 / 4.项目实施服务建设方案）

3. **检查选中状态**：
   - P02 主目录页：可高亮第 1 项（开场）
   - P10 第 1 章后分节页：应高亮第 2 项
   - P37 第 2 章后分节页：应高亮第 3 项
   - P56 第 3 章后分节页：应高亮第 4 项

**修复**：

#### 补第 4 项（从 P56 深拷贝）

```python
from copy import deepcopy
from pptx.util import Inches
from pptx.oxml.ns import qn

prs = Presentation(target)
template_shape = prs.slides[55].shapes[3]  # P56 的第4项作为模板

for page_idx in [1, 9, 36]:  # P02, P10, P37
    target_slide = prs.slides[page_idx]
    # 检查是否已有第4项
    has_item4 = any("4." in s.text_frame.text and "项目实施" in s.text_frame.text
                    for s in target_slide.shapes if s.has_text_frame)
    if has_item4:
        continue
    # 深拷贝 XML
    new_elem = deepcopy(template_shape._element)
    # 修改位置（延续前3项间距）
    xfrm_off = new_elem.find('.//' + qn('a:off'))
    xfrm_off.set('x', str(Inches(5.46)))  # 和前3项 left 对齐
    xfrm_off.set('y', str(Inches(5.77)))  # top = 前3项最后一项 top + 1.28
    # 修改尺寸
    xfrm_ext = new_elem.find('.//' + qn('a:ext'))
    xfrm_ext.set('cx', str(Inches(5.86)))
    xfrm_ext.set('cy', str(Inches(0.71)))
    # 重新生成 shape ID
    cNvPr = new_elem.find('.//' + qn('p:cNvPr'))
    existing_ids = [s.shape_id for s in target_slide.shapes]
    cNvPr.set('id', str(max(existing_ids) + 1))
    # 添加到 spTree
    target_slide.shapes._spTree.append(new_elem)

prs.save(target)
```

#### 修改选中状态（深拷贝 rPr 模板）

```python
from copy import deepcopy
from pptx.oxml.ns import qn

prs = Presentation(target)

# 获取格式模板 rPr
# 选中格式：从 P02 第1项（sz=3600, b=1, u=sng, 蓝色渐变 #2C5DE6→#6F92F3）
selected_rPr = deepcopy(prs.slides[1].shapes[0].text_frame.paragraphs[0].runs[0]._r.find(qn('a:rPr')))
# 未选中格式：从 P02 第3项（schemeClr=tx1）
unselected_rPr = deepcopy(prs.slides[1].shapes[2].text_frame.paragraphs[0].runs[0]._r.find(qn('a:rPr')))

def apply_rPr(run, rPr_template):
    r_elem = run._r
    old_rPr = r_elem.find(qn('a:rPr'))
    new_rPr = deepcopy(rPr_template)
    if old_rPr is not None:
        r_elem.replace(old_rPr, new_rPr)
    else:
        r_elem.insert(0, new_rPr)

# 把 P56 第4项改成选中状态
for shape in prs.slides[55].shapes:
    if shape.has_text_frame and "4." in shape.text_frame.text and "项目实施" in shape.text_frame.text:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                apply_rPr(run, selected_rPr)

# 把 P02/P10/P37 第4项改成未选中状态
for page_idx in [1, 9, 36]:
    for shape in prs.slides[page_idx].shapes:
        if shape.has_text_frame and "4." in shape.text_frame.text and "项目实施" in shape.text_frame.text:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    apply_rPr(run, unselected_rPr)

prs.save(target)
```

**验证**：用 PowerPoint/Keynote 打开 P02/P10/P37/P56 目视确认，选中项应有蓝色渐变文字+下划线，未选中项应为黑色无下划线。

---

## 封面副标题或日期修改失败

**症状**：用 python-pptx 修改封面副标题后，重新打开 PPT 发现文字没变。

**诊断步骤**：

1. **检查 shape 索引**：参考 PPT P01 的 shape 结构是：
   - Shape 0：主标题（如"商圈会员数字营销解决方案"）
   - Shape 1：副标题（如"科技赋能新商业..."）
   - Shape 2：日期 + 公司名（多 run，run[0]=日期，run[1]=公司名）
   - Shape 3：图片

2. **检查 run 结构**：每个 shape 的 text_frame 可能有多个 paragraph，每个 paragraph 可能有多个 run。修改时要精确定位到具体的 run。

**修复**：
```python
prs = Presentation(target)
cover = prs.slides[0]
# 副标题
cover.shapes[1].text_frame.paragraphs[0].runs[0].text = "{客户名}方案汇报"
# 日期（Shape 2 的第1个 run）
cover.shapes[2].text_frame.paragraphs[0].runs[0].text = "{YYYY.MM}"
prs.save(target)
```

---

## 客户案例已在参考 PPT 中，却做了重复定制页

**症状**：case_matcher 匹配到某客户（如粤海/时尚天河/金沙汇），做了定制案例页，结果发现参考 PPT 里已经有这个案例的详情页。

**根因**：case_matcher 只搜索 `$MATERIALS_DIR/04-cases/`，不知道参考 PPT 已经覆盖了哪些客户。

**修复**：case_matcher 跑完后，**先查 `references/reference-ppt-index.md` 的"已覆盖的客户案例"清单**（13 家），如果匹配到的客户在清单中，直接复用参考 PPT 对应页，不做定制页。

参考 PPT 已覆盖的客户：时尚天河(P43)、广州城投/金沙汇(P44)、粤海(P45)、宝能(P46)、益田(P47)、岁宝(P48)、富康城(P49)、喜街(P50)、世欧(P51)、骑楼老街(P52)、南宁轨交(P53)、彩生活(P54)、高德置地(P55)。

---

## 客户 Logo 墙做了重复定制页

**症状**：模式 A 或模式 D 场景下，做了一页客户 Logo 墙定制页，结果发现参考 PPT P42 已经是 26 张客户 Logo 墙。

**根因**：参考 PPT P42 [图:26] 就是完整的客户 Logo 墙，覆盖了蓝联所有主要标杆客户。

**修复**：**禁止做客户 Logo 墙定制页**。模式 A 直接复用 P42；模式 D 的"P6 标杆客户 Logo 墙"也是复用 P42 或保留模板原页（`incoming/正祥选型方案/` 目录下的参考 PPT）。

---

## ppt-master .venv 不存在，compile.py 无法运行

**症状**：执行 `uv run compile.py` 报错，或提示找不到 python-pptx。

**根因**：ppt-master skill 的虚拟环境未初始化。

**修复**：
```bash
cd /opt/code/skill/skills/ppt/ppt-master && uv sync
```
然后再执行 compile.py。

**绕过方案**：如果只是改封面或少量页面，走路径 1（直接复用 + python-pptx 编辑），不需要 compile.py。用 `uv run --with python-pptx python3 ...` 临时安装 python-pptx 即可。
