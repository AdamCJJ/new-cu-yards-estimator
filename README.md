# Junk Volume Estimator MVP

Estimate junk removal volume in cubic yards from photos. This app is **volume-only** and intentionally avoids any financial amounts. It ignores and does not store any user text related to financial discussions.

## Architecture overview
- **FastAPI backend** handles uploads, scene grouping, depth estimation, segmentation, and volume estimation.
- **Static frontend** served by FastAPI from `backend/static`.
- **Artifacts** saved under `/tmp/outputs`; models cached under `/tmp/models`.

## Repository layout
```
backend
  main.py
  requirements.txt
  modules
    scene_grouping.py
    scale_detection.py
    depth_estimation.py
    segmentation.py
    volume_estimation.py
    dedupe.py
  static
    index.html
    styles.css
    app.js
frontend
  README.md
Dockerfile
render.yaml
docker-compose.yml
README.md
```

## Endpoints
- `POST /jobs` (multipart upload, 1–12 images)
- `POST /jobs/{id}/mask/{photo_id}` (optional remove mask)
- `POST /jobs/{id}/estimate` (returns JSON estimate)
- `GET /health`

## Estimation heuristics (MVP)
- **Scene grouping**: lightweight embeddings from 32×32 thumbnails with cosine similarity clustering.
- **Scale detection**: picks a reference based on basic framing ratios (door, sofa, or moving box). If unclear, confidence is low and the range widens.
- **Depth estimation**: grayscale-based depth proxy with a vertical gradient to favor nearby floor areas.
- **Segmentation**: optional user mask (red scribble), otherwise non-white pixels are treated as debris.
- **Volume**: footprint area × estimated height × compaction factor, then converted to cubic yards.
- **Dedupe**: within a scene, multiple photos use the maximum estimate to prevent double counting.

## Debug mode
Send `debug=true` on `POST /jobs/{id}/estimate` to save:
- scale reference overlays
- depth map images
- debris mask images

## Acceptance tests (manual)
- Single photo with a door and a pile produces a range and confidence.
- Multi-photo same couch grouped into one scene with dedupe applied.
- Photo with no clear reference produces wider low/high range and lower confidence.

## Running locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PORT=10000 uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
```

## Deployment
Deploy on Render as a Docker Web Service using `render.yaml`. The app listens on `PORT` and binds to `0.0.0.0`.

1. Push this repository to a Git provider supported by Render.
2. In Render, create a new **Web Service** and choose **Docker** as the runtime.
3. Point the service at this repo and keep the defaults from `render.yaml`.
4. Render will build the image from `Dockerfile` and expose the service on the assigned URL.
