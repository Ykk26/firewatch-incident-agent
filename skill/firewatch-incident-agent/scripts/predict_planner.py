#!/usr/bin/env python3
"""Build predict-wise inference profiles for FireWatch streams."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


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
        adjusted["reason"] += " Fast budget shortens inspection and raises threshold."
    elif budget == "thorough":
        adjusted["duration"] = int(adjusted["duration"] * 1.4)
        adjusted["interval"] = max(0.5, round(float(adjusted["interval"]) * 0.75, 2))
        adjusted["confidence"] = max(0.2, round(float(adjusted["confidence"]) - 0.05, 2))
        adjusted["reason"] += " Thorough budget inspects longer and samples more densely."
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
        adjusted["reason"] += f" {false_positive_count} prior false positives raise threshold."
    if true_incident_count >= 1:
        adjusted["duration"] = int(adjusted["duration"] * 1.2)
        adjusted["priority"] = "high"
        adjusted["reason"] += f" {true_incident_count} prior confirmed events increase priority."
    if lesson_notes:
        adjusted["lesson_notes"] = lesson_notes[:3]
    return adjusted


def build_predict_profile(
    target: Dict[str, Any],
    config: Dict[str, Any] | None = None,
    history: Iterable[Dict[str, Any]] | None = None,
    resource_budget: str | None = None,
) -> Dict[str, Any]:
    config = config or load_config()
    scene_type = target.get("scene_type", "unknown")
    scene_profiles = config["scene_profiles"]
    base = copy.deepcopy(scene_profiles.get(scene_type, scene_profiles["unknown"]))
    budget = resource_budget or config.get("default_resource_budget", "balanced")

    profile = _budget_adjust(base, budget)
    profile = _history_adjust(profile, history or [])
    if target.get("roi"):
        profile["roi"] = target["roi"]
        profile["reason"] += " User supplied ROI limits detection to the relevant area."

    profile["scene_type"] = scene_type
    profile["source_id"] = target.get("source_id", "unknown")
    profile["resource_budget"] = budget
    return profile


def plan_patrol(request: Dict[str, Any], config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    config = config or load_config()
    budget = request.get("resource_budget") or config.get("default_resource_budget", "balanced")
    plans = []
    for target in request.get("targets", []):
        profile = build_predict_profile(target, config=config, resource_budget=budget)
        plans.append({"target": target, "predict_profile": profile})
    return plans


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build FireWatch predict-wise profiles")
    parser.add_argument("request_json", help="Patrol request JSON file")
    args = parser.parse_args()

    request = json.loads(Path(args.request_json).read_text(encoding="utf-8"))
    print(json.dumps(plan_patrol(request), ensure_ascii=False, indent=2))
