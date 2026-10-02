# 多 OpenSpec Scope

用于短口令：`检查多 scope`。

## 目标

识别仓库里所有 OpenSpec scope，避免只在根目录验证而漏掉子项目。

## 发现命令

```bash
find <ROOT> -name .openspec.yaml -o -path "*/openspec/specs"
find <ROOT> -path "*/openspec/changes" -type d
```

或运行：

```bash
cd /opt/code/skill/skills/meta/openspec-practice
uv run python scripts/scan_openspec.py <ROOT> --json
```

## 判断

- 每个包含 `openspec/` 或 `.openspec.yaml` 的目录都是一个候选 scope。
- 根 scope 通常记录产品/平台能力。
- 子 scope 可能记录后端包、SDK、独立服务或迁移中的局部能力。
- change 应落在行为真正归属的 scope。
- 跨 scope 需求要拆 change，或明确主 scope 与同步验证 scope。

## 验证入口

优先级：

1. 项目 `AGENTS.md` 明确的命令。
2. `Makefile` / `scripts/check_openspec.sh` / CI 中的聚合命令。
3. 每个 scope 内单独运行 `openspec validate --changes --strict`。

## 数据源

`现场扫描` 与 `检查多 scope` 共用同一份 `scan_openspec.py --json` 输出（契约见 `references/scan-output.schema.json`，`schema_version` 语义），分别渲染简版与详细版。矩阵行映射：`verification.command_source=none` → 命令未发现；`verification.execution=not-run` → 未执行——扫描器只发现命令，从不执行。

## 输出

```text
OpenSpec scopes：
| Scope | 验证命令 | 结果 | 失败类型 |

结果枚举（每行必须落其一，不许留空）：
- 命令未发现（注明已查位置：AGENTS.md / Makefile / scripts / CI）
- 未执行
- 失败（记录失败类型：validate / artifact 缺失 / 依赖 / 环境）
- 通过
- scope 不可访问

需求归属：
- 主 scope：
- 需要同步的 scope：

验证顺序：
1. ...
```

注意：「命令未发现」和「scope 不可访问」（`scan_status=inaccessible`）是证据状态，不等于该 scope 没有验证方式；遇到时如实输出，不推断。趋势对比可把上次扫描 JSON 存档后用 `--baseline <file>` 重跑；扫描不完整的 scope 只会出现在 `uncomparable_scopes`，不会被推断成增删或 gap 解决。
