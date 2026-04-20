# 自然语言请求整理流程

用户的真实输入通常不是 JSON，而是类似：

```text
帮我看一下这几个流：
rtsp://10.0.0.1/live
rtsp://10.0.0.2/live 这个可能是厨房
rtsp://10.0.0.3/live 可能是室外通道
```

OpenClaw 应先把它整理成临时 patrol request，再交给脚本执行。用户不需要知道或手写 patrol request；它只是 OpenClaw 与脚本之间的稳定接口。

`hints` 是内部中间字段，用来保存从自然语言中抽取出的弱线索。它不是用户必须提供的输入，也不能被当成确定事实。

## 整理规则

1. 提取所有视频流地址：`rtsp://`、`rtmp://`、`.flv`、`.m3u8`。
2. 为每路生成稳定 `source_id`。如果用户没有提供名称，使用 `stream-1`、`stream-2`。
3. 场景是可选信息。用户没说时，设置 `scene_type: "unknown"`。
4. 用户说“可能是厨房/后厨/室外/配电间/仓库”等，不要直接当事实；由 OpenClaw 写入 `hints.location_hint` 或 `hints.user_label`。
5. 不要在 patrol request 中写检测结果。检测结果必须来自检测 API 返回。

## 示例

用户输入：

```text
检查这三路：
rtsp://cam-a/live
rtsp://cam-b/live 这个可能是厨房
rtsp://cam-c/live 可能是室外通道
```

整理为：

```json
{
  "mode": "patrol",
  "resource_budget": "balanced",
  "targets": [
    {
      "source_id": "stream-1",
      "stream_url": "rtsp://cam-a/live",
      "scene_type": "unknown",
      "hints": {}
    },
    {
      "source_id": "stream-2",
      "stream_url": "rtsp://cam-b/live",
      "scene_type": "unknown",
      "hints": {
        "location_hint": "用户说可能是厨房"
      }
    },
    {
      "source_id": "stream-3",
      "stream_url": "rtsp://cam-c/live",
      "scene_type": "unknown",
      "hints": {
        "location_hint": "用户说可能是室外通道"
      }
    }
  ]
}
```

## 场景知识使用

在生成 predict-wise profile 前，结合：

- OpenClaw 从用户自然语言中抽取出的 `hints`
- `config.json` 的 `scene_reasoning_guidance`
- `knowledge/lessons_learned.jsonl` 中已审核经验

例如厨房线索：

```text
厨房可能有蒸汽和油烟误报；
因此 smoke 单独出现时不应直接高等级告警；
应提升明火证据权重，并要求多帧连续性或 fire/smoke 组合。
```

这些分析应进入 profile 的 `reason` 或报告说明，而不是写成检测事实。

## 大批量输入

如果用户一次性提交很多路视频流，并且没有逐路描述场景：

```text
使用 patrol_mode=bulk_scout；
unknown 流先轻量普查；
用户明确提到厨房、配电间、仓库等场景的流，直接使用对应场景策略。
```

用户输入示例：

```text
帮我巡检这 30 路流，大部分不知道场景，第三路可能是厨房，第十一路可能是配电间。
```

整理时：

```text
没有场景的流：scene_type=unknown, hints={}
第三路：OpenClaw 抽取 hints.location_hint=用户说可能是厨房
第十一路：OpenClaw 抽取 hints.location_hint=用户说可能是配电间
patrol_mode=bulk_scout
```

## 重新开始任务

如果用户先输入 3 路，之后重新开始任务并输入 5 路：

```text
OpenClaw 应尽量保持已有 source_id；
如果 source_id 变化，也可以通过 stream_url_hash 复用历史 camera profile；
新增流按 unknown 或本次自然语言抽取出的 hints 处理。
```

示例：

```text
第一轮：stream-1、stream-2、stream-3
第二轮：stream-1、stream-2、stream-3、stream-4、stream-5
```

第二轮中前三路会读取历史 camera profile，后两路从当前输入重新推断。
