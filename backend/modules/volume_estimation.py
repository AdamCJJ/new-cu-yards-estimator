from pathlib import Path
from typing import Dict, Optional

import numpy as np
from PIL import Image


REFERENCE_PIXEL_FRACTION = {
    "interior_door": 0.65,
    "door_handle_height": 0.45,
    "kitchen_counter_height": 0.35,
    "outlet_switch_height": 0.2,
    "mattress": 0.3,
    "sofa": 0.35,
    "dresser": 0.3,
    "refrigerator": 0.6,
    "trash_can_32g": 0.25,
    "tote_18g": 0.2,
    "moving_box": 0.2,
    "trash_bin_96g": 0.45,
    "pallet": 0.08,
    "fence_picket": 0.4,
    "curb_height": 0.1,
}


def _estimate_scale_inches_per_pixel(image_size, scale_reference: Dict) -> float:
    width, height = image_size
    ref_type = scale_reference.get("type", "unknown")
    ref_inches = scale_reference.get("reference_inches", 36.0)
    fraction = REFERENCE_PIXEL_FRACTION.get(ref_type, 0.3)
    ref_pixels = max(height * fraction, 1.0)
    return ref_inches / ref_pixels


def estimate_volume_from_masks(
    photo_path: str,
    debris_mask: np.ndarray,
    depth_map: np.ndarray,
    scale_reference: Dict,
    debug_dir: Optional[Path] = None,
) -> Dict:
    image = Image.open(photo_path)
    width, height = image.size
    inches_per_pixel = _estimate_scale_inches_per_pixel((width, height), scale_reference)
    square_inches_per_pixel = inches_per_pixel ** 2

    debris_area_pixels = float(debris_mask.sum())
    debris_area_sqft = (debris_area_pixels * square_inches_per_pixel) / 144.0

    mean_depth = float(depth_map.mean())
    estimated_height_inches = 24.0 * mean_depth
    height_feet = estimated_height_inches / 12.0

    volume_cuft = debris_area_sqft * height_feet * 0.65
    volume_cy = volume_cuft / 27.0

    scale_confidence = float(scale_reference.get("confidence", 0.2))
    coverage_ratio = min(debris_area_pixels / (width * height), 1.0)
    confidence = max(0.15, min(0.9, scale_confidence * 0.6 + coverage_ratio * 0.4))

    low = max(0.0, volume_cy * 0.7)
    high = volume_cy * 1.4

    result = {
        "low": round(low, 2),
        "likely": round(volume_cy, 2),
        "high": round(high, 2),
        "confidence": round(confidence, 2),
        "notes": "Estimated pile height from depth gradient and debris footprint.",
    }

    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        depth_img = Image.fromarray((depth_map * 255).astype(np.uint8))
        depth_path = debug_dir / f"{Path(photo_path).stem}_depth.png"
        depth_img.save(depth_path)

        mask_img = Image.fromarray((debris_mask * 255).astype(np.uint8))
        mask_path = debug_dir / f"{Path(photo_path).stem}_mask.png"
        mask_img.save(mask_path)

        result["debug"] = {"depth_path": str(depth_path), "mask_path": str(mask_path)}

    return result
