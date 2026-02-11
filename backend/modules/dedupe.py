from typing import Dict, List


def fuse_scene_estimates(estimates: List[Dict]) -> Dict:
    if not estimates:
        return {"low": 0, "likely": 0, "high": 0, "confidence": 0}

    low = max(e.get("low", 0) for e in estimates)
    likely = max(e.get("likely", 0) for e in estimates)
    high = max(e.get("high", 0) for e in estimates)
    confidence = max(e.get("confidence", 0) for e in estimates)

    return {
        "low": round(low, 2),
        "likely": round(likely, 2),
        "high": round(high, 2),
        "confidence": round(confidence, 2),
    }


def fuse_job_estimates(scene_estimates: List[Dict]) -> Dict:
    if not scene_estimates:
        return {"low": 0, "likely": 0, "high": 0, "confidence": 0}

    low = sum(e.get("low", 0) for e in scene_estimates)
    likely = sum(e.get("likely", 0) for e in scene_estimates)
    high = sum(e.get("high", 0) for e in scene_estimates)
    confidence = sum(e.get("confidence", 0) for e in scene_estimates) / len(scene_estimates)

    return {
        "low": round(low, 2),
        "likely": round(likely, 2),
        "high": round(high, 2),
        "confidence": round(confidence, 2),
    }
