# CU Yards Estimator MVP

This MVP estimates junk removal volume in **cubic yards only**. It does **not** calculate pricing, rates, or costs. Any user input mentioning price is ignored and never stored.

## Features
- Upload 1–12 photos per job.
- Auto group images into scenes using lightweight embeddings.
- Optional scribble mask per photo to include only removal regions.
- Returns low/likely/high cubic yard range with confidence.
- Debug artifacts: depth map and debris mask when `debug=true`.

## Heuristics Overview
- **Scene grouping:** 32×32 RGB embeddings with cosine similarity clustering to group similar viewpoints.
- **Scale detection:** Uses image aspect ratio to select a likely reference (door, sofa, trash can). If uncertain, uses lower confidence and wider range.
- **Depth estimation:** Lightweight gradient-based depth proxy to estimate debris height.
- **Segmentation:** Uses provided masks or a brightness heuristic to exclude background.
- **Volume estimation:** Debris footprint × height × compaction factor, then converts cubic feet to cubic yards.
- **Deduplication:** Within a scene, uses the maximum volume from multiple photos to avoid double counting.

## API
- `POST /jobs` (multipart form: `photos`)
- `POST /jobs/{id}/mask/{photo_id}` (multipart form: `mask`)
- `POST /jobs/{id}/estimate` (form field: `debug=true|false`)
- `GET /health`

### Response Format
```
{
  "job": {"low":0,"likely":0,"high":0,"confidence":0},
  "scenes":[
    {
      "scene_id":"",
      "photos":[],
      "scale_reference":{"type":"","confidence":0},
      "estimate":{"low":0,"likely":0,"high":0,"confidence":0},
      "notes":[]
    }
  ]
}
```

## Local Run
```
cd backend
pip install -r requirements.txt
python main.py
```

## Deployment
- Build and deploy the Dockerfile at repo root.
- App listens on `PORT` (default 10000) and binds `0.0.0.0`.
- Artifacts saved to `/tmp/outputs` and models under `/tmp/models`.

## Render
The `render.yaml` file defines a single Docker Web Service.
