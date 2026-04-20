# FireWatch Incident Agent

这是 `firewatch-incident-agent` skill 的本地开发项目。

## 当前进展

FireWatch 目前已经形成一条可运行的火情视频巡检主链路：

```text
自然语言中的视频流请求
  -> OpenClaw 整理 raw patrol request
  -> predict-wise 生成每路检测参数
  -> 调用火焰/烟雾检测服务
  -> 多帧视频级证据聚合
  -> 场景化风险研判
  -> 报告生成与 camera profile 更新
```

已实现能力：

- **predict-wise 初始策略**：按 unknown、场景线索、历史 camera profile、资源预算，为每一路视频流生成独立 `confidence`、`duration`、`interval` 和 `priority`。
- **大批量 unknown 轻量普查**：支持 `patrol_mode: "bulk_scout"`，没有场景线索的流先轻量扫描，有明确线索的流直接走场景精细化策略。
- **跨任务经验复用**：通过 `source_id` 和 `stream_url_hash` 复用 `knowledge/camera_profiles.json`，避免重新开始任务后丢失已有画像。
- **多帧视频级研判**：聚合 `hit_count`、`continuous_hit_count`、`class_counts`、`confidence_trend` 和场景权重，把帧级 fire/smoke 检测升级为视频级证据。
- **多路径风险分类**：输出 `transient_fire`、`sustained_fire_or_smoke`、`possible_false_positive` 或 `none`，避免强行用连续帧规则过滤短时高置信度明火。
- **知识演化骨架**：已写入 observation，并更新 camera profile；人工确认、pending review 和已审核 lessons 的完整闭环属于下一阶段。

当前边界：

- 当前版本只做单轮采样窗口内的视频级研判，不做长期运行中的自动动态调频。
- `burst follow-up` 现在是风险建议，不会自动再次调用检测 API。
- FireWatch 不自己解码视频或实现基础视觉模型，它通过 `fire_detection_client.py` 调用外部检测服务。

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

OpenClaw 负责把自然语言整理成 raw patrol request，再交给脚本执行。`hints` 是整理过程中产生的内部弱线索，例如“这路可能是厨房”，用户不需要手写 JSON 或逐路填写 `hints`。

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
