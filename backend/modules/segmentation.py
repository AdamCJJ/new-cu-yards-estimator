from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image


RED_CHANNEL_THRESHOLD = 100


def build_debris_mask(
    image_path: Path,
    mask_path: Optional[Path] = None,
    debug_dir: Optional[Path] = None,
) -> np.ndarray:
    with Image.open(image_path) as image:
        image = image.convert("RGB").resize((128, 128))
        array = np.asarray(image)

    if mask_path and mask_path.exists():
        with Image.open(mask_path) as mask_image:
            mask_image = mask_image.convert("RGB").resize((128, 128))
            mask_array = np.asarray(mask_image)
        mask = mask_array[:, :, 0] > RED_CHANNEL_THRESHOLD
    else:
        grayscale = np.mean(array, axis=2)
        mask = grayscale < 220

    if debug_dir is not None:
        mask_img = Image.fromarray((mask.astype("uint8") * 255))
        mask_img.save(debug_dir / f"{image_path.stem}_mask.png")

    return mask


def split_regions(debris_mask: np.ndarray, max_regions: int = 5) -> List[Dict]:
    height, width = debris_mask.shape
    regions = []
    grid = [
        ("northwest", (0, height // 2, 0, width // 2)),
        ("northeast", (0, height // 2, width // 2, width)),
        ("southwest", (height // 2, height, 0, width // 2)),
        ("southeast", (height // 2, height, width // 2, width)),
    ]
    for label, (r0, r1, c0, c1) in grid:
        region_mask = np.zeros_like(debris_mask, dtype=bool)
        region_mask[r0:r1, c0:c1] = debris_mask[r0:r1, c0:c1]
        coverage = float(region_mask.mean())
        regions.append(
            {
                "region_id": f"region_{label}",
                "label": label,
                "mask": region_mask,
                "coverage": coverage,
            }
        )

    center_mask = np.zeros_like(debris_mask, dtype=bool)
    center_slice = (
        slice(height // 4, height * 3 // 4),
        slice(width // 4, width * 3 // 4),
    )
    center_mask[center_slice] = debris_mask[center_slice]
    regions.append(
        {
            "region_id": "region_center",
            "label": "center",
            "mask": center_mask,
            "coverage": float(center_mask.mean()),
        }
    )

    regions = sorted(regions, key=lambda item: item["coverage"], reverse=True)
    chosen = regions[: max(1, min(max_regions, len(regions)))]
    if all(region["coverage"] == 0 for region in chosen):
        chosen = [
            {
                "region_id": "region_full",
                "label": "full",
                "mask": debris_mask,
                "coverage": float(debris_mask.mean()),
            }
        ]
    return chosen


def estimate_floor_visibility(debris_mask: np.ndarray) -> str:
    coverage = float(debris_mask.mean())
    if coverage > 0.6:
        return "limited"
    if coverage > 0.35:
        return "partial"
    return "visible"


__all__ = ["build_debris_mask", "split_regions", "estimate_floor_visibility"]
