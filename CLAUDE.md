# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dropbox → GCS → Vertex AI retrieval system. Mirrors Dropbox files to GCS, indexes images via Vector Search (multimodal embeddings) and documents via Vertex AI Search. Querying is cURL-only (no Python search API).

## Key Commands

### Build & Deploy
```bash
# Build and deploy both Cloud Run jobs (must use linux/amd64 for Cloud Run)
source infra/variables.sh && bash infra/05_build_and_deploy_jobs.sh
```

### Run Jobs Manually
```bash
# Sync Dropbox → GCS (also imports docs to Vertex AI Search)
gcloud run jobs execute sync-dropbox-to-gcs --region=us-central1

# Embed images → Vector Search
gcloud run jobs execute embed-images-to-vector-search --region=us-central1
```

### Query (cURL)
```bash
source infra/set_test_env.sh
bash curl/query_vector_search.sh "sunset photo"     # Images
bash curl/query_vertex_search.sh "meeting notes"    # Documents
bash curl/combine_results.sh "presentation"         # Both
```

### Local Development
```bash
# Set env vars first (see README.md for full list)
export GCP_PROJECT_ID=xxx
export GCS_BUCKET_NAME=xxx
export DROPBOX_APP_KEY=xxx
export DROPBOX_APP_SECRET=xxx
export DROPBOX_REFRESH_TOKEN=xxx
export VERTEX_SEARCH_DATASTORE_ID=dropbox-docs-datastore-ocr

python jobs/sync_dropbox_to_gcs/main.py
```

## Architecture

```
Dropbox → Cloud Run Job A (sync) → GCS
                                       ├── images/ → Job B → Vector Search
                                       ├── docs/   → Vertex AI Search (imported during sync)
                                       └── media/  (stored only)
```

### Two Cloud Run Jobs

1. **sync-dropbox-to-gcs** (Job A): Incremental sync from Dropbox, handles deletions, extracts ZIPs, imports docs to Vertex AI Search
2. **embed-images-to-vector-search** (Job B): Generates multimodal embeddings for images, upserts to Vector Search

### Shared Modules (`shared/`)

- `config.py` — All env vars (GCP_PROJECT_ID, GCS_BUCKET_NAME, Dropbox creds, Vertex Search IDs)
- `categories.py` — Extension → category mapping (images/docs/media), GCS key helpers
- `gcs.py` — Upload/download/delete JSON and bytes from GCS
- `dropbox_client.py` — OAuth2 refresh-token flow, cursor-based listing
- `dropbox_download.py` — Chunked streaming download for large files
- `zip_handler.py` — Disk-based streaming ZIP extraction (up to 10GB)
- `vertex_search.py` — Import documents to Vertex AI Search via Discovery Engine API

### GCS State Files (`mirror/state/`)

- `sync_state.json` — Dropbox cursor for incremental sync
- `path_index.json` — path_lower → file_id mapping (for deletions)
- `rev_index.json` — file_id → rev (skip unchanged files)
- `embedding_state.json` — file_id → embedded rev (skip already-embedded)

### File Categories

| Category | Extensions | Indexed By |
|----------|------------|------------|
| images | bmp, gif, jpg, jpeg, png | Vector Search (dim=1408) |
| docs | pdf, docx, xlsx, pptx, txt, html | Vertex AI Search |
| media | mp3, wav, mp4, mov | Not indexed |

### ZIP Handling

- Extracted during sync, not stored as ZIP
- Inner files get synthetic IDs: `<zip_id>___<inner_path>`
- Deleting ZIP → deletes all extracted children
- Metadata includes `source_zip` field

## Docker Builds

Must use `--platform linux/amd64` for Cloud Run compatibility (Apple Silicon defaults to arm64).

## Scheduled Jobs (Cloud Scheduler)

- `daily-dropbox-sync` — 02:00 UTC
- `daily-image-embed` — 04:00 UTC
- `daily-docs-reimport` — PAUSED (sync job now imports docs directly)
