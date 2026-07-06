# Page Extraction Strategy — 页面字段抽取策略

本文件定义 P2 阶段（demo 运行时探测）的页面字段抽取方法。SKILL.md 的 P2 阶段强制遵循此策略。

## 核心原则

**先静态、后动态、最后手动**。三种模式按效率降级：

| 模式 | 每页耗时 | 字段完整度 | 适用场景 |
|---|---|---|---|
| **A. 同源 fetch + 正则解析** | ~50ms × N 页（一次 evaluate 批量）| 中（仅 HTML 静态部分）| 服务器渲染 + layui/jQuery 模板站点 |
| **B. addTab + iframe.contentDocument 读取** | ~3-5s × N 页（必须串行）| 高（含 JS 渲染部分）| Vue/React SPA + layui 等动态渲染 |
| **C. Playwright snapshot** | ~5-10s × N 页 | 高（含交互态）| 需要采集交互态（弹窗/dropdown）|

**默认从 A 开始**，A 拿不到关键字段（如 labels=[] / buttons=[]）才升级到 B，B 还不够才用 C。

## A. 同源 fetch + 正则解析（推荐起点）

### 适用条件

- 目标站点已登录态在 cookie 里（同源 fetch 自动带 cookie）
- 页面 HTML 含字段名/按钮文本（即使是 JS 模板，HTML 里通常也有 `<label>` `<th>` `<button>` `<a lay-event>` 标签）
- 不需要交互态（弹窗未打开的字段拿不到）

### 实现模板

```javascript
async () => {
  const targets = [
    {top:'模块名', text:'页面名', url:'相对路径?v=61'},
    // ... 批量列表
  ];
  const out = [];
  for (const t of targets) {
    try {
      const r = await fetch(t.url);
      const html = await r.text();
      const cnTexts = new Set();
      // 抽取所有 2-15 字中文词
      const re = /[\u4e00-\u9fa5]{2,15}/g;
      const matches = html.match(re) || [];
      matches.forEach(m => {
        if (![t.text,'解析失败','服务器','加载中','layui','数据表格','操作',
              '提示','确定','取消','查询','重置','保存成功'].includes(m))
          cnTexts.add(m);
      });
      // 抽取按钮（lay-event 是 layui 的按钮事件标识）
      const buttons = [];
      const btnRe = /<a[^>]*lay-event=["']([^"']+)["'][^>]*>([^<]{1,15})</g;
      let m;
      while ((m = btnRe.exec(html)) !== null) buttons.push(m[2]);
      out.push({top:t.top, page:t.text,
                fields:[...cnTexts].slice(0, 60),
                buttons:[...new Set(buttons)].slice(0, 30)});
    } catch(e) {
      out.push({top:t.top, page:t.text, error:e.message});
    }
  }
  return JSON.stringify(out, null, 2);
}
```

### 注意事项

- **URL 列表来源**：先从二级菜单的 `<a onclick>` 提取，正则 `/addTab\(['"]([^'"]+)/` 拿到 URL
- **fetch 是同源的**：在浏览器 evaluate 里 fetch 会自动带 cookie，不需要额外配置
- **DOMParser 解析更精准但更慢**：`new DOMParser().parseFromString(html, 'text/html')` 然后用 `querySelector`，比纯正则更准但慢 3-5 倍。批量抓取时优先纯正则，单页深抓时用 DOMParser
- **layui 站点的字段在 JS 字符串里**：layui 的 `cols: [[...]]` 表格列定义是 JS 字符串，HTML 静态解析能拿到（因为整段 JS 在 `<script>` 里），但需要正则提取
- **去噪关键词**：固定过滤词列表（'解析失败'/'服务器'/'加载中'/'layui'/'数据表格'/'操作'/'提示'/'确定'/'取消'/'查询'/'重置'/'保存成功'/'绑定选择数据失败'）

### 失败信号

- `fields: []` 或 `fields.length < 3` → 升级到模式 B
- `error: 'Failed to fetch'` → 跨域/会话失效，检查登录态
- 字段全是噪音（按钮/提示文本）→ 该页面是纯 JS 渲染，升级到模式 B

