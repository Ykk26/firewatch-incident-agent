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
from knowledge_store import read_jsonl, matching_history, write_observation
from predict_planner import load_config, build_predict_profile
from report_writer import render_incident_report, render_patrol_summary, write_text
from risk_assessor import assess_risk
from temporal_aggregator import aggregate_detection_result


SKILL_DIR = Path(__file__).resolve().parents[1]


def _incident_id(source_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"fire-{stamp}-{source_id}-{uuid.uuid4().hex[:6]}"


def _simulated_result(target: Dict[str, Any]) -> Dict[str, Any]:
    return target.get(
        "simulate_result",
        {
            "status": "completed",
            "detections": [],
            "evidence_frames": [],
        },
    )


def run_patrol(request: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    config = load_config()
    paths = config["knowledge_paths"]
    budget = request.get("resource_budget") or config["default_resource_budget"]
    client = FireDetectionClient(config["fire_detection_service_url"])
    output_dir = SKILL_DIR / config.get("output_dir", "outputs")
    events: List[Dict[str, Any]] = []

    lessons = read_jsonl(paths["lessons_learned"])

    for target in request.get("targets", []):
        source_id = target.get("source_id", "unknown")
        scene_type = target.get("scene_type", "unknown")
        history = matching_history(lessons, source_id=source_id, scene_type=scene_type)
        profile = build_predict_profile(target, config=config, history=history, resource_budget=budget)

        if dry_run:
            result = _simulated_result(target)
        else:
            result = client.detect_stream(target["stream_url"], profile)

        temporal_evidence = aggregate_detection_result(result)
        risk = assess_risk(temporal_evidence, scene_type, profile, config["risk_thresholds"])
        event = {
            "incident_id": _incident_id(source_id),
            "source_id": source_id,
            "source_url": target.get("stream_url"),
            "scene_type": scene_type,
            "predict_profile": profile,
            "temporal_evidence": temporal_evidence,
            "risk": risk,
            "knowledge_refs": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_observation(paths, event)
        events.append(event)

        if risk["level"] in set(config["notify_on"]):
            report = render_incident_report(event)
            write_text(output_dir / f"{event['incident_id']}.md", report)

    patrol_id = request.get("patrol_id") or f"patrol-{uuid.uuid4().hex[:8]}"
    summary = render_patrol_summary(patrol_id, events)
    summary_path = write_text(output_dir / f"{patrol_id}-summary.md", summary)
    return {"patrol_id": patrol_id, "summary_path": summary_path, "events": events}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a FireWatch patrol")
    parser.add_argument("request_json", help="Patrol request JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Use simulate_result data instead of calling service")
    args = parser.parse_args()

    request = json.loads(Path(args.request_json).read_text(encoding="utf-8"))
    result = run_patrol(request, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
