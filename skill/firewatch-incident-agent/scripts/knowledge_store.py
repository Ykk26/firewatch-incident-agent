#!/usr/bin/env python3
"""JSONL storage for FireWatch observations and scene lessons."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


SKILL_DIR = Path(__file__).resolve().parents[1]


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = SKILL_DIR / candidate
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def append_jsonl(path: str | Path, record: Dict[str, Any]) -> None:
    destination = _resolve(path)
    record = dict(record)
    record.setdefault("stored_at", datetime.now(timezone.utc).isoformat())
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    source = _resolve(path)
    if not source.exists():
        return []
    records = []
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def matching_history(
    records: Iterable[Dict[str, Any]],
    source_id: str | None = None,
    scene_type: str | None = None,
) -> List[Dict[str, Any]]:
    matches = []
    for record in records:
        if source_id and record.get("source_id") != source_id:
            continue
        if scene_type and record.get("scene_type") != scene_type:
            continue
        matches.append(record)
    return matches


def write_observation(paths: Dict[str, str], event: Dict[str, Any]) -> None:
    append_jsonl(paths["observations"], event)


def write_pending_lesson(paths: Dict[str, str], lesson: Dict[str, Any]) -> None:
    append_jsonl(paths["pending_review"], lesson)
