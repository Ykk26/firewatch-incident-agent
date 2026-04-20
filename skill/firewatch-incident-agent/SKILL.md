---
name: firewatch-incident-agent
description: Orchestrate intelligent fire patrols for camera and video streams. Use when the user asks to inspect one or many streams, optimize predict parameters per stream, aggregate multi-frame fire/smoke evidence, reduce false positives, generate fire incident reports or alerts, or store scene-specific fire safety lessons from confirmations and reviews.
---

# FireWatch Incident Agent

## 定位

使用本 skill 编排火情视频巡检工作流。它面向火焰/烟雾检测服务或视觉模型 API，负责多路巡检、predict-wise 参数规划、多帧证据聚合、风险研判、报告生成和场景知识演化。

## 核心工作流

1. 接收用户自然语言输入中的一个或多个视频流地址，场景信息可选。
2. 由 OpenClaw 根据用户描述整理临时 patrol request：`source_id`、`stream_url`、可选 `scene_type`、可选 `hints`、可选 `roi`、`patrol_mode` 和资源约束。不要要求用户手写 JSON；JSON 只是脚本接口。
3. 如果用户一次性提交大量视频流且多数没有场景线索，设置 `patrol_mode: "bulk_scout"`：unknown 流走轻量普查；带厨房、配电间、仓库、室外等线索的流跳过轻量普查，直接走对应场景精细化策略。
4. 使用 `scripts/camera_profile_store.py` 读取历史 camera profile。优先通过 `source_id` 匹配；如果 source_id 变化，则通过 `stream_url_hash` 匹配。不要在知识库中明文保存真实视频流地址。
5. 结合本次用户 hints、`config.json` 中的通用场景知识、`knowledge/lessons_learned.jsonl` 中的已审核经验，以及历史 camera profile，分析每一路流的 camera profile。
6. 使用 `scripts/predict_planner.py` 为每一路视频流生成 predict-wise profile。profile 必须解释参数依据，例如 unknown 轻量普查、厨房蒸汽误报、配电间 smoke 权重、历史画像复用等。
7. 使用 `scripts/fire_detection_client.py` 调用火焰/烟雾检测 API。
8. 使用 `scripts/temporal_aggregator.py` 聚合检测结果。多帧连续是增强证据，但不是唯一门槛；单帧高置信度 fire 应进入突发明火证据路径。
9. 使用 `scripts/risk_assessor.py` 按多路径证据策略评估风险：`transient_fire`、`sustained_fire_or_smoke`、`possible_false_positive` 或 `none`。
10. 使用 `scripts/report_writer.py` 生成 Markdown 报告或告警文本。
11. 使用 `scripts/knowledge_store.py` 写入观察记录；使用 `scripts/camera_profile_store.py` 更新 `knowledge/camera_profiles.json`，让下一次任务复用摄像头画像。

## 设计原则

- 将模型推理视为可替换服务。优先通过配置接入检测 API，不把具体模型或服务实现写死在工作流里。
- 不假设每路摄像头都有准确场景标签。缺少场景时，使用 unknown 默认策略或弱线索推导的倾向策略。
- 当用户一次性提交大量视频流且没有逐路场景时，使用 `patrol_mode: "bulk_scout"` 对 unknown 流轻量普查；如果某一路有厨房、配电间、仓库等明确线索，则直接使用对应场景的精细化策略。
- 支持跨任务复用 camera profile。用户先提交 3 路、下次扩展到 5 路时，已出现过的流应通过 `source_id` 或 `stream_url_hash` 复用历史画像；新增流再按本次 hints 或 unknown 策略处理。
- 解释 predict-wise 参数选择。任何非默认的置信度、检测时长、抽帧间隔或 ROI 都要给出简短原因。
- 优先使用视频级证据，不要只依赖单帧判断。综合连续性、类别组合、置信度趋势和场景历史。
- 知识演化必须分阶段。新经验先进入 `knowledge/pending_review.jsonl`，审核后才能成为可信场景知识。
- 消防建议要保持克制。建议人工复核并遵循单位应急预案，不要把不确定模型输出说成事实。

## 巡检运行方式

用户不需要手写 JSON。OpenClaw 应从用户消息中提取视频流地址和可选场景描述，形成临时 patrol request，再调用 `scripts/orchestrator.py`。

脚本入口仍然接收 JSON，是为了让 OpenClaw 和本地测试有稳定的结构化接口。

只查看检测前策略，不调用检测服务：

```powershell
.\tools\run-live-patrol.ps1 -RequestPath examples\patrol_5_streams_raw.json -PlanOnly
```

执行真实巡检：

```powershell
.\tools\run-live-patrol.ps1 -RequestPath examples\local\patrol_live.json
```

巡检目标示例：

```json
{
  "mode": "patrol",
  "patrol_mode": "normal",
  "resource_budget": "balanced",
  "targets": [
    {
      "source_id": "stream-1",
      "stream_url": "rtsp://camera/warehouse-east",
      "scene_type": "unknown",
      "hints": {
        "location_hint": "用户提到可能是厨房或后厨",
        "user_label": "厨房摄像头"
      }
    }
  ]
}
```

如果用户只给地址，没有场景描述，则 `scene_type` 使用 `unknown`，`hints` 可以为空。FireWatch 先使用 unknown 默认策略，并在后续通过观察、用户确认和知识库迭代逐步形成摄像头画像。

大批量 unknown 示例：

```json
{
  "mode": "patrol",
  "patrol_mode": "bulk_scout",
  "resource_budget": "fast",
  "targets": [
    {
      "source_id": "stream-1",
      "stream_url": "rtsp://camera/a",
      "scene_type": "unknown",
      "hints": {}
    },
    {
      "source_id": "stream-2",
      "stream_url": "rtsp://camera/b",
      "scene_type": "unknown",
      "hints": {
        "location_hint": "用户说这一路可能是厨房"
      }
    }
  ]
}
```

在这个例子中，`stream-1` 会走 unknown 轻量普查；`stream-2` 会结合厨房知识使用精细化策略。

跨任务复用示例：

```text
第一轮：用户提交 stream-1、stream-2、stream-3。
巡检后：FireWatch 写入 camera_profiles.json。
第二轮：用户提交 stream-1、stream-2、stream-3、stream-4、stream-5。
结果：前三路复用历史 camera profile；后两路按本次 hints 或 unknown 策略处理。
```

## 参考文件

- 修改架构或讲参赛故事时，阅读 `references/architecture.md`。
- 修改事件 JSON、报告或存储结构时，阅读 `references/event-schema.md`。
- 修改每路推理参数规划时，阅读 `references/predict-wise.md`。
- 修改多帧聚合、突发明火和疑似误报判断时，阅读 `references/temporal-aggregation-policy.md`。
- 修改场景知识演化流程时，阅读 `references/knowledge-evolution.md`。
- 修改自然语言请求到 patrol request 的整理方式时，阅读 `references/request-workflow.md`。

## 输出标准

处理巡检或事件时，返回：

- 巡检摘要：视频流数量、异常流数量、资源节省说明。
- 风险结果：等级、判断依据、误报风险。
- 证据：可用的证据帧路径或 URL。
- 知识更新：写入 observation 或 pending review 的内容。
- 后续动作：人工复核、告警推送或复盘审核建议。
