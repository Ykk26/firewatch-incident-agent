#!/usr/bin/env python3
"""Aggregate frame-level detections into video-level evidence."""

from __future__ import annotations

from typing import Any, Dict, List


def _continuous_hit_count(detections: List[Dict[str, Any]]) -> int:
    if not detections:
        return 0
    frames = sorted({int(item.get("frame", 0)) for item in detections})
    best = current = 1
    previous = frames[0]
    for frame in frames[1:]:
        if frame - previous <= 60:
            current += 1
        else:
            best = max(best, current)
            current = 1
        previous = frame
    return max(best, current)


def aggregate_detection_result(result: Dict[str, Any]) -> Dict[str, Any]:
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

    return {
        "frames_analyzed": max(frames) if frames else 0,
        "hit_count": len(detections),
        "max_confidence": max(confidences) if confidences else 0.0,
        "classes": classes,
        "class_counts": class_counts,
        "class_max_confidence": class_max_confidence,
        "continuous_hit_count": _continuous_hit_count(detections),
        "evidence_frames": result.get("evidence_frames", []) or [],
        "raw_status": result.get("status", "unknown"),
        "raw_error": result.get("error"),
    }
