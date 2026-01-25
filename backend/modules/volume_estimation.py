from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
from PIL import Image

from backend.modules.scale_detection import ScaleReference


MATERIAL_FACTORS = {
    "loose household mixed": 0.85,
    "bagged trash": 0.7,
    "construction debris": 0.95,
    "yard waste": 0.65,
}
DEFAULT_VOID_FACTOR = 0.15


@dataclass
class VolumeRange:
    low: float
    likely: float
    high: float
    confidence: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "low": round(self.low, 2),
            "likely": round(self.likely, 2),
            "high": round(self.high, 2),
            "confidence": round(self.confidence, 2),
        }


def estimate_volume_range(
    image_path: Path,
    depth_map: np.ndarray,
    debris_mask: np.ndarray,
    scale: ScaleReference,
    material: str = "loose household mixed",
    compaction_factor: float | None = None,
) -> Dict[str, float]:
    with Image.open(image_path) as image:
        width, height = image.size

    mask_ratio = debris_mask.mean()
    reference_height_px = max(height * 0.6, 1)
    pixels_per_inch = reference_height_px / scale.height_in
    inches_per_pixel = 1 / max(pixels_per_inch, 1e-4)
    area_sq_in = mask_ratio * (width * inches_per_pixel) * (height * inches_per_pixel)
    area_sq_ft = area_sq_in / 144

    avg_depth = float(depth_map[debris_mask].mean()) if debris_mask.any() else 0.1
    pile_height_ft = max(avg_depth * scale.height_in / 12.0, 0.1)

    compaction = compaction_factor or MATERIAL_FACTORS.get(material, 0.85)
    volume_cuft = area_sq_ft * pile_height_ft * compaction
    volume_cy = volume_cuft / 27.0

    uncertainty = 0.35 if scale.confidence < 0.3 else 0.2
    low = max(volume_cy * (1 - uncertainty), 0.01)
    high = volume_cy * (1 + uncertainty)
    likely = volume_cy
    confidence = max(0.1, min(scale.confidence + 0.2, 0.95))

    return VolumeRange(low, likely, high, confidence).to_dict()


__all__ = ["DEFAULT_VOID_FACTOR", "MATERIAL_FACTORS", "estimate_volume_range"]
