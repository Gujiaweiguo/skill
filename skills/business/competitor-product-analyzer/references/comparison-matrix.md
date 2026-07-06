# Comparison Matrix — 加权对比矩阵方法论

本文件定义 P6 阶段的加权对比矩阵与改进建议分级规则。SKILL.md 的 P6 阶段强制遵循此方法论。

## 设计原则

行业最佳实践明确（ideaplan.io、compttr.com、productboard、aakashg.com、fairview）：

1. **不做 100 行打勾表**：要聚焦客户/买家关心的 15-25 项能力，不是穷举
2. **不打 binary yes/no**：要用 4 级实现质量评分（Leading/Competitive/Behind/Missing）
3. **不平均加权**：3-5 项关键能力决定 80% 决策，必须加权
4. **权重来自买家研究**：不是内部拍脑袋，来自客户需求频率/岗位痛点频率
5. **改进建议分 4 类**：补齐/增强/借鉴/观察，对应不同优先级

## 矩阵结构

`ability-comparison-matrix.json` 顶层：

```json
{
  "schema_version": "1.0",
  "vendor": "qimao",
  "lanlnk_product": "MI（商管系统）",
  "generated_at": "2026-07-06T11:30:00+08:00",
  "weight_source": "requirement-evaluator 客户需求频率 + 岗位病药矩阵",
  "dimensions": [
    { /* 见下方 Dimension 对象 */ }
  ],
  "capabilities": [
    { /* 见下方 MatrixCapability 对象 */ }
  ],
  "summary": {
    "lanlnk_weighted_score": 3.4,
    "competitor_weighted_score": 3.8,
    "gap_focus": ["合同免租期分段", "招商漏斗周报", "集团驾驶舱"]
  }
}
```

## Dimension 对象（加权维度）

不按"功能模块"加权，按**客户决策维度**加权：

| 维度（示例） | 含义 | 典型能力 |
|---|---|---|
| 核心业务闭环 | 招商→合同→财务→营运是否跑得通 | 铺位建档、合同审批、出账收款 |
| 财务精细化 | 账龄、保证金、预存款、发票、对账 | 账龄分析、保证金自动转抵 |
| 移动协同 | 移动端审批、现场拍照、离线 | 移动审批、巡场拍照 |
| 报表与决策 | 自定义报表、驾驶舱、经营分析 | 集团驾驶舱、招商漏斗 |
| 集成生态 | POS/停车/客流/电子签/支付 | POS 对接、客流接入 |
| AI 增强 | 问数、RAG、Copilot | 经营数据问数、制度问答 |
| 实施与运维 | 部署、升级、配置灵活度 | 字段配置、流程引擎 |

```json
{
  "dimension_id": "DIM-core-closed-loop",
  "name": "核心业务闭环",
  "weight": 25,
  "rationale": "客户选型时最关心，决定能否上线运营"
}
```

**权重分配规则**：

- 总和 = 100
- 核心业务闭环权重最高（20-30）
- 客户高频痛点维度次之（15-20）
- AI/BI 等新兴维度可低权（5-10），除非客户明确关注
- 权重必须来自买家研究，不是内部假设

**权重来源优先级**：

1. 用户在 P0 显式提供
2. `requirement-evaluator` 的客户需求汇总（频率高的能力维度加权）
3. `$LANLNK_BASE/knowledge/sales/methodology/15-商业地产岗位病药矩阵.md`（多岗位共同痛点加权）
4. 默认均匀分布（仅当以上都缺失，且必须在 summary 标注"权重未校准"）

## MatrixCapability 对象

```json
{
  "capability_id": "CAP-合同管理-新合同申请",
  "module": "合同管理",
  "capability_name": "新合同申请",
  "dimension_id": "DIM-core-closed-loop",
  "lanlnk_quality": "Competitive",
  "competitor_quality": "Leading",
  "quality_gap": +1,
  "evidence_strength": "high",
  "recommendation": {
    "type": "增强",
    "priority": "P1",
    "rationale": "蓝联已有新合同申请，但旗茂支持免租期分段（前 3 月全免+后续 3 月半免），蓝联只支持整段免租期。客户谈判灵活性不足。",
    "evidence_refs": ["EV-001", "EV-002"],
    "prd_handoff": "建议在 product-prd-generator 的合同模块 PRD 中增加'免租期分段配置'字段"
  }
}
```

### quality_gap 计算

`quality_gap = competitor_quality_score - lanlnk_quality_score`

质量评分映射：

| quality_assessment | 分数 |
|---|---|
| Leading | 4 |
| Competitive | 3 |
| Behind | 2 |
| Missing | 1 |

