#!/usr/bin/env python3
"""Integrated FireWatch patrol runner."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fire_detection_client import FireDetectionClient
from camera_profile_store import find_profile, load_profiles, save_profiles, update_profile_from_event
from knowledge_store import read_jsonl, matching_history, write_observation
from predict_planner import load_config, build_predict_profile
from report_writer import render_incident_report, render_patrol_summary, write_text
from risk_assessor import assess_risk
from temporal_aggregator import aggregate_detection_result


SKILL_DIR = Path(__file__).resolve().parents[1]


def _incident_id(source_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"fire-{stamp}-{source_id}-{uuid.uuid4().hex[:6]}"


def run_patrol(request: Dict[str, Any]) -> Dict[str, Any]:
    config = load_config()
    paths = config["knowledge_paths"]
    budget = request.get("resource_budget") or config["default_resource_budget"]
    patrol_mode = request.get("patrol_mode") or config.get("default_patrol_mode", "normal")
    client = FireDetectionClient(config["fire_detection_service_url"])
    output_dir = SKILL_DIR / config.get("output_dir", "outputs")
    events: List[Dict[str, Any]] = []

    lessons = read_jsonl(paths["lessons_learned"])
    camera_profiles = load_profiles(paths["camera_profiles"])

    for target in request.get("targets", []):
        source_id = target.get("source_id", "unknown")
        declared_scene_type = target.get("scene_type", "unknown")
        historical_profile = find_profile(camera_profiles, source_id, target.get("stream_url"))
        if historical_profile and not target.get("historical_camera_profile"):
            target = dict(target)
            target["historical_camera_profile"] = historical_profile

        profile = build_predict_profile(
            target,
            config=config,
            resource_budget=budget,
            patrol_mode=patrol_mode,
        )
        effective_scene_type = profile.get("scene_type", declared_scene_type)
        history_scene_type = effective_scene_type if effective_scene_type != "unknown" else None
        history = matching_history(lessons, source_id=source_id, scene_type=history_scene_type)
        if history:
            profile = build_predict_profile(
                target,
                config=config,
                history=history,
                resource_budget=budget,
                patrol_mode=patrol_mode,
            )
            effective_scene_type = profile.get("scene_type", declared_scene_type)

        result = client.detect_stream(target["stream_url"], profile)

        temporal_evidence = aggregate_detection_result(result, config.get("temporal_policy"))
        risk = assess_risk(temporal_evidence, profile, config["risk_thresholds"])
        event = {
            "incident_id": _incident_id(source_id),
            "source_id": source_id,
            "source_url": target.get("stream_url"),
            "scene_type": effective_scene_type,
            "declared_scene_type": profile.get("declared_scene_type", "unknown"),
            "predict_profile": profile,
            "temporal_evidence": temporal_evidence,
            "risk": risk,
            "knowledge_refs": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_observation(paths, event)
        update_profile_from_event(camera_profiles, event)
        events.append(event)

        if risk["level"] in set(config["notify_on"]):
            report = render_incident_report(event)
            write_text(output_dir / f"{event['incident_id']}.md", report)

    patrol_id = request.get("patrol_id") or f"patrol-{uuid.uuid4().hex[:8]}"
    summary = render_patrol_summary(patrol_id, events)
    summary_path = write_text(output_dir / f"{patrol_id}-summary.md", summary)
    save_profiles(paths["camera_profiles"], camera_profiles)
    return {"patrol_id": patrol_id, "summary_path": summary_path, "events": events}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a FireWatch patrol")
    parser.add_argument("request_json", help="Patrol request JSON file")
    args = parser.parse_args()

    request = json.loads(Path(args.request_json).read_text(encoding="utf-8"))
    result = run_patrol(request)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
