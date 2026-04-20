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

    reasons = []
    level = "none"
    false_positive_risk = "low"

    if hit_count == 0:
        return {
            "level": "none",
            "false_positive_risk": "low",
            "reasons": ["No fire or smoke detections were returned."],
        }

    if max_confidence >= thresholds["high_confidence"]:
        reasons.append(f"Maximum confidence is high ({max_confidence:.2f}).")
    elif max_confidence >= thresholds["medium_confidence"]:
        reasons.append(f"Maximum confidence is moderate ({max_confidence:.2f}).")
    else:
        reasons.append(f"Maximum confidence is low ({max_confidence:.2f}).")

    if {"fire", "smoke"}.issubset(classes):
        reasons.append("Fire and smoke both appear in the sampled frames.")
    elif "smoke" in classes:
        reasons.append("Smoke appears in the sampled frames.")
    elif "fire" in classes:
        reasons.append("Fire appears in the sampled frames.")

    if continuous_hits >= thresholds["continuous_hits_for_high"]:
        reasons.append(f"Detections are temporally continuous ({continuous_hits} hit frames).")
    elif continuous_hits >= thresholds["continuous_hits_for_medium"]:
        reasons.append(f"Detections repeat across frames ({continuous_hits} hit frames).")
    else:
        reasons.append("Detection is isolated to a small number of frames.")

    if scene_type in HIGH_RISK_SCENES:
        reasons.append(f"{scene_type} is treated as a high-risk scene.")

    if (
        max_confidence >= thresholds["high_confidence"]
        and continuous_hits >= thresholds["continuous_hits_for_high"]
    ) or ({"fire", "smoke"}.issubset(classes) and scene_type in HIGH_RISK_SCENES):
        level = "high"
        false_positive_risk = "low"
    elif max_confidence >= thresholds["medium_confidence"] or continuous_hits >= thresholds["continuous_hits_for_medium"]:
        level = "medium"
        false_positive_risk = "medium"
    else:
        level = "low"
        false_positive_risk = "high"

    if scene_type == "outdoor" and continuous_hits < thresholds["continuous_hits_for_medium"]:
        false_positive_risk = "high"
        reasons.append("Outdoor single-frame fire-like hits are often caused by glare or headlights.")
    if scene_type == "kitchen" and "smoke" in classes and "fire" not in classes:
        false_positive_risk = "medium"
        reasons.append("Kitchen steam can mimic smoke, so human verification is needed.")

    return {
        "level": level,
        "false_positive_risk": false_positive_risk,
        "reasons": reasons,
    }
