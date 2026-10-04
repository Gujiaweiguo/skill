# 现场扫描

用于短口令：`现场扫描 <项目>`。

## 目标

用最少输入盘清一个项目的 OpenSpec 使用现场：项目规则、scope、specs、active changes、archive、验证入口、风险和下一步。

## 步骤

1. 解析用户短口令的公司和产品上下文。产品路径必须来自 resolver 的 `code_root`；绝对路径可直接扫描，但不能据此猜产品。
2. 输出 resolver 的 company/product/layer authority 与所有非 complete 状态。
3. 读取项目根目录 `AGENTS.md` 和 `README*`。如果存在多个 `AGENTS.md`，列出并优先根目录。
4. 运行扫描脚本（`--json` 输出契约见 `references/scan-output.schema.json`；`现场扫描` 与 `检查多 scope` 共用该输出）：

```bash
cd /opt/code/skill/skills/meta/openspec-practice
uv run python scripts/scan_openspec.py <PROJECT_ROOT> --json
```

产品 ID 的上下文由 `uv run python scripts/resolve_context.py <PRODUCT_ID> [--company-id <ID>]` 输出；只有 resolver 返回的 `layers.code_root` 可作为产品目标路径。绝对路径输入允许直接扫描，无法映射时 company/product 标为 unresolved。

人读报告可去掉 `--json`；契约数据一律以 `--json` 输出为准。趋势对比：把上次扫描 JSON 存档，重跑时加 `--baseline <file>` 得到增量 diff（scope 扫描不完整时该 scope 只进 `uncomparable_scopes`，不产生增删结论）。baseline 严格校验：非对象、`schema_version` 不符、root 不同、scopes 形状非法、evidence 与 `active_changes` 不一致或含重复项、reason 不在枚举内，一律 exit 2 并给字段级错误；过期 baseline 重新生成，不要手改。

5. 如项目有自定义验证命令，读取 `Makefile`、`scripts/*openspec*`、`package.json`、`pyproject.toml` 中的相关命令。未发现时在输出中显式写「未发现（已查 <位置列表>）」，不省略该行——未发现证据不等于项目没有验证。
6. 必要时在每个 scope 运行：

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
| active change 的 verification report 非 present（missing / unreadable / empty / placeholder） | 在制或待验证或报告不可信；结合 tasks 勾选判断。历史 change 缺报告按 proposal/tasks/specs/code/tests 做证据审计，不补造 |
| 项目脚本提供聚合检查 | 优先使用聚合检查作为门禁 |

## 输出

```text
结论：
- 项目类型：<PRD/迁移驱动 | 平台持续迭代 | 多 scope | 混合>

解析上下文：
- company/product：<resolver 输出>
- 三层 authority：<ontology / prd / code path、status、revision>
- 非 complete 状态：<逐项列出；无则写 none>

现场：
- scope: <路径和数量>
- specs: <数量>
- active changes: <数量和状态；verification report 非 present 的按状态列出>
- archive: <数量和明显漂移>
- 验证入口: <命令，或「未发现（已查 AGENTS.md/Makefile/scripts/package.json/pyproject.toml）」>

建议下一步：
- <先出 Implementation Plan / 整理 active / 审计 archive / 回写 PRD / 执行某 change>
```
