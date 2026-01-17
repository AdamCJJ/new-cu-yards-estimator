from __future__ import annotations

from typing import Dict, List


def dedupe_scene_estimates(estimates: List[Dict[str, float]]) -> Dict[str, float]:
    if not estimates:
        return {"low": 0.0, "likely": 0.0, "high": 0.0, "confidence": 0.0}

    low = max(item["low"] for item in estimates)
    likely = max(item["likely"] for item in estimates)
    high = max(item["high"] for item in estimates)
    confidence = max(item["confidence"] for item in estimates)

    return {
        "low": round(low, 2),
        "likely": round(likely, 2),
        "high": round(high, 2),
        "confidence": round(confidence, 2),
    }


__all__ = ["dedupe_scene_estimates"]
