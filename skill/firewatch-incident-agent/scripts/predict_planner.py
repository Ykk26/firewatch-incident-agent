#!/usr/bin/env python3
"""Build predict-wise inference profiles for FireWatch streams."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from camera_profile_store import find_profile, load_profiles


SKILL_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _budget_adjust(profile: Dict[str, Any], budget: str) -> Dict[str, Any]:
    adjusted = copy.deepcopy(profile)
    if budget == "fast":
        adjusted["duration"] = max(5, int(adjusted["duration"] * 0.6))
        adjusted["interval"] = round(float(adjusted["interval"]) * 1.5, 2)
        adjusted["confidence"] = min(0.9, round(float(adjusted["confidence"]) + 0.08, 2))
        adjusted["reason"] += " fast 预算会缩短检测时间并提高阈值。"
    elif budget == "thorough":
        adjusted["duration"] = int(adjusted["duration"] * 1.4)
        adjusted["interval"] = max(0.5, round(float(adjusted["interval"]) * 0.75, 2))
        adjusted["confidence"] = max(0.2, round(float(adjusted["confidence"]) - 0.05, 2))
        adjusted["reason"] += " thorough 预算会延长检测时间并提高抽帧密度。"
    return adjusted


def _patrol_mode_adjust(profile: Dict[str, Any], patrol_mode: str, scene_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    mode_config = config.get("patrol_modes", {}).get(patrol_mode, {})
    adjusted = copy.deepcopy(profile)
    if not mode_config:
        return adjusted

    if patrol_mode == "bulk_scout":
        if mode_config.get("unknown_only", True) and scene_type != "unknown":
            adjusted["reason"] += " 当前流已有场景线索，跳过 bulk_scout 轻量普查，直接使用场景精细化策略。"
            return adjusted
        for key in ("confidence", "duration", "interval", "priority"):
            if key in mode_config:
                adjusted[key] = mode_config[key]
        adjusted["reason"] = f"{mode_config.get('reason', '')} {adjusted['reason']}".strip()
        return adjusted

    if patrol_mode == "focused":
        adjusted["confidence"] = max(
            0.2,
            round(float(adjusted["confidence"]) + float(mode_config.get("confidence_delta", 0)), 2),
        )
        adjusted["duration"] = int(adjusted["duration"] * float(mode_config.get("duration_multiplier", 1)))
        adjusted["interval"] = max(
            0.5,
            round(float(adjusted["interval"]) * float(mode_config.get("interval_multiplier", 1)), 2),
        )
        adjusted["priority"] = "high"
        adjusted["reason"] += f" {mode_config.get('reason', '')}".rstrip()
    return adjusted


def _history_adjust(profile: Dict[str, Any], history: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    adjusted = copy.deepcopy(profile)
    false_positive_count = 0
    true_incident_count = 0
    lesson_notes: List[str] = []

    for item in history:
        outcome = item.get("outcome")
        if outcome == "false_positive":
            false_positive_count += 1
        elif outcome in {"true_incident", "drill"}:
            true_incident_count += 1
        note = item.get("lesson")
        if note:
            lesson_notes.append(str(note))

    if false_positive_count >= 2:
        adjusted["confidence"] = min(0.9, round(float(adjusted["confidence"]) + 0.1, 2))
        adjusted["reason"] += f" 历史存在 {false_positive_count} 次误报，因此提高阈值。"
    if true_incident_count >= 1:
        adjusted["duration"] = int(adjusted["duration"] * 1.2)
        adjusted["priority"] = "high"
        adjusted["reason"] += f" 历史存在 {true_incident_count} 次确认事件，因此提高优先级。"
    if lesson_notes:
        adjusted["lesson_notes"] = lesson_notes[:3]
    return adjusted


def _infer_scene_from_hints(target: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    declared = target.get("scene_type")
    hints = target.get("hints", {}) or {}
    historical_profile = target.get("historical_camera_profile") or {}
    mapping = config.get("hint_scene_mapping", {})

    if declared and declared != "unknown":
        return {
            "effective_scene_type": declared,
            "scene_confidence": 1.0,
            "basis": f"用户或配置显式标注为 {declared}。",
            "declared_scene_type": declared,
            "hints": hints,
        }

    indoor_outdoor = hints.get("indoor_outdoor")
    mapped = mapping.get("indoor_outdoor", {}).get(indoor_outdoor)
    if mapped:
        return {
            "effective_scene_type": mapped,
            "scene_confidence": 0.55,
            "basis": f"未提供明确场景，根据 indoor_outdoor={indoor_outdoor} 使用 {mapped} 倾向策略。",
            "declared_scene_type": declared or "unknown",
            "hints": hints,
        }

    text = " ".join(str(hints.get(key, "")) for key in ("location_hint", "user_label", "notes"))
    for keyword, scene_type in mapping.get("location_keywords", {}).items():
        if keyword and keyword in text:
            return {
                "effective_scene_type": scene_type,
                "scene_confidence": 0.65,
                "basis": f"未提供明确场景，根据线索“{keyword}”使用 {scene_type} 倾向策略。",
                "declared_scene_type": declared or "unknown",
                "hints": hints,
            }

    risk_zone = hints.get("risk_zone")
    mapped = mapping.get("risk_zone", {}).get(risk_zone)
    if mapped:
        return {
            "effective_scene_type": mapped,
            "scene_confidence": 0.45,
            "basis": f"未提供明确场景，根据 risk_zone={risk_zone} 使用 {mapped} 倾向策略。",
            "declared_scene_type": declared or "unknown",
            "hints": hints,
        }

    historical_scene = historical_profile.get("preferred_scene_type") or historical_profile.get("last_effective_scene_type")
    if historical_scene and historical_scene != "unknown":
        return {
            "effective_scene_type": historical_scene,
            "scene_confidence": min(0.9, float(historical_profile.get("scene_confidence", 0.5)) + 0.1),
            "basis": f"本次未提供明确场景，根据历史 camera profile 复用 {historical_scene} 倾向策略。",
            "declared_scene_type": declared or "unknown",
            "hints": hints,
            "historical_camera_profile": historical_profile,
        }

    return {
        "effective_scene_type": "unknown",
        "scene_confidence": 0.0,
        "basis": "未提供明确场景或可用线索，使用 unknown 默认策略。",
        "declared_scene_type": declared or "unknown",
        "hints": hints,
        "historical_camera_profile": historical_profile,
    }


def build_predict_profile(
    target: Dict[str, Any],
    config: Dict[str, Any] | None = None,
    history: Iterable[Dict[str, Any]] | None = None,
    resource_budget: str | None = None,
    patrol_mode: str | None = None,
) -> Dict[str, Any]:
    config = config or load_config()
    camera_profile = _infer_scene_from_hints(target, config)
    scene_type = camera_profile["effective_scene_type"]
    scene_profiles = config["scene_profiles"]
    base = copy.deepcopy(scene_profiles.get(scene_type, scene_profiles["unknown"]))
    budget = resource_budget or config.get("default_resource_budget", "balanced")
    mode = patrol_mode or config.get("default_patrol_mode", "normal")

    profile = _patrol_mode_adjust(base, mode, scene_type, config)
    effective_budget = budget
    if mode == "bulk_scout" and scene_type != "unknown" and budget == "fast":
        effective_budget = "balanced"
        profile["reason"] += " bulk_scout 下该流已有场景线索，保持场景默认精细策略，不再叠加 fast 降级。"
    profile = _budget_adjust(profile, effective_budget)
    profile = _history_adjust(profile, history or [])
    profile["reason"] = f"{camera_profile['basis']} {profile['reason']}"
    if target.get("roi"):
        profile["roi"] = target["roi"]
        profile["reason"] += " 用户提供 ROI，因此只检测相关区域。"

    profile["scene_type"] = scene_type
    profile["declared_scene_type"] = camera_profile["declared_scene_type"]
    profile["scene_confidence"] = camera_profile["scene_confidence"]
    profile["camera_profile_basis"] = camera_profile["basis"]
    profile["hints"] = camera_profile["hints"]
    if camera_profile.get("historical_camera_profile"):
        profile["historical_camera_profile"] = camera_profile["historical_camera_profile"]
    profile["scene_reasoning_guidance"] = config.get("scene_reasoning_guidance", {}).get(
        scene_type,
        config.get("scene_reasoning_guidance", {}).get("unknown", {}),
    )
    profile["source_id"] = target.get("source_id", "unknown")
    profile["resource_budget"] = budget
    profile["effective_resource_budget"] = effective_budget
    profile["patrol_mode"] = mode
    return profile


def _load_camera_profiles_for_plan(config: Dict[str, Any]) -> Dict[str, Any]:
    paths = config.get("knowledge_paths", {})
    path = paths.get("camera_profiles")
    if not path:
        return {"profiles": {}, "url_index": {}}
    return load_profiles(path)


def plan_patrol(
    request: Dict[str, Any],
    config: Dict[str, Any] | None = None,
    use_camera_profiles: bool = True,
) -> List[Dict[str, Any]]:
    config = config or load_config()
    budget = request.get("resource_budget") or config.get("default_resource_budget", "balanced")
    patrol_mode = request.get("patrol_mode") or config.get("default_patrol_mode", "normal")
    camera_profiles = _load_camera_profiles_for_plan(config) if use_camera_profiles else {"profiles": {}, "url_index": {}}
    plans = []
    for target in request.get("targets", []):
        target_for_plan = dict(target)
        historical_profile = find_profile(
            camera_profiles,
            target_for_plan.get("source_id"),
            target_for_plan.get("stream_url"),
        )
        if historical_profile and not target_for_plan.get("historical_camera_profile"):
            target_for_plan["historical_camera_profile"] = historical_profile
        profile = build_predict_profile(
            target_for_plan,
            config=config,
            resource_budget=budget,
            patrol_mode=patrol_mode,
        )
        plans.append({"target": target_for_plan, "predict_profile": profile})
    return plans


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build FireWatch predict-wise profiles")
    parser.add_argument("request_json", help="Patrol request JSON file")
    args = parser.parse_args()

    request = json.loads(Path(args.request_json).read_text(encoding="utf-8"))
    print(json.dumps(plan_patrol(request), ensure_ascii=False, indent=2))
