# FireWatch Incident Agent

这是 `firewatch-incident-agent` skill 的本地开发项目。

## 目录说明

- `skill/firewatch-incident-agent/`：skill 源码目录，作为开发源头。
- `tools/sync-skill.ps1`：手动同步到 `../../skills/firewatch-incident-agent`。
- `tools/watch-sync-skill.ps1`：开发时监听变更并自动同步。
- `examples/patrol_3_streams_raw.json`：三路 raw 巡检输入示例，只包含视频流和可选线索。
- `examples/patrol_5_streams_raw.json`：五路 raw 巡检输入示例，只包含视频流和可选线索。
- `docs/analysis-implementation-todo.md`：中文分析、实现方案和 Todo。

## 使用方式

只看 OpenClaw 检测前的 camera profile 和 predict-wise 参数规划：

```powershell
.\tools\run-live-patrol.ps1 -RequestPath examples\patrol_5_streams_raw.json -PlanOnly
```

调用真实火焰/烟雾检测服务巡检：

```powershell
New-Item -ItemType Directory -Force examples\local
Copy-Item examples\patrol_5_streams_raw.json examples\local\patrol_live.json
# 修改 examples\local\patrol_live.json 中的视频流地址
.\tools\run-live-patrol.ps1
```

`examples/local/` 已加入 `.gitignore`，用于保存本机真实摄像头地址和私有配置。

## OpenClaw 输入方式

真实使用时，用户可以直接输入一个或多个视频流地址，并可选说明场景：

```text
帮我看这三路：
rtsp://cam-a/live
rtsp://cam-b/live 这个可能是厨房
rtsp://cam-c/live 可能是室外通道
```

OpenClaw 负责把自然语言整理成 raw patrol request，再交给脚本执行。

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
