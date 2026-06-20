# 结构化内容包格式规范 v1.0

## 概述

结构化内容包（Content Package）是**业务 Skill → ppt-master** 之间的标准数据交换格式。
业务 Skill 负责"说什么"（内容策略、素材匹配、叙事编排），
ppt-master 负责"怎么画"（视觉设计、版式、配色、配图）。

## 文件格式

- 格式：Markdown + YAML frontmatter
- 编码：UTF-8
- 扩展名：`.content.md`
- 存放目录：`$PROPOSALS_DIR/{项目}/content-packages/`（立项 + 方案统一）

## 完整结构

```markdown
---
# ========== 元数据 ==========
title: "项目名称 + 文档类型"
project: "客户项目名称"
client: "客户单位全称"
type: "proposal | report | intro"     # 文档类型
style: "商务汇报 | 咨询风格 | 技术演讲"  # 推荐 ppt-master 风格
target_pages: 20-30                    # 目标页数范围
date: "2026-06-15"
author: "蓝联科技"

# ========== 素材引用 ==========
sources:
  - path: "$MATERIALS_DIR/03-products/商圈会员CRM系统.md"
    type: 产品方案
    pages: [6, 7, 8]                     # 引用到哪些页面
  - path: "$MATERIALS_DIR/04-cases/时尚天河CRM会员营销.md"
    type: 客户案例
    pages: [9, 10]
  - path: "$MATERIALS_DIR/01-company-overview/公司简介.md"
    type: 公司概况
    pages: [1, 2, 3]

# ========== 配色建议（可选） ==========
colors:
  primary: "1a1a2e"
  secondary: "16213e"
  accent: "0f3460"
  light: "e94560"
  bg: "f5f5f5"

# ========== 品牌标识 ==========
brand:
  logo: "$MATERIALS_DIR/../assets/logo.png"   # 可选
  slogan: "让商业更智能"
---

# 页面大纲

<!--
每页一个章节，按序号排列。
ppt-master 根据 type 字段选择对应版式。
-->

## 第1页

```yaml
type: cover
title: "正祥广场会员系统立项方案"
subtitle: "福州正祥商业管理有限公司"
date: "2026年6月"
```

## 第2页

```yaml
type: toc
title: "目录"
items:
  - 项目背景与痛点
  - 市场对标分析
  - 建设方案
  - 投入预算
  - 实施计划
```

## 第3页

```yaml
type: section
title: "01 项目背景与痛点"
```

## 第4页

```yaml
type: content
title: "正祥广场现状"
layout: left-right      # 左右分栏
left: |
  正祥广场位于福州市中心，建筑面积30万㎡，
  年客流量约2000万人次，现有商户500+家。
  
  **现状问题：**
  - 会员分散，无统一会员体系
  - 积分规则不统一，商户参与度低
  - 缺乏数字化营销手段
  - 停车体验差，无法与会员体系联动
right: |
  > **关键数据**
  >
  > 30万㎡ 建筑面积
  > 500+ 入驻商户
  > 2000万 年客流量
  > ⚠️ 会员转化率 <5%
```

## 第5页

```yaml
type: content
title: "竞品对标：福州仓山万达广场"
layout: comparison       # 对比页
columns:
  - name: "正祥广场（现状）"
    items:
      - 会员体系: 无统一体系
      - 积分: 各商户独立
      - 停车: 人工收费
      - 小程序: 无
  - name: "仓山万达（对标）"
    items:
      - 会员体系: 普卡-钻石4级
      - 积分: 全场通用+消费累积
      - 停车: 消费免停+自动积分
      - 小程序: 停车/优惠/导航
highlight: "差距明显：需从0到1建设完整会员体系"
```

## 第6页

```yaml
type: content
title: "推荐方案：商圈会员CRM系统"
layout: feature-grid     # 功能网格
features:
  - icon: "会员管理"
    desc: "统一的会员等级、积分、权益管理"
  - icon: "积分体系"
    desc: "全场通用积分、消费累积、自动积分"
  - icon: "停车联动"
    desc: "消费免停、积分抵扣停车费"
  - icon: "营销工具"
    desc: "优惠券、秒杀、拼团、社群运营"
  - icon: "数据看板"
    desc: "会员画像、消费分析、运营报表"
  - icon: "小程序"
    desc: "会员中心、积分商城、停车缴费"
```

## 第7页

```yaml
type: content
title: "投入预算"
layout: data-table       # 数据表格
table:
  header: ["项目", "金额（万元）", "说明"]
  rows:
    - ["软件系统", "50-60", "CRM系统+小程序+停车模块"]
    - ["实施服务", "20-30", "部署/配置/培训/上线"]
    - ["运营陪跑", "10-15", "3个月运营支持"]
    - ["云服务", "5-8", "首年云资源"]
    - ["合计", "85-113", ""]
note: "具体金额需根据实际需求细化确认"
```

## 第8页

```yaml
type: summary
title: "建议与下一步"
items:
  - 建议立即启动立项，抢占Q3黄金运营期
  - 下一步：需求调研 → 出具详细方案 → 商务洽谈
cta: "联系：蓝联科技 | 让商业更智能"
```

## 第9页

```yaml
type: end
title: "谢谢"
contact: "蓝联科技 | www.lanlnk.com | contact@lanlnk.com"
```

## 页面类型说明

| type | 用途 | ppt-master 处理方式 |
|------|------|-------------------|
| `cover` | 封面 | 大标题+副标题+日期+品牌 |
| `toc` | 目录 | 章节列表，可加页码 |
| `section` | 章节过渡页 | 章节标题+装饰元素 |
| `content` | 核心内容页 | 按 layout 字段选择版式 |
| `summary` | 总结页 | 核心回顾+CTA |
| `end` | 结尾页 | 联系方式+口号 |

## content 页 layout 类型

| layout | 适用场景 | 说明 |
|--------|---------|------|
| `left-right` | 对比/因果 | 左文右数据，或左因右果 |
| `comparison` | 竞品对标 | 多列对比，highlight 关键差异 |
| `feature-grid` | 产品介绍 | 2x3 或 3x2 网格展示功能点 |
| `data-table` | 预算/参数 | 表格数据，可加汇总行 |
| `timeline` | 发展历程/实施计划 | 横向时间轴 |
| `big-number` | 核心数据 | 大数字+说明文字 |
| `bullet-list` | 要点陈列 | 列表+图标 |

## 内容包生成规范

1. 业务 Skill 完成 P0-P3 内容编排后，按此格式输出 `.content.md`
2. 放入 `content-packages/` 临时目录（与正式输出同项目目录）
3. ppt-master 检测到 `.content.md` 输入时，按此协议解析生成
4. 内容包本身不包含图片二进制数据，仅引用路径