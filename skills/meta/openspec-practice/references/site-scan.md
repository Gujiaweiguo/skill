# 现场扫描

用于短口令：`现场扫描 <项目>`。

## 目标

用最少输入盘清一个项目的 OpenSpec 使用现场：项目规则、scope、specs、active changes、archive、验证入口、风险和下一步。

## 步骤

1. 解析项目路径。`mi`、`langchat`、`docs`、`skill` 使用 `SKILL.md` 中的默认路径。
2. 读取项目根目录 `AGENTS.md` 和 `README*`。如果存在多个 `AGENTS.md`，列出并优先根目录。
3. 运行扫描脚本：

```bash
cd /opt/code/skill/skills/meta/openspec-practice
uv run python scripts/scan_openspec.py <PROJECT_ROOT>
```

4. 如项目有自定义验证命令，读取 `Makefile`、`scripts/*openspec*`、`package.json`、`pyproject.toml` 中的相关命令。
5. 必要时在每个 scope 运行：

```bash
openspec list --json
openspec validate --changes --strict --json --no-interactive
```

## 判断

| 信号 | 判断 |
|---|---|
| specs 和 archive 很多，active changes 也存在 | 多 change 批次项目，先排序和分流 |
| 根目录和子目录都有 openspec | 多 scope 项目，先确定需求归属 scope |
| archived tasks 有未勾选项 | 可能有历史漂移，不能直接当成未完成 |
| active changes valid 但任务未完成 | 正常在制，不是漂移 |
| 项目脚本提供聚合检查 | 优先使用聚合检查作为门禁 |

## 输出

```text
结论：
- 项目类型：<PRD/迁移驱动 | 平台持续迭代 | 多 scope | 混合>

现场：
- scope: <路径和数量>
- specs: <数量>
- active changes: <数量和状态>
- archive: <数量和明显漂移>
- 验证入口: <命令>

建议下一步：
- <先出 Implementation Plan / 整理 active / 审计 archive / 回写 PRD / 执行某 change>
```
