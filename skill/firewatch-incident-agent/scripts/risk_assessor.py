#!/usr/bin/env python3
"""Assess fire incident risk from temporal evidence and scene context."""

from __future__ import annotations

from typing import Any, Dict


HIGH_RISK_SCENES = {"warehouse", "electrical_room"}


def assess_risk(
    temporal_evidence: Dict[str, Any],
    scene_type: str,
    profile: Dict[str, Any],
    thresholds: Dict[str, Any],
) -> Dict[str, Any]:
    hit_count = int(temporal_evidence.get("hit_count", 0))
    max_confidence = float(temporal_evidence.get("max_confidence", 0.0))
    continuous_hits = int(temporal_evidence.get("continuous_hit_count", 0))
    classes = set(temporal_evidence.get("classes", []))
    class_counts = temporal_evidence.get("class_counts", {}) or {}
    class_max_confidence = temporal_evidence.get("class_max_confidence", {}) or {}
    fire_count = int(class_counts.get("fire", 0))
    smoke_count = int(class_counts.get("smoke", 0))
    fire_max_confidence = float(class_max_confidence.get("fire", 0.0))
    smoke_max_confidence = float(class_max_confidence.get("smoke", 0.0))
    guidance = profile.get("scene_reasoning_guidance", {}) or {}
    alert_bias = guidance.get("alert_bias", {}) or {}
    allow_transient_fire = bool(alert_bias.get("allow_transient_fire", True))
    require_temporal_for_smoke_only = bool(alert_bias.get("require_temporal_for_smoke_only", True))
    followup_on_transient = bool(alert_bias.get("followup_on_transient", True))

    reasons = []
    level = "none"
    false_positive_risk = "low"
    event_type = "none"
    suggested_action = "无需告警。"

    if hit_count == 0:
        return {
            "level": "none",
            "event_type": "none",
            "false_positive_risk": "low",
            "reasons": ["未返回 fire 或 smoke 检测结果。"],
            "suggested_action": suggested_action,
        }

    if max_confidence >= thresholds["high_confidence"]:
        reasons.append(f"最高置信度较高（{max_confidence:.2f}）。")
    elif max_confidence >= thresholds["medium_confidence"]:
        reasons.append(f"最高置信度中等（{max_confidence:.2f}）。")
    else:
        reasons.append(f"最高置信度偏低（{max_confidence:.2f}）。")

    if {"fire", "smoke"}.issubset(classes):
        reasons.append("采样帧中同时出现 fire 和 smoke。")
    elif "smoke" in classes:
        reasons.append("采样帧中出现 smoke。")
    elif "fire" in classes:
        reasons.append("采样帧中出现 fire。")

    if continuous_hits >= thresholds["continuous_hits_for_high"]:
        reasons.append(f"检测结果具有时间连续性（{continuous_hits} 个命中帧）。")
    elif continuous_hits >= thresholds["continuous_hits_for_medium"]:
        reasons.append(f"检测结果跨帧重复出现（{continuous_hits} 个命中帧）。")
    else:
        reasons.append("检测结果只出现在少量帧中。")

    if scene_type in HIGH_RISK_SCENES:
        reasons.append(f"{scene_type} 按高风险场景处理。")

    transient_fire_threshold = float(thresholds.get("transient_fire_confidence", 0.8))
    is_transient_fire = (
        allow_transient_fire
        and fire_count > 0
        and fire_max_confidence >= transient_fire_threshold
        and continuous_hits < thresholds["continuous_hits_for_medium"]
    )
    is_sustained = continuous_hits >= thresholds["continuous_hits_for_medium"]
    has_fire_and_smoke = {"fire", "smoke"}.issubset(classes)
    smoke_only_requires_temporal = "smoke" in classes and "fire" not in classes and require_temporal_for_smoke_only

    if is_transient_fire:
        event_type = "transient_fire"
        reasons.append("出现单帧或短时高置信度 fire，按突发型明火证据处理，不因缺少连续帧而丢弃。")
        if scene_type in HIGH_RISK_SCENES:
            level = "high"
            false_positive_risk = "medium"
        elif scene_type == "outdoor":
            level = "medium"
            false_positive_risk = "medium"
        else:
            level = "medium"
            false_positive_risk = "medium"
        suggested_action = "建议快速人工复核，并启动短时加密复检。"
        if followup_on_transient:
            reasons.append("建议触发 burst follow-up：短时间内提高抽帧密度复检。")
    elif (
        max_confidence >= thresholds["high_confidence"]
        and continuous_hits >= thresholds["continuous_hits_for_high"]
    ) or (has_fire_and_smoke and scene_type in HIGH_RISK_SCENES):
        event_type = "sustained_fire_or_smoke"
        level = "high"
        false_positive_risk = "low"
        suggested_action = "建议立即人工复核，并按现场预案升级处置。"
    elif max_confidence >= thresholds["medium_confidence"] or continuous_hits >= thresholds["continuous_hits_for_medium"]:
        event_type = "sustained_fire_or_smoke" if is_sustained else "possible_false_positive"
        if smoke_only_requires_temporal and smoke_count > 0 and continuous_hits < thresholds["continuous_hits_for_medium"]:
            level = "low"
            false_positive_risk = "high"
            reasons.append("该场景 smoke 单独出现需要时间连续性确认。")
            suggested_action = "建议记录并复核，必要时短时加密复检。"
        else:
            level = "medium"
            false_positive_risk = "medium"
            suggested_action = "建议人工复核，并结合现场情况判断是否升级。"
    else:
        event_type = "possible_false_positive"
        level = "low"
        false_positive_risk = "high"
        suggested_action = "建议记录为低风险疑似异常，后续结合人工反馈修正画像。"

    if scene_type == "outdoor" and continuous_hits < thresholds["continuous_hits_for_medium"]:
        false_positive_risk = "high"
        reasons.append("室外单帧 fire-like 命中常见于反光或车灯，误报风险较高。")
    if scene_type == "kitchen" and "smoke" in classes and "fire" not in classes:
        false_positive_risk = "medium"
        reasons.append("厨房蒸汽可能模拟 smoke，需要人工复核。")

    return {
        "level": level,
        "event_type": event_type,
        "false_positive_risk": false_positive_risk,
        "reasons": reasons,
        "suggested_action": suggested_action,
    }
