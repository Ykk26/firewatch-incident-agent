# Predict-wise 参数规划

Predict-wise 的含义是：每一路视频流都拥有独立推理策略。

传统做法通常是：

```text
所有摄像头使用同样的检测时长、抽帧间隔、置信度阈值和告警规则。
```

FireWatch 的做法是：

```text
不要求一开始知道准确场景；
先构建 camera profile；
再结合弱线索、历史经验和资源预算，为每一路流生成单独的 predict profile。
```

## 输入因素

- `scene_type`：可选显式场景；没有时使用 unknown。
- `hints`：OpenClaw 从自然语言中抽取出的内部弱线索，例如 indoor_outdoor、risk_zone、location_hint、user_label。用户不需要手写这些字段。
- `resource_budget`：fast、balanced、thorough。
- `patrol_mode`：bulk_scout、normal、focused。
- `history`：真实火情、误报、演练、已审核经验。
- `roi`：用户指定的检测区域。
- `source_id`：具体摄像头或视频流 ID。

## Camera Profile

真实业务里，经常拿不到准确摄像头场景。FireWatch 不把场景标签当成强前提，而是先形成一个 camera profile：

```json
{
  "source_id": "cam_001",
  "declared_scene_type": "unknown",
  "effective_scene_type": "outdoor",
  "scene_confidence": 0.55,
  "hints": {
    "indoor_outdoor": "outdoor",
    "user_label": "园区通道"
  },
  "basis": "未提供明确场景，根据 indoor_outdoor=outdoor 使用 outdoor 倾向策略。"
}
```

`effective_scene_type` 只是当前巡检策略的工作假设，不等于事实标签。后续应通过人工确认和历史观察持续修正。

## 资源预算策略

`fast`：

```text
缩短检测时间
放大抽帧间隔
提高置信度阈值
目标是快速筛查和节省资源
```

`balanced`：

```text
使用 camera profile 推导出的默认参数
适合常规巡检
```

`thorough`：

```text
延长检测时间
缩小抽帧间隔
适当降低高风险场景阈值
目标是提高召回和留证质量
```

## 场景策略

下面的策略是 profile 模板，不要求摄像头一开始就被准确分类。

仓库：

```text
高风险区域，检测时间更长，抽帧更密，阈值略低。
```

配电间：

```text
烟雾很重要，低置信度 smoke 也值得关注。
```

厨房：

```text
蒸汽和正常明火容易误报，需要更强证据。
```

室外：

```text
夕阳、车灯、反光容易误报 fire，阈值更高，抽帧更轻。
```

未知场景：

```text
使用平衡参数，等待积累足够观察记录。
```

## 弱线索策略

当 `scene_type` 缺失或为 unknown 时，按以下顺序使用 OpenClaw 抽取出的弱线索：

```text
1. indoor_outdoor=outdoor -> outdoor 倾向策略
2. location_hint/user_label/notes 中的关键词 -> 对应场景倾向策略
3. risk_zone=high -> 高风险兜底倾向策略
4. 仍无依据 -> unknown 默认策略
```

报告中必须说明这是“倾向策略”，避免把推断当成事实。

## 大批量视频流策略

当用户一次性提交大量视频流时，不要求用户逐路标注场景，也不要对所有视频流直接精检。

推荐使用：

```json
{
  "patrol_mode": "bulk_scout",
  "resource_budget": "fast"
}
```

`bulk_scout` 的含义：

```text
对没有场景线索的 unknown 流，使用短时长、大间隔、较高阈值的轻量普查策略；
目标是先找出疑似异常流，避免一开始对所有流精检。
```

如果某一路有明确或可推断场景，例如用户说“这一路可能是厨房”，则不要套用 unknown 轻量普查，而是直接使用厨房精细化策略：

```text
厨房：考虑蒸汽/油烟误报，提高明火证据权重，要求连续帧或 fire/smoke 组合。
配电间：重视 smoke，使用更密集观察。
室外：提高阈值，避免反光/车灯误报。
```

这样可以同时支持：

```text
大量 unknown 流先省资源普查；
已知重点场景直接精细化检测。
```

## 下一阶段：自适应巡检调频

当前版本的 predict-wise 主要负责生成每一路视频流的初始检测参数；它不会在一次任务运行中持续调度同一路视频流。后续可以增加 adaptive patrol loop，用于长期巡检：

```text
10 路 unknown 视频流接入
  -> 第一轮使用 bulk_scout 轻量普查
  -> 没有检测到目标的流进入低频巡检
  -> 检测到疑似 fire/smoke 的流进入 burst follow-up
  -> burst follow-up 临时提高抽帧密度、延长检测时长、降低漏报风险
  -> 多轮无异常后回落到普通或低频巡检
```

这属于后续增强能力。当前实现只会在 `risk.suggested_action` 和 `risk.reasons` 中建议短时加密复检，不会自动再次调用检测 API。

## 历史经验影响

如果某路摄像头近期多次真实火情：

```text
提高优先级
延长检测时长
必要时降低阈值
```

如果某路摄像头近期误报频繁：

```text
提高置信度阈值
要求更多连续帧
在报告中解释误报风险
```

如果存在已审核经验：

```text
只在匹配 source_id 或 scene_type 时应用；
不要让未审核经验自动影响安全策略。
```

## 输出要求

每个 profile 必须包含 `reason`，用用户能理解的话解释为什么这样设置参数。
