# FireWatch 架构说明

FireWatch 是一个上层编排 skill，不替代原有火焰检测模型服务。

## 核心故事

基础模型偏图片能力：输入单帧图片，输出 fire/smoke 检测结果。

OpenClaw 负责把这个单帧能力升级为视频巡检能力：

```text
多路视频流
  -> 每路独立推理参数
  -> 多帧采样
  -> 时间连续性分析
  -> 风险研判
  -> 场景经验沉淀
  -> 下一次巡检策略优化
```

## 模块划分

- `Predict-wise Planner`：为每一路视频流生成独立推理 profile，而不是使用一套全局参数。
- `Fire Detection Client`：调用现有 `fire-detection` REST API。
- `Temporal Evidence Aggregator`：把帧级检测结果聚合为视频级证据。
- `Risk Assessor`：输出风险等级、误报风险和研判依据。
- `Scene Knowledge Evolver`：存储巡检观察、人工确认、误报和已审核经验。
- `Report Writer`：生成事件报告、巡检摘要和告警文本。

## OpenClaw 亮点

参赛时不要把重点放在“我们有一个火焰检测模型”，而是放在：

```text
OpenClaw 如何让基础模型会省资源、会看视频、会积累经验。
```

可以这样表达：

```text
检测模型是眼睛，FireWatch 是规划、研判和记忆。
```

## 与原 skill 的关系

`fire-detection`：

```text
底层检测能力，负责模型推理、证据帧生成、API 返回。
```

`firewatch-incident-agent`：

```text
上层编排能力，负责多路巡检、参数规划、多帧聚合、风险评估、知识演化和报告生成。
```

默认不要修改 `fire-detection`。只有用户明确要求改底层服务时，才进入原 skill。