- `quality_gap > 0`：竞品优于蓝联（重点关注）
- `quality_gap = 0`：持平
- `quality_gap < 0`：蓝联优于竞品（差异化机会）

## 改进建议四类

| 类型 | 触发条件 | 默认优先级 | 说明 |
|---|---|---|---|
| `补齐` | lanlnk_quality=Missing 且该维度 weight≥15 | P0/P1 | 客户会关心、蓝联没有、必须做 |
| `补齐` | lanlnk_quality=Missing 且该维度 weight<15 | P1/P2 | 蓝联没有但客户关注度低 |
| `增强` | lanlnk_quality=Behind 或 (Competitive 且 competitor=Leading) | P1/P2 | 蓝联有但体验/字段/流程不如竞品 |
| `增强` | lanlnk_quality=Competitive 且 competitor=Competitive 且 evidence=high 且有具体短板 | P2 | 持平但有局部短板 |
| `借鉴` | competitor=Leading 且蓝联 Competitive | P2/P3 | 竞品设计好但不一定立刻做 |
| `观察` | evidence=low 或 status=unknown | 不进路线图 | 证据不足或权限未覆盖 |

**优先级调整规则**：

- 客户必需（requirement-evaluator 标必需）→ 优先级升一级（P2→P1）
- 多客户共同需求（≥3 客户提到）→ 优先级升一级
- 仅销售材料证据 → 强制降为"观察"
- 实现复杂度 L（跨模块/新业务线）→ 优先级可降一级（避免一上来做大改）

## 加权总分（诊断信号，不是判决）

```
加权总分 = Σ (quality_score × dimension_weight) / 100
```

**重要**：加权总分是**诊断信号**，不是竞品胜负判决。

- 竞品加权总分 > 蓝联：说明在客户关心的维度上竞品更强，是改进的优先方向
- 蓝联加权总分 > 竞品：说明蓝联有可放大的差异化优势，sales 可作为卖点
- 总分接近：说明同质化，差异化要看具体维度的 Leading 项

**禁止**：把加权总分直接写成"竞品综合评分 X 分，蓝联 X 分，竞品胜"。必须落到具体维度和能力。

## 改进建议报告结构

`lanlnk-product-improvement-recommendations.md`：

```markdown
# 竞品能力分析与蓝联产品改进建议

> 竞品：<vendor> <product>
> 对照产品：<lanlnk_product>
> 分析模式：<input_mode>
> 资料覆盖度：手册 N 份 + demo 探测 M 页 + 截图 K 张
> 证据置信度分布：high X% / medium Y% / low Z%
> 生成日期：YYYY-MM-DD

## 一、管理层摘要
- 发现 N 项能力，覆盖 D 个客户决策维度
- 蓝联加权总分 X / 竞品加权总分 Y
- **关键发现**：竞品在 <维度1>、<维度2> 领先；蓝联在 <维度3> 有差异化优势
- **核心建议**：P0 必补 N 项 / P1 增强 N 项 / P2 借鉴 N 项 / 观察 N 项

## 二、加权对比矩阵（按维度分组）
### 维度1：核心业务闭环（权重 25）
| 能力 | 蓝联质量 | 竞品质量 | 差距 | 证据 | 建议 | 优先级 |
|---|---|---|---|---|---|---|
（每个维度一表）

## 三、改进建议清单
### P0 必补（本期）
| # | 能力 | 维度 | 竞品优势 | 蓝联现状 | 建议 | PRD 交接 |
### P1 增强（下期）
### P2 借鉴（远期）
### 观察（证据不足，不进路线图）

## 四、蓝联差异化优势（可作 sales 卖点）
（quality_gap < 0 的能力，蓝联比竞品强）

## 五、待确认问题（来自 review/pending-items.md）

## 附录：证据台账摘要
（按 capability 列出 evidence_id，完整版见 evidence-ledger.md）
```

## 与兄弟 Skill 的衔接

| 输出 | 衔接 | 说明 |
|---|---|---|
| `lanlnk-product-improvement-recommendations.md` 的 P0/P1 项 | → `product-prd-generator` | 作为 PRD 的差距分析输入 |
| `ability-comparison-matrix.json` | → `strategy-brief-generator` | 作为"看竞对"的证据 |
| 蓝联差异化优势章节 | → `company-intro-generator` | 作为方案汇报的卖点素材（仅内部用，不直接抄竞品）|
| 待确认问题清单 | → 销售/客户沟通 | 作为竞品复核问卷 |
