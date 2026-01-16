from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image


@dataclass
class SceneEmbedding:
    path: Path
    vector: np.ndarray


def compute_embeddings(paths: List[Path]) -> List[SceneEmbedding]:
    embeddings = []
    for path in paths:
        with Image.open(path) as image:
            image = image.convert("RGB").resize((32, 32))
            array = np.asarray(image).astype("float32") / 255.0
            vector = array.reshape(-1)
            norm = np.linalg.norm(vector) or 1.0
            vector = vector / norm
            embeddings.append(SceneEmbedding(path=path, vector=vector))
    return embeddings


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / ((np.linalg.norm(a) or 1.0) * (np.linalg.norm(b) or 1.0)))


def assign_scenes(paths: List[Path], embeddings: List[SceneEmbedding]) -> Dict[str, List[Path]]:
    scenes: Dict[str, List[Path]] = {}
    scene_vectors: Dict[str, np.ndarray] = {}
    threshold = 0.9

    for embed in embeddings:
        assigned = False
        for scene_id, vector in scene_vectors.items():
            similarity = _cosine_similarity(embed.vector, vector)
            if similarity >= threshold:
                scenes[scene_id].append(embed.path)
                scene_vectors[scene_id] = (vector + embed.vector) / 2
                assigned = True
                break
        if not assigned:
            scene_id = f"scene-{len(scenes) + 1}"
            scenes[scene_id] = [embed.path]
            scene_vectors[scene_id] = embed.vector

    return scenes


__all__ = ["compute_embeddings", "assign_scenes"]
