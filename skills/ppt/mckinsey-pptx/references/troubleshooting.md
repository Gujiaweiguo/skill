# mckinsey-pptx 排障手册

> 本文件记录 mckinsey-pptx 的非显而易见行为。跨 skill 通用规则见 `AGENTS.md`，不在此重复。

## 与 ppt-master 的区别（不要混用）

| 维度 | mckinsey-pptx | ppt-master |
|---|---|---|
| 视觉规范 | 麦肯锡风格（战略咨询专用） | 通用商务（汇报/方案/路演） |
| 引擎 | PptxGenJS（Node.js） | python-pptx + proposal-pptx |
| 结构约束 | MECE + 金字塔 + 数据驱动叙事 | 灵活版式 |
| 适用场景 | 战略咨询/投研/行业研究/管理咨询 | 商务汇报/客户演示/技术方案 |

**坑**：把通用商务汇报用 mckinsey-pptx 生成 → 强制套 MECE 金字塔结构，过度结构化；把战略咨询汇报用 ppt-master → 缺乏咨询级的严谨视觉。选错 skill 产出质量下降。

## MECE 与金字塔是硬约束

麦肯锡风格的「结论先行 + MECE 分解 + 数据支撑」不是建议，是**结构强制**：

- 每页必须有明确的核心论点（action title），不是中性标题
- 论据必须 MECE（互斥且穷尽），不能有重叠或遗漏
- 叙事遵循金字塔：顶部结论 → 下方分层论据支撑

**症状**：输入内容不满足 MECE 时，生成结果要么强行分解导致逻辑牵强，要么产出空骨架。内容准备阶段就应按 MECE 组织，不要指望 skill 替你补逻辑。

## 麦肯锡视觉硬编码

以下视觉规则硬编码在生成逻辑里，不是配置项：

- **深蓝 header 栏**（咨询标志性视觉）
- 结构化版式（非自由排版）
- 数据驱动图表表达
- 极简色彩（深蓝为主，克制使用其他颜色）

改视觉规范 = 改源码，不是改配置。如果客户要非麦肯锡风格，用 ppt-master 而非改本 skill。

## Node.js + PptxGenJS 依赖

```bash
cd skills/ppt/mckinsey-pptx
npm install   # 一次性安装 pptxgenjs
```

- 与 ppt-master 的 python-pptx 生态**完全独立**，不共享依赖
- Node.js 环境缺失时无法生成 .pptx
- 生成命令通过 Node 脚本调用 PptxGenJS API

## 降级：pptxgenjs 不可用

当 Node.js / pptxgenjs 不可用时，skill **优雅降级**为输出 text-only outline（Markdown 大纲），不报错中断。降级产物可用于人工制作 PPT，但无麦肯锡视觉。

**判断是否降级**：检查输出是 `.pptx`（正常）还是 `.md` outline（降级）。

## imageGen 视觉素材补充

复杂咨询 deck 常需补充视觉素材（图标/示意图）。本 skill 通过 imageGen 补充视觉材料，但 imageGen 不可用时不阻塞——产出纯文本+图表版式。

## 与 frontend-slides 的区别

frontend-slides 也是 PptxGenJS，但面向**技术分享**（代码高亮/架构图/性能图表/Sprint 回顾），不是战略咨询。技术内容用 frontend-slides，战略内容用 mckinsey-pptx。
