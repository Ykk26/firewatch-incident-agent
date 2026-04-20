#!/usr/bin/env python3
"""Aggregate frame-level detections into video-level evidence."""

from __future__ import annotations

from typing import Any, Dict, List


def _continuous_hit_count(detections: List[Dict[str, Any]], frame_gap: int) -> int:
    if not detections:
        return 0
    frames = sorted({int(item.get("frame", 0)) for item in detections})
    best = current = 1
    previous = frames[0]
    for frame in frames[1:]:
        if frame - previous <= frame_gap:
            current += 1
        else:
            best = max(best, current)
            current = 1
        previous = frame
    return max(best, current)


def _trend_label(values: List[float], trend_delta: float, spike_margin: float) -> str:
    if len(values) < 2:
        return "insufficient"

    first = values[0]
    last = values[-1]
    peak = max(values)
    delta = last - first
    edge_peak = max(first, last)

    if peak - edge_peak >= spike_margin:
        return "spiky"
    if delta >= trend_delta:
        return "rising"
    if delta <= -trend_delta:
        return "falling"
    return "stable"


def _confidence_series(detections: List[Dict[str, Any]]) -> List[float]:
    by_frame: Dict[int, float] = {}
    for item in detections:
        frame = int(item.get("frame", 0))
        confidence = float(item.get("confidence", 0.0))
        by_frame[frame] = max(by_frame.get(frame, 0.0), confidence)
    return [by_frame[frame] for frame in sorted(by_frame)]


def _confidence_trend(detections: List[Dict[str, Any]], trend_delta: float, spike_margin: float) -> Dict[str, Any]:
    overall_series = _confidence_series(detections)
    by_class: Dict[str, Dict[str, Any]] = {}
    class_names = sorted({str(item.get("class_name", "unknown")) for item in detections})

    for class_name in class_names:
        class_series = _confidence_series(
            [item for item in detections if str(item.get("class_name", "unknown")) == class_name]
        )
        by_class[class_name] = _series_summary(class_series, trend_delta, spike_margin)

    return {
        **_series_summary(overall_series, trend_delta, spike_margin),
        "by_class": by_class,
    }


def _series_summary(values: List[float], trend_delta: float, spike_margin: float) -> Dict[str, Any]:
    if not values:
        return {
            "trend": "insufficient",
            "first_confidence": 0.0,
            "last_confidence": 0.0,
            "delta": 0.0,
            "peak_confidence": 0.0,
            "sample_count": 0,
        }

    first = values[0]
    last = values[-1]
    peak = max(values)
    return {
        "trend": _trend_label(values, trend_delta, spike_margin),
        "first_confidence": first,
        "last_confidence": last,
        "delta": last - first,
        "peak_confidence": peak,
        "sample_count": len(values),
    }


def aggregate_detection_result(
    result: Dict[str, Any],
    temporal_policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    temporal_policy = temporal_policy or {}
    continuous_frame_gap = int(temporal_policy.get("continuous_frame_gap", 60))
    trend_delta = float(temporal_policy.get("trend_delta", 0.15))
    spike_margin = float(temporal_policy.get("spike_margin", 0.2))
    detections = result.get("detections", []) or []
    confidences = [float(item.get("confidence", 0.0)) for item in detections]
    classes = sorted({str(item.get("class_name", "unknown")) for item in detections})
    frames = sorted({int(item.get("frame", 0)) for item in detections})
    class_counts: Dict[str, int] = {}
    class_max_confidence: Dict[str, float] = {}
    for item in detections:
        class_name = str(item.get("class_name", "unknown"))
        confidence = float(item.get("confidence", 0.0))
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
        class_max_confidence[class_name] = max(class_max_confidence.get(class_name, 0.0), confidence)

    frames_analyzed = result.get("frames_analyzed", result.get("sampled_frame_count", len(frames)))

    return {
        "frames_analyzed": int(frames_analyzed or 0),
        "hit_frame_count": len(frames),
        "max_frame_index": max(frames) if frames else 0,
        "hit_count": len(detections),
        "max_confidence": max(confidences) if confidences else 0.0,
        "classes": classes,
        "class_counts": class_counts,
        "class_max_confidence": class_max_confidence,
        "continuous_hit_count": _continuous_hit_count(detections, continuous_frame_gap),
        "continuous_frame_gap": continuous_frame_gap,
        "confidence_trend": _confidence_trend(detections, trend_delta, spike_margin),
        "evidence_frames": result.get("evidence_frames", []) or [],
        "raw_status": result.get("status", "unknown"),
        "raw_error": result.get("error"),
    }
