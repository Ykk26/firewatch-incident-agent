#!/usr/bin/env python3
"""Persistent camera profile memory for FireWatch."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


SKILL_DIR = Path(__file__).resolve().parents[1]


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = SKILL_DIR / candidate
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def stream_url_hash(stream_url: str | None) -> str | None:
    if not stream_url:
        return None
    return hashlib.sha256(stream_url.encode("utf-8")).hexdigest()


def load_profiles(path: str | Path) -> Dict[str, Any]:
    source = _resolve(path)
    if not source.exists():
        return {"profiles": {}, "url_index": {}}
    data = json.loads(source.read_text(encoding="utf-8"))
    data.setdefault("profiles", {})
    data.setdefault("url_index", {})
    return data


def save_profiles(path: str | Path, data: Dict[str, Any]) -> None:
    destination = _resolve(path)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_profile(data: Dict[str, Any], source_id: str | None, stream_url: str | None) -> Optional[Dict[str, Any]]:
    profiles = data.get("profiles", {})
    if source_id and source_id in profiles:
        return profiles[source_id]

    url_hash = stream_url_hash(stream_url)
    if url_hash:
        indexed_source = data.get("url_index", {}).get(url_hash)
        if indexed_source and indexed_source in profiles:
            return profiles[indexed_source]
    return None


def update_profile_from_event(data: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    source_id = event.get("source_id") or "unknown"
    stream_url = event.get("source_url")
    url_hash = stream_url_hash(stream_url)
    now = datetime.now(timezone.utc).isoformat()
    profiles = data.setdefault("profiles", {})
    profile = profiles.get(source_id, {})

    risk_level = event.get("risk", {}).get("level", "unknown")
    risk_history = profile.setdefault("risk_history", {})
    risk_history[risk_level] = int(risk_history.get(risk_level, 0)) + 1

    predict_profile = event.get("predict_profile", {})
    scene_type = event.get("scene_type", predict_profile.get("scene_type", "unknown"))
    profile.update(
        {
            "source_id": source_id,
            "stream_url_hash": url_hash,
            "last_effective_scene_type": scene_type,
            "scene_confidence": predict_profile.get("scene_confidence", 0.0),
            "last_camera_profile_basis": predict_profile.get("camera_profile_basis"),
            "last_seen_at": now,
            "seen_count": int(profile.get("seen_count", 0)) + 1,
            "last_risk_level": risk_level,
            "last_false_positive_risk": event.get("risk", {}).get("false_positive_risk"),
            "last_profile_reason": predict_profile.get("reason"),
        }
    )

    hints = predict_profile.get("hints")
    if hints:
        profile["last_hints"] = hints

    if scene_type != "unknown":
        profile["preferred_scene_type"] = scene_type

    profiles[source_id] = profile
    if url_hash:
        data.setdefault("url_index", {})[url_hash] = source_id
    return profile
