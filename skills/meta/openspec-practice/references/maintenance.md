# 维护与复利工程

## 目标

让 `openspec-practice` 在真实项目使用中持续变好，但不把一次性项目内容塞进 skill。

## 触发

用户说：

- `复利工程`
- `沉淀这次经验`
- `把这次 OpenSpec 实战经验沉淀一下`
- `以后这个 skill 按这个模式`

## 分流

优先使用 `compound-learning` 的三通道判断：

| 经验类型 | 写入位置 |
|---|---|
| 只影响某个目标项目 | 目标项目 `AGENTS.md` 或项目 docs |
| 影响人类使用 OpenCode/OpenSpec 的方式 | `/opt/code/docs/opencode/`，并更新 `90-复利工程/更新日志.md` |
| 只影响本 skill 的触发、流程、失败模式 | `openspec-practice/SKILL.md` 或 `references/` |
| 影响多个 skill | `/opt/code/skill/AGENTS.md` |
| 影响文档质量通用规则 | `/opt/code/skill/references/docspec/` |

## 可沉淀

- 已经在真实项目验证过的短口令。
- 新的 OpenSpec 现场类型。
- 新的 archive 漂移类型。
- 新的验证门禁或多 scope 识别模式。
- 反复出现的失败模式和恢复流程。

## 不沉淀

- 客户敏感信息、密钥、报价明细。
- 一次性项目路径，除非是稳定示例路径如 `/opt/code/mi`。
- 未完成、未验证、仍在猜测的判断。
- 业务系统具体实现细节，除非它影响 OpenSpec 流程本身。

## 更新检查

修改本 skill 后检查：

```bash
cd /opt/code/skill/skills/meta/openspec-practice
uv run python scripts/scan_openspec.py /opt/code/mi --json
uv run python scripts/scan_openspec.py /opt/code/langchat --json
```

并确认：

- `SKILL.md` 仍然短，详细流程在 `references/`。
- 新增参考文件被 `SKILL.md` 明确路由。
- Python 脚本只用 stdlib，能通过 `uv run` 执行。
