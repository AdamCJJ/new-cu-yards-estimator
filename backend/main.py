import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.modules.scene_grouping import group_scenes
from backend.modules.scale_detection import choose_scale_reference, detect_scale_reference
from backend.modules.depth_estimation import estimate_depth_map
from backend.modules.segmentation import (
    build_debris_mask,
    estimate_floor_visibility,
    split_regions,
)
from backend.modules.volume_estimation import (
    DEFAULT_VOID_FACTOR,
    MATERIAL_FACTORS,
    estimate_volume_range,
)
from backend.modules.dedupe import dedupe_scene_estimates

BASE_OUTPUT_DIR = Path("/tmp/outputs")
BASE_MODEL_DIR = Path("/tmp/models")

BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BASE_MODEL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def load_job(job_id: str) -> Dict:
    job_path = BASE_OUTPUT_DIR / job_id / "job.json"
    if not job_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(job_path.read_text())


def save_job(job_id: str, payload: Dict) -> None:
    job_path = BASE_OUTPUT_DIR / job_id / "job.json"
    job_path.write_text(json.dumps(payload, indent=2))


def get_job_dir(job_id: str) -> Path:
    return BASE_OUTPUT_DIR / job_id


@app.get("/")
def index() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(index_path.read_text())


@app.get("/health")
def health_check() -> Dict:
    return {"status": "ok"}


@app.post("/jobs")
def create_job(files: List[UploadFile] = File(...)) -> Dict:
    if not 1 <= len(files) <= 12:
        raise HTTPException(status_code=400, detail="Upload between 1 and 12 images")

    job_id = uuid.uuid4().hex
    job_dir = get_job_dir(job_id)
    images_dir = job_dir / "images"
    masks_dir = job_dir / "masks"
    debug_dir = job_dir / "debug"
    images_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    stored_files = []
    for upload in files:
        if not upload.content_type or not upload.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are supported")
        suffix = Path(upload.filename or "image").suffix or ".jpg"
        photo_id = uuid.uuid4().hex
        filename = f"{photo_id}{suffix}"
        dest = images_dir / filename
        dest.write_bytes(upload.file.read())
        stored_files.append({"photo_id": photo_id, "filename": filename})

    job_payload = {
        "id": job_id,
        "created_at": datetime.utcnow().isoformat(),
        "photos": stored_files,
    }
    save_job(job_id, job_payload)
    return {"job_id": job_id, "photos": stored_files}


