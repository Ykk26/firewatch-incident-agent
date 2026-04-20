# FireWatch Incident Agent

这是 `firewatch-incident-agent` skill 的本地开发项目。

## 目录说明

- `skill/firewatch-incident-agent/`：skill 源码目录，作为开发源头。
- `tools/sync-skill.ps1`：手动同步到 `../../skills/firewatch-incident-agent`。
- `tools/watch-sync-skill.ps1`：开发时监听变更并自动同步。
- `examples/patrol_request_dry_run.json`：本地 dry-run 巡检示例。
- `docs/analysis-implementation-todo.md`：中文分析、实现方案和 Todo。

## 同步方式

手动同步：

```powershell
.\tools\sync-skill.ps1
```

镜像同步：

```powershell
.\tools\sync-skill.ps1 -Mirror
```

开发时自动同步：

```powershell
.\tools\watch-sync-skill.ps1
```

项目目录是源头，`skills/firewatch-incident-agent` 是同步后的 OpenClaw 可发现 skill 目录。
