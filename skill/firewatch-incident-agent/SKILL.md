---
name: firewatch-incident-agent
description: Orchestrate intelligent fire patrols on top of fire-detection. Use when the user asks to inspect one or many camera/video streams, optimize predict parameters per stream, aggregate multi-frame fire/smoke evidence, reduce false positives, generate fire incident reports or alerts, or store scene-specific fire safety lessons from confirmations and reviews.
---

# FireWatch Incident Agent

## 定位

使用本 skill 作为 `skills/fire-detection` 之上的编排层。保持原火焰检测 skill 不变，把它当作底层推理服务；本 skill 负责多路巡检、predict-wise 参数规划、多帧证据聚合、风险研判、报告生成和场景知识演化。

## 核心工作流

1. 将用户请求解析为巡检目标：`source_id`、`stream_url`、`scene_type`、可选 `roi` 和用户约束。
2. 使用 `scripts/predict_planner.py` 为每一路视频流生成 predict-wise profile。
3. 使用 `scripts/fire_detection_client.py` 调用现有火焰检测 API。
4. 使用 `scripts/temporal_aggregator.py` 聚合多帧检测结果。
5. 使用 `scripts/risk_assessor.py` 评估风险等级和误报可能性。
6. 使用 `scripts/report_writer.py` 生成 Markdown 报告或告警文本。
7. 使用 `scripts/knowledge_store.py` 存储观察记录、确认案例、误报和候选经验。

## 设计原则

- 保留 `fire-detection` 作为底层模型服务。除非用户明确要求，不要修改原 skill。
- 解释 predict-wise 参数选择。任何非默认的置信度、检测时长、抽帧间隔或 ROI 都要给出简短原因。
- 优先使用视频级证据，不要只依赖单帧判断。综合连续性、类别组合、置信度趋势和场景历史。
- 知识演化必须分阶段。新经验先进入 `knowledge/pending_review.jsonl`，审核后才能成为可信场景知识。
- 消防建议要保持克制。建议人工复核并遵循单位应急预案，不要把不确定模型输出说成事实。

## 巡检运行方式

初版集成入口是 `scripts/orchestrator.py`。它接收巡检 JSON，并写出事件和报告产物。

巡检目标示例：

```json
{
  "mode": "patrol",
  "resource_budget": "balanced",
  "targets": [
    {
      "source_id": "warehouse-east",
      "stream_url": "rtsp://camera/warehouse-east",
      "scene_type": "warehouse"
    }
  ]
}
```

## 参考文件

- 修改架构或讲参赛故事时，阅读 `references/architecture.md`。
- 修改事件 JSON、报告或存储结构时，阅读 `references/event-schema.md`。
- 修改每路推理参数规划时，阅读 `references/predict-wise.md`。
- 修改场景知识演化流程时，阅读 `references/knowledge-evolution.md`。

## 输出标准

处理巡检或事件时，返回：

- 巡检摘要：视频流数量、异常流数量、资源节省说明。
- 风险结果：等级、判断依据、误报风险。
- 证据：可用的证据帧路径或 URL。
- 知识更新：写入 observation 或 pending review 的内容。
- 后续动作：人工复核、告警推送或复盘审核建议。
