from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw


REFERENCE_OPTIONS = [
    ("interior door", 80.0),
    ("door handle", 36.0),
    ("kitchen counter", 36.0),
    ("standard outlet", 18.0),
    ("mattress", 10.0),
    ("sofa", 36.0),
    ("dresser", 48.0),
    ("refrigerator", 66.0),
    ("32 gallon trash can", 27.0),
    ("18 gallon tote", 16.0),
    ("moving box", 18.0),
    ("96 gallon trash bin", 45.0),
    ("pallet", 48.0),
    ("fence picket", 72.0),
    ("curb", 6.0),
]


@dataclass
class ScaleReference:
    label: str
    height_in: float
    confidence: float
    note: str

    def overlay_debug(self, image_path: Path, debug_dir: Optional[Path]) -> None:
        if debug_dir is None:
            return
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            draw = ImageDraw.Draw(image)
            text = f"Scale: {self.label} ({self.height_in} in)"
            draw.rectangle([(10, 10), (10 + len(text) * 6, 30)], fill=(0, 0, 0))
            draw.text((14, 12), text, fill=(255, 255, 255))
            output_path = debug_dir / f"{image_path.stem}_scale.png"
            image.save(output_path)


def _choose_reference(image_path: Path) -> ScaleReference:
    with Image.open(image_path) as image:
        width, height = image.size

    if height > width * 1.2:
        return ScaleReference(
            label="interior door",
            height_in=80.0,
            confidence=0.45,
            note="Vertical framing suggests door-sized reference",
        )

    if width > height * 1.3:
        return ScaleReference(
            label="sofa",
            height_in=36.0,
            confidence=0.3,
            note="Wide framing suggests furniture scale",
        )

    return ScaleReference(
        label="moving box",
        height_in=18.0,
        confidence=0.2,
        note="Fallback scale due to unclear reference",
    )


def _top_candidates() -> List[Tuple[str, float, float, str]]:
    return [
        ("interior door", 80.0, 0.45, "Common vertical reference"),
        ("kitchen counter", 36.0, 0.35, "Common interior reference"),
        ("moving box", 18.0, 0.2, "Common portable reference"),
    ]


def choose_scale_reference(image_path: Path) -> ScaleReference:
    return _choose_reference(image_path)


def detect_scale_reference(image_path: Path) -> dict:
    chosen = _choose_reference(image_path)
    candidates = _top_candidates()
    return {
        "chosen": {
            "type": chosen.label,
            "confidence": chosen.confidence,
            "note": chosen.note,
        },
        "candidates": [
            {
                "type": label,
                "confidence": confidence,
                "note": note,
            }
            for label, _height, confidence, note in candidates
        ],
    }


__all__ = ["ScaleReference", "detect_scale_reference", "choose_scale_reference"]
