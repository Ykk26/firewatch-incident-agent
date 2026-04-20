# FireWatch Skill 初版分析、实现方案与 Todo

## 一、分析报告

现有 `fire-detection` skill 已经能完成底层火焰/烟雾检测闭环：调用 YOLO 检测服务，处理图片或视频流，并返回检测结果和证据帧。它适合作为底层“视觉推理能力”，但如果作为 skill 案例大赛作品，亮点容易落在模型和 FastAPI 服务上，而不是 OpenClaw。

新 skill 的目标不是替代 `fire-detection`，而是在它上面增加一个 OpenClaw 编排层，把“单帧图片检测能力”升级成“多路视频火情巡检 Agent”。

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

原 `fire-detection` 的定位保持不变：

```text
fire-detection = 底层火焰/烟雾检测服务封装
```

## 二、实现方案

### 1. 目录策略

采用“项目开发目录 + skill 发布目录”的方式：

```text
projects/firewatch-incident-agent/
  skill/firewatch-incident-agent/    # skill 源码，开发源头
  tools/                             # 同步脚本
  examples/                          # dry-run 示例
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
  调用原 fire-detection 服务，不修改原 skill。

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
  -> 调用 fire-detection 检测服务
  -> 聚合多帧检测结果
  -> 风险分级与误报判断
  -> 生成报告/告警摘要
  -> 写入 observations
  -> 用户确认后进入案例库或待审核经验库
```

### 4. predict-wise 设计

每路视频流生成一个 profile：

```json
{
  "source_id": "warehouse-east",
  "scene_type": "warehouse",
  "confidence": 0.35,
  "duration": 30,
  "interval": 1.0,
  "priority": "high",
  "reason": "仓库为高风险区域，因此检测时间更长、抽帧更密。"
}
```

规划依据：

```text
场景类型：
  仓库、配电间、厨房、室外、未知场景。

资源预算：
  fast、balanced、thorough。

历史经验：
  历史真实火情、历史误报、已审核经验。

人工约束：
  ROI、指定时长、指定阈值。
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
- [x] 增加 dry-run 示例
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
- [ ] 接入真实 `fire-detection` 服务做端到端视频流测试
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
