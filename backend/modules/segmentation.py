from typing import Optional

import numpy as np
from PIL import Image


def generate_debris_mask(photo_path: str, mask_path: Optional[str]) -> np.ndarray:
    image = Image.open(photo_path).convert("RGB")
    if mask_path:
        mask = Image.open(mask_path).convert("L").resize(image.size)
        mask_arr = np.asarray(mask, dtype=np.float32) / 255.0
        return (mask_arr > 0.2).astype(np.float32)

    arr = np.asarray(image, dtype=np.float32) / 255.0
    brightness = arr.mean(axis=2)
    debris_mask = (brightness < 0.9).astype(np.float32)
    return debris_mask