## B. addTab + iframe.contentDocument 读取

### 适用条件

- 站点用 addTab/iframe 模式加载内容页（每个二级菜单点击后在主区域创建 iframe）
- 同源（iframe 跨域访问 contentDocument 会被浏览器拒绝）
- 模式 A 静态解析失败

### 实现模板

```javascript
async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // 1. 切换顶级菜单，加载二级菜单
  if (typeof CreateLeftNav === 'function') {
    CreateLeftNav('模块名');
    await sleep(2000);
  }
  // 2. 调用 addTab 打开页面
  if (typeof addTab === 'function') {
    addTab('相对路径', '页面名');
    await sleep(3000);
  }
  // 3. 等 iframe 加载完成
  const iframe = document.querySelector('iframe');
  if (!iframe || !iframe.contentDocument) return 'no iframe access';
  const idoc = iframe.contentDocument;
  // 4. 提取字段
  const labels = Array.from(idoc.querySelectorAll('label, .layui-form-label, th'))
    .map(e => (e.innerText||'').trim()).filter(t => t && t.length<25);
  const placeholders = Array.from(idoc.querySelectorAll('input,textarea,select'))
    .map(i => i.placeholder||'').filter(t => t && t.length<25);
  const buttons = Array.from(idoc.querySelectorAll('button, .layui-btn, a[lay-event], a[onclick]'))
    .map(b => (b.innerText||'').trim()).filter(t => t && t.length<15);
  return JSON.stringify({labels:[...new Set(labels)], placeholders, buttons}, null, 2);
}
```

### ⚠️ iframe 内 evaluate 的高风险操作

**禁止**：在 `iframe.contentDocument` 里调用 `element.click()`。click 可能触发跳转或打开新窗口，导致 **整个 Playwright page 的 URL 被重置为 about:blank**，会话失效。

**实测**：在合同管理页面 iframe 里调用 `subA.click()`（子菜单链接）后，page URL 变成 `about:blank`，需要重新 `browser_navigate` 到 Main.html 才能恢复。

**正确做法**：iframe 里只读 DOM（textContent/innerHTML/querySelectorAll），交互操作（click/fill）放回主 document 上下文。

### 失败信号

- `no iframe access` → 跨域，无法用本模式
- `iframe.contentDocument` 抛错 → 同源策略阻止
- iframe 加载超过 5s → sleep 不够，加长到 5-8s

## C. Playwright snapshot（兜底）

### 适用条件

- A 和 B 都失败
- 需要采集交互态（点开 modal 后的字段、dropdown 展开后的选项）

### 实现方式

按 doc-generator 的 `screenshot-plan.json` 模式：

1. 主上下文 click 子菜单 → 等 iframe 加载 → `browser_snapshot` 取整个 page（含 iframe 内的元素）
2. snapshot 用 `ref=eXXX` 定位元素，再做后续 click/fill
3. 关键节点 `browser_take_screenshot`

**性能最差**：每页 5-10s（snapshot 本身就慢，加上 click 等待），仅用于精抓重点页面（如 P0 必补的 3-5 张报表）。

## 菜单加载机制探测

不同站点的左侧菜单加载机制不同，**必须先探测 `<a>` 标签的 onclick handler** 才能选择正确的菜单收集策略。

### 4 种典型机制

| 机制 | onclick 模式 | 菜单 DOM 行为 | 收集策略 |
|---|---|---|---|
| **传统 accordion** | `onclick=""`（无）或 CSS hover | dd 永远在 DOM 里，只是 CSS 隐藏 | 直接 `querySelectorAll('li dd')` |
| **CreateLeftNav 替换式** | `onclick="CreateLeftNav('模块名')"` | 点击后**整体替换左侧菜单容器**的 innerHTML | 必须每次点击+sleep+读 divSide |
| **异步加载子菜单** | `onclick="loadSubMenu('id')"` | dd 不在 DOM 里，点击后异步插入 | 点击+sleep+读 |
| **SPA 路由切换** | `onclick="router.push('/path')"` | 整个 Vue/React 重新渲染 | 用 Playwright snapshot |

