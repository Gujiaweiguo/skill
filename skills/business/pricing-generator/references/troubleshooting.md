# pricing-generator 排障手册

> 本文件记录 pricing-generator 的非显而易见行为。跨 skill 通用规则见 `AGENTS.md`，不在此重复。

## 人天单价差额（成本 vs 报价）

两个 skill 用不同的人天单价，**差额是利润，不是 bug**：

| skill | 单价 | 用途 |
|---|---|---|
| requirement-evaluator | 1,500 元/天 | **成本基准**估算（二开要多少成本） |
| pricing-generator | 2,000 元/天 | **报价单价**（面客） |

差额 500 元/天 = 毛利空间。调价时两边联动，不要只改一边。

## P0.3 前置 requirement-evaluator 检测

P0.3 检测是否存在前置 requirement-evaluator 输出（二开清单）。**缺失则自动先跑 requirement-evaluator**。

- 症状：用户直接调 pricing-generator 却发现先触发了 requirement-evaluator 流程——这是设计行为，不是误触发
- 跳过条件：已存在 requirement-evaluator 产出（二开清单）时直接复用，不重跑

## pricing YAML schema（关键约束）

`pricing_compiler.py` 期望的 YAML 结构是 **扁平的 `categories` 列表**，不是嵌套的 `items.software`：

```yaml
# ✅ 正确
categories:
  - name: 标准产品
    items:
      - id: MI-001
        name: 商管系统
        description: ...
        first_unit_price: 50000
        first_qty: 1
        new_unit_price: 20000
        new_qty: 1
```

```yaml
# ❌ 错误（会导致编译失败或报价项丢失）
items:
  software:
    - id: MI-001
      ...
```

每个 item 必填：`id` / `name` / `description` / `first_unit_price` / `first_qty` / `new_unit_price` / `new_qty`。

## SAAS vs 私有化模式差异

两种模式的定价结构不同：

- **SAAS**：首年全价 + 次年续费（通常首年 5 万 / 次年 2 万）。`first_*` 是首年，`new_*` 是续费年
- **私有化**：一次性 license + 年度维护费。结构不同，模板不同

模板文件：`references/报价模板_<模式>.md`。选错模式会导致报价结构错乱。

## 依赖：产品功能清单

pricing-generator 依赖 product-prd-generator 产出的功能清单（`$LANLNK_BASE/out/prd/<产品>/output/功能清单.md`）作为定价基线。功能清单缺失时无法生成标准产品报价部分。

## Excel 输出格式约定

参考「正祥报价单」风格：
- 深蓝表头 `#001E5A8A`
- 浅红汇总行 `#00F9E5DD`
- 字体：微软雅黑

这些硬编码在 `generate_quote.py`，改格式需改源码不是配置。

## 与兄弟 skill 的边界

不做的事情（见 SKILL.md「不做的事情」）：不评估需求 / 不写方案汇报 / 不写投标商务标 / 不做产品 PRD。这些分别交给 requirement-evaluator / company-intro-generator / bid-doc-master / product-prd-generator。
