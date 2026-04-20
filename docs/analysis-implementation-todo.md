# FireWatch Skill 初版分析、实现方案与 Todo

## 一、分析报告

项目已经具备一个清晰方向：不要把参赛重点放在“我们有一个火焰检测模型”，而是放在 OpenClaw 如何把火焰/烟雾检测 API 编排成一个会省资源、会看视频、会积累经验的巡检 Agent。

新 skill 的目标是把“单帧图片检测能力”升级成“多路视频火情巡检 Agent”。后端可以接任意火焰/烟雾检测服务，FireWatch 负责策略、研判、报告和知识演化。

核心叙事：

```text
基础模型只会看单张图片；
OpenClaw 让它会管理多路视频、会节省推理资源、会做多帧研判、会积累不同场景的经验。
```

参赛故事建议聚焦三点：

1. **predict-wise 节省资源**

   不同摄像头不使用同一套参数，而是按场景、历史误报、风险等级和资源预算，为每一路视频流生成独立推理策略。高风险区域精检，低风险区域轻检，误报多的区域更谨慎。

2. **多帧视频研判降低误报**

   基础模型输出的是单帧结果。OpenClaw 聚合多帧检测，分析连续性、类别组合和置信度趋势。单帧高置信度不一定直接告警，连续低置信度也可能升级为风险事件。

3. **场景知识智能迭代**

   每次真实火情、误报、演练和人工复核都沉淀为场景经验。仓库积累仓库经验，配电间积累配电间经验，室外场景积累反光/车灯等误报规律，再反向优化后续 predict-wise 参数和风险判断。

因此，新 skill 的定位应该是：

```text
firewatch-incident-agent = 火情巡检编排、视频级研判、知识演化与报告生成 Agent
```

## 二、实现方案

### 1. 目录策略

采用“项目开发目录 + skill 发布目录”的方式：

```text
projects/firewatch-incident-agent/
  skill/firewatch-incident-agent/    # skill 源码，开发源头
  tools/                             # 同步脚本
  examples/                          # raw 输入示例
  docs/                              # 中文分析、方案、参赛叙事

skills/firewatch-incident-agent/     # 同步后的 OpenClaw skill 目录
```

开发时只改 `projects/firewatch-incident-agent/skill/firewatch-incident-agent/`，然后通过同步脚本发布到 `skills/firewatch-incident-agent/`。

### 2. 初版模块

初版包含以下能力：

```text
Predict-wise Planner
  为每路视频生成独立推理参数。

Fire Detection Client
  调用火焰/烟雾检测 API 或视觉模型服务。

Temporal Evidence Aggregator
  将单帧检测结果聚合成视频级证据。

Risk Assessor
  输出风险等级、误报风险和判断依据。

Scene Knowledge Store
  记录巡检观察、确认案例、待审核经验和已审核经验。

Report Writer
  生成事件报告和巡检摘要。

Orchestrator
  串联以上模块，形成初版巡检工作流。
```

### 3. 核心数据流

```text
用户巡检请求
  -> 解析多路视频流和场景
  -> predict-wise 生成每路推理参数
  -> 调用火焰/烟雾检测服务
  -> 聚合多帧检测结果
  -> 风险分级与误报判断
  -> 生成报告/告警摘要
  -> 写入 observations
  -> 用户确认后进入案例库或待审核经验库
```

### 4. predict-wise 设计

真实业务里不一定能拿到每个摄像头的准确场景。因此 predict-wise 不应该强依赖 `scene_type`，而是先构建 camera profile。

每路视频流先形成一个 camera profile：

```json
{
  "source_id": "warehouse-east",
  "declared_scene_type": "unknown",
  "effective_scene_type": "warehouse",
  "scene_confidence": 0.65,
  "hints": {
    "location_hint": "仓库东门附近",
    "risk_zone": "high"
  },
  "basis": "未提供明确场景，根据线索“仓库”使用 warehouse 倾向策略。"
}
```

再生成 predict profile：

```json
{
  "source_id": "warehouse-east",
  "scene_type": "warehouse",
  "declared_scene_type": "unknown",
  "scene_confidence": 0.65,
  "confidence": 0.35,
  "duration": 30,
  "interval": 1.0,
  "priority": "high",
  "reason": "未提供明确场景，根据线索“仓库”使用 warehouse 倾向策略。仓库区域火势扩散影响更高，因此检测时间更长、抽帧更密。"
}
```

规划依据：

```text
显式场景：
  如果用户或系统已经明确标注，则直接采用。

弱线索：
  由 OpenClaw 从用户自然语言中抽取，例如室内/室外、区域名称、用户标签、风险区域、备注关键词。
  这是内部中间信息，不要求用户手写 hints JSON。

资源预算：
  fast、balanced、thorough。

历史经验：
  历史真实火情、历史误报、已审核经验。

人工约束：
  ROI、指定时长、指定阈值。
```

默认逻辑：

```text
如果没有明确场景，也没有可用线索，使用 unknown 默认策略；
后续通过巡检记录、人工确认和知识迭代逐步修正 camera profile。
```

### 5. 多帧视频研判

基础模型只回答：

```text
这一帧有没有 fire/smoke？
```

OpenClaw 聚合后回答：

```text
异常是否连续出现？
是否同时有 fire 和 smoke？
置信度是否持续上升？
是否符合该场景历史误报规律？
是否需要升级为中/高风险？
```

典型判断：

```text
单帧 fire 0.72，后续无异常
  -> 可能是反光或火花，降低告警等级。

多帧 fire 0.42、0.48、0.53，并伴随 smoke
  -> 虽然单帧置信度不高，但连续出现，升级为中/高风险。
```

