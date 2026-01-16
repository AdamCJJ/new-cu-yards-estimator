from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image


def estimate_depth_map(image_path: Path, debug_dir: Optional[Path] = None) -> np.ndarray:
    with Image.open(image_path) as image:
        image = image.convert("L").resize((128, 128))
        gray = np.asarray(image).astype("float32") / 255.0

    height, width = gray.shape
    gradient = np.linspace(1.0, 0.2, height).reshape(-1, 1)
    depth = gray * gradient

    if debug_dir is not None:
        depth_img = Image.fromarray((depth * 255).astype("uint8"))
        depth_img.save(debug_dir / f"{image_path.stem}_depth.png")

    return depth


__all__ = ["estimate_depth_map"]
