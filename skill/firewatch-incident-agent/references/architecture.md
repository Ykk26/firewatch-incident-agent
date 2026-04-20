# FireWatch 架构说明

FireWatch 是一个面向火情视频巡检的编排 skill。它不绑定某个具体模型实现，而是把火焰/烟雾检测服务包装成可解释、可复盘、可演化的巡检工作流。

## 核心故事

基础模型偏图片能力：输入单帧图片，输出 fire/smoke 检测结果。

OpenClaw 负责把这个单帧能力升级为视频巡检能力：

```text
多路视频流
  -> camera profile 构建
  -> 每路独立推理参数
  -> 多帧采样
  -> 时间连续性分析
  -> 风险研判
  -> 场景经验沉淀
  -> 下一次巡检策略优化
```

## 模块划分

- `Predict-wise Planner`：先基于弱线索和历史经验构建 camera profile，再为每一路视频流生成独立推理 profile。
- `Fire Detection Client`：调用火焰/烟雾检测 API 或视觉模型服务。
- `Temporal Evidence Aggregator`：把帧级检测结果聚合为视频级证据。
- `Risk Assessor`：输出风险等级、误报风险和研判依据。
- `Scene Knowledge Evolver`：存储巡检观察、人工确认、误报和已审核经验。
- `Report Writer`：生成事件报告、巡检摘要和告警文本。

## OpenClaw 亮点

参赛时不要把重点放在“我们有一个火焰检测模型”，而是放在：

```text
OpenClaw 如何让基础模型会省资源、会看视频、会积累经验。
```

真实业务里不要求一开始知道每个摄像头的准确场景。FireWatch 可以从 unknown 默认策略开始，根据区域名称、室内外线索、用户反馈和历史观察逐步形成摄像头画像。

可以这样表达：

```text
检测模型是眼睛，FireWatch 是规划、研判和记忆。
```

## 与检测服务的关系

FireWatch 默认把检测能力视为外部服务：

```text
检测服务负责模型推理、证据帧生成和 API 返回；
FireWatch 负责多路巡检、参数规划、多帧聚合、风险评估、知识演化和报告生成。
```

这样做的好处是检测模型可以独立升级，FireWatch 的巡检策略、报告和知识演化逻辑可以保持稳定。
