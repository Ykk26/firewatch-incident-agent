#!/usr/bin/env python3
"""Render FireWatch incident and patrol reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List


SKILL_DIR = Path(__file__).resolve().parents[1]


def _bullet(items: Iterable[str]) -> str:
    values = list(items)
    if not values:
        return "- None"
    return "\n".join(f"- {item}" for item in values)


def _format_confidence_trend(trend: Dict[str, Any]) -> str:
    if not trend:
        return "insufficient"
    label = trend.get("trend", "insufficient")
    first = float(trend.get("first_confidence", 0.0))
    last = float(trend.get("last_confidence", 0.0))
    peak = float(trend.get("peak_confidence", 0.0))
    delta = float(trend.get("delta", 0.0))
    return f"{label} (first={first:.2f}, last={last:.2f}, peak={peak:.2f}, delta={delta:.2f})"


def render_incident_report(event: Dict[str, Any]) -> str:
    template = (SKILL_DIR / "templates" / "incident_report.md").read_text(encoding="utf-8")
    profile = event["predict_profile"]
    evidence = event["temporal_evidence"]
    risk = event["risk"]
    weighted_evidence = risk.get("weighted_evidence", {}) or {}
    return template.format(
        incident_id=event["incident_id"],
        source_id=event["source_id"],
        scene_type=event["scene_type"],
        risk_level=risk["level"],
        event_type=risk.get("event_type", "unknown"),
        false_positive_risk=risk["false_positive_risk"],
        confidence=profile["confidence"],
        duration=profile["duration"],
        interval=profile["interval"],
        priority=profile["priority"],
        profile_reason=profile["reason"],
        frames_analyzed=evidence["frames_analyzed"],
        hit_frame_count=evidence.get("hit_frame_count", 0),
        max_frame_index=evidence.get("max_frame_index", 0),
        hit_count=evidence["hit_count"],
        continuous_hit_count=evidence["continuous_hit_count"],
        continuous_frame_gap=evidence.get("continuous_frame_gap", 0),
        confidence_trend=_format_confidence_trend(evidence.get("confidence_trend", {})),
        max_confidence=f"{evidence['max_confidence']:.2f}",
        effective_confidence=f"{weighted_evidence.get('effective_confidence', evidence['max_confidence']):.2f}",
        fire_weight=f"{weighted_evidence.get('fire_weight', 1.0):.2f}",
        smoke_weight=f"{weighted_evidence.get('smoke_weight', 1.0):.2f}",
        classes=", ".join(evidence["classes"]) or "none",
        risk_reasons=_bullet(risk["reasons"]),
        suggested_action=risk.get("suggested_action", "Verify the scene with on-site staff."),
        evidence_frames=_bullet(evidence["evidence_frames"]),
    )


def render_patrol_summary(patrol_id: str, events: List[Dict[str, Any]]) -> str:
    template = (SKILL_DIR / "templates" / "patrol_summary.md").read_text(encoding="utf-8")
    abnormal = [event for event in events if event["risk"]["level"] in {"low", "medium", "high", "critical"}]
    rows = []
    for event in events:
        rows.append(
            f"- {event['source_id']} ({event['scene_type']}): "
            f"{event['risk']['level']}, max_conf={event['temporal_evidence']['max_confidence']:.2f}"
        )
    strategy = "Predict-wise profiles inspected higher-risk scenes more densely and lower-risk scenes more lightly."
    updates = "Observations were written for each inspected stream."
    return template.format(
        patrol_id=patrol_id,
        stream_count=len(events),
        abnormal_count=len(abnormal),
        result_rows="\n".join(rows) or "- No streams inspected",
        resource_strategy=strategy,
        knowledge_updates=updates,
    )


def write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)
