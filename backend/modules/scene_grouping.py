from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image


EMBED_SIZE = (32, 32)
SIMILARITY_THRESHOLD = 0.92


def _embed_image(path: str) -> np.ndarray:
    image = Image.open(path).convert("RGB").resize(EMBED_SIZE)
    arr = np.asarray(image, dtype=np.float32).reshape(-1)
    norm = np.linalg.norm(arr) or 1.0
    return arr / norm


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / ((np.linalg.norm(a) or 1.0) * (np.linalg.norm(b) or 1.0)))


def group_scenes(photo_paths: List[str]) -> Dict[str, List[str]]:
    embeddings = {path: _embed_image(path) for path in photo_paths}
    unassigned = set(photo_paths)
    scenes: Dict[str, List[str]] = {}

    while unassigned:
        seed = unassigned.pop()
        scene_id = f"scene_{len(scenes) + 1}"
        scenes[scene_id] = [seed]
        seed_embedding = embeddings[seed]

        similar = []
        for candidate in list(unassigned):
            similarity = _cosine_similarity(seed_embedding, embeddings[candidate])
            if similarity >= SIMILARITY_THRESHOLD:
                similar.append(candidate)

        for candidate in similar:
            unassigned.remove(candidate)
            scenes[scene_id].append(candidate)

    for scene_id in scenes:
        scenes[scene_id] = sorted(scenes[scene_id])

    return scenes