### 探测脚本

```javascript
() => {
  const topMenus = Array.from(document.querySelectorAll('a'))
    .filter(a => {
      const txt = (a.innerText||'').trim();
      const onclick = a.getAttribute('onclick') || '';
      return txt && txt.length < 30 && onclick && !txt.includes('llkj');
    })
    .map(a => ({text: a.innerText.trim(), onclick: a.getAttribute('onclick').substring(0, 100)}));
  return JSON.stringify(topMenus.slice(0, 15), null, 2);
}
```

**判定**：
- 看到 `CreateLeftNav(...)` → 替换式，需要点+sleep+读
- 看到 `addTab(...)` → 子菜单是 addTab 加载 iframe
- 看到 `loadSubMenu(...)` → 异步加载
- 没有 onclick 但 a 在 li 里 → 传统 accordion

### 实战经验（旗茂 BS 系统）

旗茂用 layui + iframe 模式：

- **顶级菜单**：`onclick="CreateLeftNav('合同管理')"` → 替换整个 `#divSide` 容器
- **二级菜单**：`onclick="addTab('Contract/LayuiMall/ContractNew/ContractList.html', '合同管理')"` → 在主区域创建 iframe
- **accordion 行为**：连续点击多个顶级菜单时，前一个会被折叠，但被折叠菜单的 dd 不在 DOM 里（与"传统 accordion dd 永远在 DOM"不同）

**正确收集流程**：
```javascript
async () => {
  const targets = ['系统管理','基础资料','合同管理','财务管理','营运管理','移动商管','物业管理','报表管理'];
  const out = {};
  for (const t of targets) {
    const a = Array.from(document.querySelectorAll('a'))
      .find(x => (x.innerText||'').trim() === t && x.getAttribute('onclick')?.includes('CreateLeftNav'));
    if (!a) continue;
    a.click();
    await sleep(2000);  // 必须等子菜单异步加载
    const side = document.getElementById('divSide');
    const dds = [];
    side.querySelectorAll('dd').forEach(dd => {
      const t = (dd.innerText||'').trim();
      if (t && t.length < 30) dds.push(t);
    });
    out[t] = [...new Set(dds)];
  }
  return JSON.stringify(out, null, 2);
}
```

**坑**：sleep 时间不够会拿到空数组；accordion 折叠后用 `closest('li')` 找不到 dd，必须用 `getElementById('divSide')` 直接定位容器。

## 推荐执行顺序（P2 阶段）

```
P2.1 探测菜单加载机制（看 onclick handler）
    ↓
P2.2 收集全部顶级+二级菜单（按机制选脚本）
    ↓
P2.3 提取所有二级菜单的 URL（addTab 参数）
    ↓
P2.4 模式 A 批量 fetch + 正则解析（一次 evaluate 抓 10-20 页）
    ↓ 标记失败的页面
P2.5 模式 B 对失败页 addTab+iframe 深抓（精抓重点页）
    ↓ 仍有失败
P2.6 模式 C Playwright snapshot 兜底（仅 P0 必补报表/关键表单）
    ↓
P2.7 写 runtime-probe.json + imgs/
```

**预算控制**：模式 A 每页 50ms，B 每页 3-5s，C 每页 5-10s。8 模块 × 平均 10 页 = 80 页，全部用 A 仅 4s，全部用 B 需 4-7 分钟，全部用 C 需 7-13 分钟。**永远从 A 开始**。

## 与 doc-generator 的边界

本 skill **不直接调用** doc-generator。但 P2 的策略借鉴 doc-generator 的运行时探测原则：

- 文本/角色 locator（不用 CSS/XPath）
- 单页失败容忍（一页 timeout 不阻塞整体）
- 失败页记入 manifest，标注原因

差异：doc-generator 探测的是"自家应用"（用户给的源码 + dev server），本 skill 探测的是"竞品应用"（远程站点 + 授权账号）。所以本 skill 多了合规边界（见 `safety-and-ethics.md`）。
