# 事件 Schema

事件对象用于统一承载一次视频流巡检或火情研判结果。报告、告警、知识存储都应尽量复用这个结构，避免同一事件在不同模块里字段不一致。

## 标准结构

```json
{
  "incident_id": "fire-20260420-143210-warehouse-east",
  "source_id": "warehouse-east",
  "source_url": "rtsp://camera/warehouse-east",
  "scene_type": "warehouse",
  "declared_scene_type": "unknown",
  "predict_profile": {
    "confidence": 0.35,
    "duration": 30,
    "interval": 1.0,
    "priority": "high",
    "declared_scene_type": "unknown",
    "scene_confidence": 0.65,
    "camera_profile_basis": "未提供明确场景，根据线索“仓库”使用 warehouse 倾向策略。",
    "hints": {
      "location_hint": "仓库东门附近",
      "risk_zone": "high"
    },
    "reason": "未提供明确场景，根据线索“仓库”使用 warehouse 倾向策略。仓库区域火势扩散影响更高，因此检测时间更长、抽帧更密。"
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
    "event_type": "sustained_fire_or_smoke",
    "false_positive_risk": "low",
    "reasons": [],
    "suggested_action": "建议立即人工复核，并按现场预案升级处置。"
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
当前巡检采用的有效场景类型，可能来自明确标注，也可能来自弱线索推断。
```

`declared_scene_type`：

```text
用户或系统显式提供的场景类型。没有明确场景时为 unknown。
```

`predict_profile`：

```text
OpenClaw 为该路视频流生成的推理参数。必须包含 reason，解释为什么这样设置。
```

`predict_profile.scene_confidence`：

```text
当前 camera profile 对有效场景的置信度。它表示策略依据强弱，不表示火情检测置信度。
```

`predict_profile.camera_profile_basis`：

```text
说明 effective scene 是如何得到的，例如显式标注、室内外线索、位置关键词或 unknown 默认策略。
```

`temporal_evidence`：

```text
多帧聚合后的证据摘要，不是单帧裸输出。
```

`risk`：

```text
风险等级、事件类型、误报风险、判断依据和建议动作。报告和告警应优先展示这一部分。
```

`risk.event_type`：

```text
证据路径：transient_fire、sustained_fire_or_smoke、possible_false_positive 或 none。
```

`knowledge_refs`：

```text
关联的消防知识、历史经验或复盘记录。
```