@app.post("/jobs/{job_id}/mask/{photo_id}")
def upload_mask(job_id: str, photo_id: str, file: UploadFile = File(...)) -> Dict:
    job = load_job(job_id)
    if not any(photo["photo_id"] == photo_id for photo in job["photos"]):
        raise HTTPException(status_code=404, detail="Photo not found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    masks_dir = get_job_dir(job_id) / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "mask").suffix or ".png"
    mask_path = masks_dir / f"{photo_id}{suffix}"
    mask_path.write_bytes(file.file.read())

    return {"status": "ok", "photo_id": photo_id}


@app.post("/jobs/{job_id}/estimate")
def estimate_job(job_id: str, debug: Optional[bool] = False) -> Dict:
    job = load_job(job_id)
    job_dir = get_job_dir(job_id)
    images_dir = job_dir / "images"
    masks_dir = job_dir / "masks"
    debug_dir = job_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    photos = job["photos"]
    photo_paths = [images_dir / photo["filename"] for photo in photos]
    embeddings = group_scenes.compute_embeddings(photo_paths)
    scene_groups = group_scenes.assign_scenes(photo_paths, embeddings)

    scene_results = []
    for scene_id, scene_photos in scene_groups.items():
        photo_data = []
        photo_estimates = []
        for path in scene_photos:
            mask_path = next(masks_dir.glob(f"{path.stem}.*"), None)
            scale_reference = choose_scale_reference(path)
            scale_meta = detect_scale_reference(path)
            depth_map = estimate_depth_map(path, debug_dir if debug else None)
            debris_mask = build_debris_mask(path, mask_path, debug_dir if debug else None)
            full_estimate = estimate_volume_range(
                path,
                depth_map,
                debris_mask,
                scale_reference,
                compaction_factor=MATERIAL_FACTORS.get("loose household mixed", 0.85),
            )
            if debug:
                scale_reference.overlay_debug(path, debug_dir)
            photo_data.append(
                {
                    "path": path,
                    "scale_reference": scale_reference,
                    "scale_meta": scale_meta,
                    "depth_map": depth_map,
                    "debris_mask": debris_mask,
                }
            )
            photo_estimates.append(full_estimate)

        primary_photo = max(photo_data, key=lambda item: float(item["debris_mask"].mean()))
        scale_reference = primary_photo["scale_reference"]
        scale_meta = primary_photo["scale_meta"]
        debris_mask = primary_photo["debris_mask"]
        depth_map = primary_photo["depth_map"]
        floor_visibility = estimate_floor_visibility(debris_mask)
        compaction = MATERIAL_FACTORS.get("loose household mixed", 0.85)

        regions = []
        region_masks = split_regions(debris_mask, max_regions=5)
        for region in region_masks:
            region_volume = estimate_volume_range(
                primary_photo["path"],
                depth_map,
                region["mask"],
                scale_reference,
                compaction_factor=compaction,
            )
            regions.append(
                {
                    "region_id": region["region_id"],
                    "label": region["label"],
                    "estimate": region_volume,
                    "assumptions": [
                        {"type": "void_factor", "value": DEFAULT_VOID_FACTOR},
                        {"type": "compaction_factor", "value": compaction},
                        {"type": "scale_source", "value": scale_meta["chosen"]["type"]},
                        {"type": "floor_visibility", "value": floor_visibility},
                    ],
                }
            )

        region_sum = {
            "low": round(sum(region["estimate"]["low"] for region in regions), 2),
            "likely": round(sum(region["estimate"]["likely"] for region in regions), 2),
            "high": round(sum(region["estimate"]["high"] for region in regions), 2),
            "confidence": round(
                sum(region["estimate"]["confidence"] for region in regions) / len(regions),
                2,
            )
            if regions
            else 0.0,
        }
        deduped_photo_estimate = dedupe_scene_estimates(photo_estimates)
        scene_estimate = dedupe_scene_estimates([region_sum, deduped_photo_estimate])

        notes = [
            "Scene volume derived from region breakdown (1-5 areas).",
            "Large-object dedupe uses max-per-scene strategy across photos.",
        ]
        if len(scene_photos) > 1:
            notes.append(
                "Multi-view fusion not implemented; used representative photo and widened range."
            )
            scene_estimate = {
                "low": round(scene_estimate["low"] * 0.75, 2),
                "likely": scene_estimate["likely"],
                "high": round(scene_estimate["high"] * 1.25, 2),
                "confidence": round(scene_estimate["confidence"] * 0.85, 2),
            }

        scene_results.append(
            {
                "scene_id": scene_id,
                "photos": [photo.name for photo in scene_photos],
                "scale_reference": scale_meta,
                "estimate": scene_estimate,
                "regions": regions,
                "assumptions": [
                    {"type": "void_factor", "value": DEFAULT_VOID_FACTOR},
                    {"type": "compaction_factor", "value": compaction},
                    {"type": "scale_source", "value": scale_meta["chosen"]["type"]},
                    {"type": "floor_visibility", "value": floor_visibility},
                ],
                "notes": notes,
            }
        )

    job_summary = {
        "low": round(sum(scene["estimate"]["low"] for scene in scene_results), 2),
        "likely": round(sum(scene["estimate"]["likely"] for scene in scene_results), 2),
        "high": round(sum(scene["estimate"]["high"] for scene in scene_results), 2),
        "confidence": round(
            sum(scene["estimate"]["confidence"] for scene in scene_results) / len(scene_results),
            2,
        )
        if scene_results
        else 0.0,
    }

    response = {
        "job": job_summary,
        "scenes": scene_results,
    }

    if debug:
        response["debug"] = {
            "output_dir": str(debug_dir),
            "artifacts": [path.name for path in debug_dir.glob("*")],
        }

    return response


@app.get("/debug/{job_id}/{filename}")
def get_debug_file(job_id: str, filename: str) -> FileResponse:
    debug_path = get_job_dir(job_id) / "debug" / filename
    if not debug_path.exists():
        raise HTTPException(status_code=404, detail="Debug file not found")
    return FileResponse(debug_path)


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> Dict:
    return load_job(job_id)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
