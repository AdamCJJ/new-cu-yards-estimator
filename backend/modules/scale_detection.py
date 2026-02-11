from typing import Dict

from PIL import Image


REFERENCE_LIBRARY = [
    ("interior_door", 80.0),
    ("door_handle_height", 36.0),
    ("kitchen_counter_height", 36.0),
    ("outlet_switch_height", 18.0),
    ("mattress", 12.0),
    ("sofa", 36.0),
    ("dresser", 30.0),
    ("refrigerator", 68.0),
    ("trash_can_32g", 27.0),
    ("tote_18g", 16.0),
    ("moving_box", 18.0),
    ("trash_bin_96g", 45.0),
    ("pallet", 6.0),
    ("fence_picket", 48.0),
    ("curb_height", 6.0),
]


def detect_scale_reference(photo_path: str) -> Dict:
    image = Image.open(photo_path)
    width, height = image.size
    aspect_ratio = height / max(width, 1)

    if aspect_ratio > 1.2:
        ref_type, ref_inches = "interior_door", 80.0
        confidence = 0.55
    elif aspect_ratio < 0.8:
        ref_type, ref_inches = "sofa", 36.0
        confidence = 0.35
    else:
        ref_type, ref_inches = "trash_can_32g", 27.0
        confidence = 0.3

    return {"type": ref_type, "reference_inches": ref_inches, "confidence": confidence}
