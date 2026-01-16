from __future__ import annotations

from pathlib import Path
from typing import Optional

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


__all__ = ["build_debris_mask"]
