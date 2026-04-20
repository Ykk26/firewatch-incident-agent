#!/usr/bin/env python3
"""Client for the existing fire-detection FastAPI service."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

import requests


class FireDetectionClient:
    def __init__(self, service_url: str, timeout: int = 120, poll_interval: float = 3.0):
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval

    def detect_image(self, image_path: str, confidence: float) -> Dict[str, Any]:
        with open(image_path, "rb") as handle:
            response = requests.post(
                f"{self.service_url}/api/detect/image",
                files={"file": handle},
                params={"confidence": confidence},
                timeout=self.timeout,
            )
        response.raise_for_status()
        return response.json()

    def start_stream(self, stream_url: str, profile: Dict[str, Any]) -> str:
        payload = {
            "stream_url": stream_url,
            "duration": int(profile["duration"]),
            "confidence": float(profile["confidence"]),
            "interval": float(profile["interval"]),
            "alert": False,
        }
        if profile.get("roi"):
            payload["roi"] = profile["roi"]
        response = requests.post(f"{self.service_url}/api/detect/stream", json=payload, timeout=20)
        response.raise_for_status()
        return response.json()["task_id"]

    def poll_result(self, task_id: str) -> Dict[str, Any]:
        started = time.time()
        while time.time() - started < self.timeout:
            response = requests.get(f"{self.service_url}/api/results/{task_id}", timeout=20)
            response.raise_for_status()
            result = response.json()
            if result.get("status") in {"completed", "failed"}:
                return result
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Detection task timed out: {task_id}")

    def detect_stream(self, stream_url: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        task_id = self.start_stream(stream_url, profile)
        return self.poll_result(task_id)

    def download_evidence_frames(self, result: Dict[str, Any], output_dir: Path) -> List[str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        saved: List[str] = []
        for frame_path in result.get("evidence_frames", []):
            if not frame_path:
                continue
            url = frame_path if frame_path.startswith("http") else f"{self.service_url}/{frame_path.lstrip('/')}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            destination = output_dir / Path(frame_path).name
            destination.write_bytes(response.content)
            saved.append(str(destination))
        return saved
