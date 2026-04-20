# 事件 Schema

事件对象用于统一承载一次视频流巡检或火情研判结果。报告、告警、知识存储都应尽量复用这个结构，避免同一事件在不同模块里字段不一致。

## 标准结构

```json
{
  "incident_id": "fire-20260420-143210-warehouse-east",
  "source_id": "warehouse-east",
  "source_url": "rtsp://camera/warehouse-east",
  "scene_type": "warehouse",
  "predict_profile": {
    "confidence": 0.35,
    "duration": 30,
    "interval": 1.0,
    "priority": "high",
    "reason": "仓库为高风险区域，因此检测时间更长、抽帧更密。"
  },
  "temporal_evidence": {
    "frames_analyzed": 30,
    "hit_count": 5,
    "max_confidence": 0.91,
    "classes": ["fire", "smoke"],
    "continuous_hit_count": 3,
    "evidence_frames": []
  },
  "risk": {
    "level": "high",
    "false_positive_risk": "low",
    "reasons": []
  },
  "knowledge_refs": [],
  "created_at": "2026-04-20T14:32:10+08:00"
}
```

## 字段说明

`incident_id`：

```text
事件唯一 ID。建议包含时间、source_id 和短随机后缀。
```

`source_id`：

```text
摄像头或视频流的业务标识，例如 warehouse-east、power-room-01。
```

`scene_type`：

```text
场景类型，例如 warehouse、electrical_room、kitchen、outdoor、unknown。
```

`predict_profile`：

```text
OpenClaw 为该路视频流生成的推理参数。必须包含 reason，解释为什么这样设置。
```

`temporal_evidence`：

```text
多帧聚合后的证据摘要，不是单帧裸输出。
```

`risk`：

```text
风险等级、误报风险和判断依据。报告和告警应优先展示这一部分。
```

`knowledge_refs`：

```text
关联的消防知识、历史经验或复盘记录。
```
