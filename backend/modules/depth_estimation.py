from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image


def estimate_depth_map(photo_path: str) -> np.ndarray:
    image = Image.open(photo_path).convert("L")
    width, height = image.size
    gradient = np.linspace(1.0, 0.2, height, dtype=np.float32).reshape(height, 1)
    depth_map = np.repeat(gradient, width, axis=1)
    return depth_map
