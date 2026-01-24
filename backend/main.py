import io
import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from modules.scene_grouping import group_scenes
from modules.scale_detection import detect_scale_reference
from modules.depth_estimation import estimate_depth_map
from modules.segmentation import generate_debris_mask
from modules.volume_estimation import estimate_volume_from_masks
from modules.dedupe import fuse_job_estimates, fuse_scene_estimates

OUTPUT_DIR = Path("/tmp/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR = Path("/tmp/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index() -> HTMLResponse:
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Frontend not found</h1>")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _job_dir(job_id: str) -> Path:
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def _write_metadata(job_dir: Path, metadata: Dict) -> None:
    (job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _load_metadata(job_dir: Path) -> Dict:
    metadata_path = job_dir / "metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    return {}


@app.post("/jobs")
async def create_job(photos: List[UploadFile] = File(...)) -> JSONResponse:
    if not 1 <= len(photos) <= 12:
        raise HTTPException(status_code=400, detail="Upload between 1 and 12 images.")

    job_id = uuid.uuid4().hex
    job_dir = _job_dir(job_id)
    photo_entries = []

    for photo in photos:
        photo_id = uuid.uuid4().hex
        suffix = Path(photo.filename or "photo.jpg").suffix or ".jpg"
        photo_path = job_dir / f"{photo_id}{suffix}"
        content = await photo.read()
        photo_path.write_bytes(content)
        photo_entries.append({"photo_id": photo_id, "filename": photo.filename, "path": str(photo_path)})

    metadata = {"job_id": job_id, "photos": photo_entries, "masks": {}}
    _write_metadata(job_dir, metadata)

    return JSONResponse({"job_id": job_id, "photos": photo_entries})


@app.post("/jobs/{job_id}/mask/{photo_id}")
async def upload_mask(job_id: str, photo_id: str, mask: UploadFile = File(...)) -> JSONResponse:
    job_dir = _job_dir(job_id)
    metadata = _load_metadata(job_dir)
    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    mask_suffix = Path(mask.filename or "mask.png").suffix or ".png"
    mask_path = job_dir / f"{photo_id}_mask{mask_suffix}"
    mask_path.write_bytes(await mask.read())

    metadata.setdefault("masks", {})[photo_id] = str(mask_path)
    _write_metadata(job_dir, metadata)

    return JSONResponse({"job_id": job_id, "photo_id": photo_id, "mask_path": str(mask_path)})


@app.post("/jobs/{job_id}/estimate")
async def estimate_job(job_id: str, debug: Optional[bool] = Form(default=False)) -> JSONResponse:
    job_dir = _job_dir(job_id)
    metadata = _load_metadata(job_dir)
    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    photos = metadata.get("photos", [])
    if not photos:
        raise HTTPException(status_code=400, detail="No photos found for job")

    scene_groups = group_scenes([p["path"] for p in photos])

    scene_results = []
    photo_id_lookup = {photo["path"]: photo["photo_id"] for photo in photos}

    for scene_id, photo_paths in scene_groups.items():
        per_photo_estimates = []
        scale_reference = {"type": "unknown", "confidence": 0.2}
        scale_notes = []
        for photo_path in photo_paths:
            photo_id = photo_id_lookup.get(photo_path)
            mask_path = metadata.get("masks", {}).get(photo_id)
            scale_reference = detect_scale_reference(photo_path)
            depth_map = estimate_depth_map(photo_path)
            debris_mask = generate_debris_mask(photo_path, mask_path)
            estimate = estimate_volume_from_masks(
                photo_path=photo_path,
                debris_mask=debris_mask,
                depth_map=depth_map,
                scale_reference=scale_reference,
                debug_dir=job_dir / "debug" if debug else None,
            )
            per_photo_estimates.append(estimate)
            scale_notes.append(estimate.get("notes", ""))

        fused_estimate = fuse_scene_estimates(per_photo_estimates)
        scene_results.append(
            {
                "scene_id": scene_id,
                "photos": [Path(p).name for p in photo_paths],
                "scale_reference": scale_reference,
                "estimate": fused_estimate,
                "notes": [note for note in scale_notes if note],
            }
        )

    job_estimate = fuse_job_estimates([scene["estimate"] for scene in scene_results])

    return JSONResponse({"job": job_estimate, "scenes": scene_results})


@app.get("/outputs/{job_id}/{file_name}")
def get_output(job_id: str, file_name: str) -> FileResponse:
    job_dir = _job_dir(job_id)
    target = job_dir / file_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