### 5.1 下一阶段：自适应巡检调频

当前初版已经能在任务开始前根据 unknown、场景线索、历史画像和资源预算生成 predict-wise 初始策略，但还没有实现任务运行中的动态调频。下一阶段可以增加 adaptive patrol loop：

```text
大量 unknown 视频流接入
  -> 第一轮使用 bulk_scout 轻量普查
  -> 连续没有检测到 fire/smoke 的流，下调巡检频率或延长下一轮间隔
  -> 检测到疑似 fire/smoke 的流，进入 burst follow-up，提高抽帧密度并延长观察时间
  -> 风险消退后回落到普通巡检
  -> 被人工确认为真实火情、误报或演练后，写入知识库并影响后续 camera profile
```

这个能力适合放在后续版本中实现，不应在当前 skill 文档中暗示已经自动执行。当前版本只生成初始 predict-wise profile，并在检测后给出 follow-up 建议和知识更新。

### 6. 知识智能迭代

知识存储采用分层 JSONL：

```text
knowledge/observations.jsonl
  每次巡检观察。

knowledge/incident_cases.jsonl
  用户确认后的真实火情、误报、演练案例。

knowledge/pending_review.jsonl
  从复盘中提取的待审核经验。

knowledge/lessons_learned.jsonl
  审核通过后可影响后续推理策略的经验。

knowledge/source_index.json
  知识来源和审核策略。
```

原则：

```text
新经验不能直接影响安全判断；
必须先进入 pending_review；
审核通过后才进入 lessons_learned；
predict-wise 只读取已审核经验。
```

## 三、Todo 列表

### Phase 1：初版骨架

- [x] 建立项目开发目录 `projects/firewatch-incident-agent`
- [x] 建立 skill 源目录 `skill/firewatch-incident-agent`
- [x] 建立发布目录 `skills/firewatch-incident-agent`
- [x] 编写 `SKILL.md`
- [x] 编写 `config.json`
- [x] 增加 `agents/openai.yaml`
- [x] 增加架构、schema、predict-wise、知识演化参考文档

### Phase 2：基础编排脚本

- [x] 实现 `predict_planner.py`
- [x] 实现 `fire_detection_client.py`
- [x] 实现 `temporal_aggregator.py`
- [x] 实现 `risk_assessor.py`
- [x] 实现 `knowledge_store.py`
- [x] 实现 `report_writer.py`
- [x] 实现 `orchestrator.py`
- [x] 增加三路 raw 巡检输入示例
- [x] 增加五路 raw 巡检输入示例
- [x] 增加真实巡检运行脚本
- [x] 增加 PlanOnly 参数用于只查看检测前策略
- [x] 增加 bulk_scout 大批量未知流轻量普查策略
- [x] 支持大批量 unknown 与已知厨房/配电间等精细化场景并存
- [x] 增加 camera_profiles.json 运行态摄像头画像存储
- [x] 支持跨任务通过 source_id 或 stream_url_hash 复用历史画像
- [x] 增加多路径证据聚合策略：transient_fire、sustained_fire_or_smoke、possible_false_positive
- [x] 支持单帧高置信度 fire 触发快速复核，而不是被多帧规则过滤
- [x] 增加 confidence_trend，支持 rising、falling、stable、spiky、insufficient 趋势研判
- [x] 通过 Python 编译检查
- [x] 通过 skill 校验

### Phase 3：同步开发机制

- [x] 增加 `tools/sync-skill.ps1`
- [x] 增加 `tools/watch-sync-skill.ps1`
- [x] 支持项目目录到 skill 目录同步
- [x] 排除 `outputs`、`__pycache__`、运行时 JSONL 等产物

### Phase 4：下一步增强

- [ ] 增加“用户确认真实火情/误报/演练”的命令入口
- [ ] 自动从用户确认中提取 candidate lesson
- [ ] 将 candidate lesson 写入 `pending_review.jsonl`
- [ ] 增加审核通过后写入 `lessons_learned.jsonl`
- [ ] 让 predict-wise 读取已审核经验并解释参数变化
- [ ] 增加资源节省指标：统一参数 vs predict-wise 推理帧数对比
- [ ] 设计 adaptive patrol loop：大量 unknown 流先 bulk_scout，长期无目标流降频，疑似异常流 burst follow-up 加密复检
- [ ] 为 adaptive patrol loop 增加状态字段：last_seen_target_at、quiet_rounds、followup_until、current_patrol_tier
- [ ] 接入真实火焰/烟雾检测服务做端到端视频流测试
- [ ] 生成飞书告警文本或卡片
- [ ] 接入 `fire-knowledge-search` 和 `fire-knowledge-review`
- [ ] 准备参赛 demo 脚本和演示材料

## 四、参赛表达

一句话定位：

```text
FireWatch 复用基础图片检测模型，通过 OpenClaw 的 skill 编排能力，实现多路视频流 predict-wise 推理调度、多帧证据聚合、场景化知识迭代和火情报告生成，把单帧检测升级为可持续进化的视频巡检 Agent。
```

三句话卖点：

```text
省资源：
predict-wise 为每路视频流生成独立推理策略，高风险精检，低风险轻检。

更可靠：
OpenClaw 通过多帧聚合降低单帧误报，也能发现低置信度连续异常。

会进化：
每次真实火情、误报和人工复核都会沉淀为场景经验，反向优化后续巡检策略。
```

最终叙事：

```text
模型是眼睛，OpenClaw 是规划、研判和记忆。
```
