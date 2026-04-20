# 消防巡检知识演化机制

FireWatch 的知识演化目标是：让不同场景积累不同经验，并把真实火情和误报都转化为下一次巡检的改进依据。

## 存储文件

`knowledge/observations.jsonl`

```text
记录每次巡检观察，包括 source_id、scene_type、predict_profile、检测结果、风险等级和证据帧。
```

`knowledge/incident_cases.jsonl`

```text
记录用户确认后的真实火情、误报、演练和不确定事件。
```

`knowledge/pending_review.jsonl`

```text
记录从复盘和用户反馈中提取的候选经验，等待审核。
```

`knowledge/lessons_learned.jsonl`

```text
记录审核通过的经验。只有这里的经验可以影响后续 predict-wise 参数规划。
```

`knowledge/camera_profiles.json`

```text
记录每一路摄像头的运行态画像，包括 source_id、stream_url_hash、最近采用的 effective scene、风险历史、最近一次策略依据。
```

`knowledge/source_index.json`

```text
记录知识来源、审核状态和可信度策略。
```

## 演化流程

```text
巡检事件
  -> 写入 observations
  -> 用户确认真实火情/误报/演练
  -> 写入 incident_cases
  -> 提取 candidate lesson
  -> 写入 pending_review
  -> 审核通过
  -> 写入 lessons_learned
  -> 后续 predict-wise 读取并调整参数
```

## 跨任务复用

当用户第一次提交 3 路视频流，第二次重新开始任务并扩展到 5 路时：

```text
已出现过的 3 路：
  通过 source_id 或 stream_url_hash 找到 camera_profiles.json 中的历史画像；
  如果本次没有新的场景描述，则复用历史 effective scene 和策略经验。

新增的 2 路：
  没有历史画像，使用本次由 OpenClaw 从自然语言中抽取出的 hints，或使用 unknown 默认策略。
```

匹配优先级：

```text
1. source_id
2. stream_url_hash
```

不要在知识库中明文存储真实视频流地址，使用 `stream_url_hash` 识别同一路流。

## 场景化经验示例

仓库：

```text
货架遮挡可能导致火焰框不完整；
夜间低照度下 smoke 置信度偏低；
真实火情通常表现为连续多帧 fire + smoke。
```

配电间：

```text
smoke 比 fire 更敏感；
低置信度烟雾也需要复核；
报告中避免给出不可靠的具体灭火指令。
```

厨房：

```text
蒸汽可能误报 smoke；
正常炉灶明火需要 ROI 限定；
需要结合持续时间和区域判断异常。
```

室外：

```text
夕阳、车灯、反光可能误报 fire；
单帧低置信度不应直接升级；
需要更多连续帧或 smoke 伴随证据。
```

## 安全原则

- 未审核经验只能进入 `pending_review`，不能直接影响后续安全策略。
- 报告中要区分“模型检测结果”和“人工确认结果”。
- 消防建议应保持克制，优先建议人工复核和遵循单位应急预案。
- 涉及真实火情时，不要因为算法判断低风险而阻止人工升级处置。
