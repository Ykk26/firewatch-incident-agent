# 多路径证据聚合策略

多帧聚合不是“连续帧过滤器”。FireWatch 不应因为缺少多帧连续证据就丢弃单帧高置信度明火。

## 原则

```text
多帧连续是增强证据；
单帧高置信度 fire 是突发证据；
低置信度且符合场景误报规律的结果是疑似误报证据。
```

## 三条证据路径

`transient_fire`

```text
单帧或短时高置信度 fire。
不因缺少连续帧而忽略。
建议快速人工复核，并启动短时加密复检。
```

`sustained_fire_or_smoke`

```text
多帧连续 fire/smoke，或 fire + smoke 组合。
用于判断持续火情、烟雾扩散或正在发展的风险。
```

`possible_false_positive`

```text
单帧低置信度 fire-like、厨房单独 smoke、室外反光/车灯等。
降低告警等级，但记录为可复核事件。
```

## 场景化决策

场景化决策不应写死在 `risk_assessor.py` 中。代码只读取 `profile.scene_reasoning_guidance`，具体场景知识由 `config.json`、`lessons_learned` 和 camera profile 提供。

连续帧判断的距离阈值不应写死在聚合脚本中，应由 `config.json` 的 `temporal_policy.continuous_frame_gap` 控制。

置信度趋势也属于视频级证据。聚合脚本应根据 `temporal_policy.trend_delta` 和 `temporal_policy.spike_margin` 输出 `confidence_trend`：

```text
rising：采样窗口内置信度整体增强；
falling：采样窗口内置信度整体下降；
stable：置信度波动不大；
spiky：单点尖峰，前后不持续；
insufficient：命中帧不足，无法判断趋势。
```

场景权重必须参与风险计算。`alert_bias.fire_weight` 和 `alert_bias.smoke_weight` 用于把模型返回的类别置信度转换为视频级有效证据分；例如厨房可以提高 fire 证据权重并降低 smoke 单独证据，配电间可以提高 smoke 证据权重。

配置示例：

```json
{
  "scene_reasoning_guidance": {
    "kitchen": {
      "common_false_positive_patterns": ["蒸汽", "油烟"],
      "policy": "厨房 smoke 容易误报，应提高明火证据权重。",
      "alert_bias": {
        "allow_transient_fire": true,
        "require_temporal_for_smoke_only": true
      },
      "risk_rules": {
        "transient_fire_level": "medium",
        "smoke_only_false_positive_risk": "medium"
      }
    }
  }
}
```

厨房策略可以表达为：

```text
smoke 可能来自蒸汽或油烟，单独 smoke 不直接高等级告警；
高置信度 fire 仍进入 transient_fire；
fire + smoke 或连续 fire/smoke 才升级。
```

室外：

```text
单帧低/中置信度 fire-like 可能来自反光或车灯；
单帧高置信度 fire 进入 transient_fire 并建议短时加密复检；
连续 fire 或 fire + smoke 才升级。
```

配电间：

```text
smoke 权重更高；
连续 smoke 即使置信度不高也应复核；
单帧 fire 进入快速复核路径。
```

仓库：

```text
连续 fire 或 fire + smoke 高优先级；
单帧高置信度 fire 进入 transient_fire，建议快速复核。
```

## 输出要求

风险输出应包含：

```text
event_type
risk level
false_positive_risk
reasons
suggested_action
```
