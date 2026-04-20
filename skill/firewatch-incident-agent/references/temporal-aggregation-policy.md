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

厨房：

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
