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
uv run python scripts/scan_openspec.py <ROOT>
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

## 输出

```text
OpenSpec scopes：
| Scope | specs | active | archive | 验证命令 |

需求归属：
- 主 scope：
- 需要同步的 scope：

验证顺序：
1. ...
```
