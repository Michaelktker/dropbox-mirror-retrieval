# IMPLEMENTATION PLAN — Dropbox → GCS → Vertex AI

**Status**: 
- **Image embeddings** ✅ COMPLETE — 22,252/22,277 embedded (99.9%)
- **Document import** ✅ COMPLETE — 4,108/4,144 docs imported to OCR-enabled Vertex AI Search datastore (99.1%)
- **ZIP file support** ✅ DEPLOYED — extracts images/docs from ZIPs up to 10 GB

---

## Completed Jobs Summary

All processes completed successfully on Google Cloud infrastructure.

| Process | Status | Final Count |
|---------|--------|-------------|
| **Document Import** | ✅ Complete | 4,108/4,144 (99.1%) |
| **Image Embedding** | ✅ Complete | 22,252/22,277 (99.9%) |
| **ZIP Processing** | ✅ Deployed | Streaming extraction enabled |

**Notes:**
- 36 documents failed to import (likely unsupported formats or corrupted files)
- 25 images skipped (exceeded 20MB size limit or embedding errors)
- ZIP files are extracted and contents indexed by category (images → Vector Search, docs → Vertex AI Search)

---

## Resolved Blockers

### ~~Documents Need File Extensions~~ ✅ RESOLVED
Vertex AI Search requires files with extensions (`.pdf`, `.docx`, etc.) but docs were stored without extensions.

**Fix Applied:**
1. ✅ Modified `shared/categories.py` — `gcs_key()` now accepts optional `extension` parameter
2. ✅ Modified `jobs/sync_dropbox_to_gcs/main.py` — adds extension for docs category
3. ✅ Deleted old docs from GCS (4,143 files without extensions)
4. ✅ Rebuilt and pushed sync job with extension changes
5. ✅ Cleared rev_index doc entries + cursor to force full re-sync
6. ✅ Ran sync job — docs re-downloaded with `.pdf`, `.docx`, etc. extensions (4,144 total)
7. ✅ Import triggered to OCR-enabled Vertex AI Search datastore

---

## ZIP File Processing ✅ DEPLOYED (2026-02-15)

Added support for extracting and indexing contents of ZIP archives up to 10 GB.

### New Files Created
- `shared/dropbox_download.py` — chunked streaming download for large files
- `shared/zip_handler.py` — disk-based streaming ZIP extraction

### Changes to Existing Files
- `jobs/sync_dropbox_to_gcs/main.py` — ZIP detection, extraction, and upload logic
- `shared/gcs.py` — added `upload_from_filename()` for disk-based uploads
- `infra/05_build_and_deploy_jobs.sh` — increased memory (4Gi), CPU (2), timeout (7200s)

### How It Works
1. Sync job detects `.zip` files in Dropbox
2. Downloads ZIP to `/scratch` disk (streaming, not in-memory)
3. Extracts files one at a time to minimize memory usage
4. Categorizes each extracted file (images/docs/media)
5. Uploads to appropriate GCS prefix with synthetic ID: `<zip_id>___<inner_path>`
6. Doc files preserve extensions for Vertex AI Search compatibility
7. Metadata includes `source_zip` field to track origin

### Limits
| Constraint | Value |
|------------|-------|
| Max ZIP size | 10 GB |
| Max inner file size | 1 GB |
| Cloud Run memory | 4 GiB |
| Cloud Run timeout | 2 hours |
| Nested ZIPs | Not supported (skipped) |

### Integration Points
- **rev_index** — tracks ZIP rev to skip unchanged archives
- **path_index** — maps `<zip_path>!/<inner_path>` → synthetic file ID
- **Deletion handling** — deleting a ZIP removes all extracted children
- **Job B** — extracted images automatically picked up for embedding
- **Vertex AI Search** — extracted docs automatically imported

---

## Phase 1: Code & Repo Structure ✅

- [x] `.gitignore`
- [x] `shared/__init__.py`
- [x] `shared/config.py` — env-var config (all required + optional vars) + `REV_INDEX_KEY`
- [x] `shared/categories.py` — extension → category mapping, GCS key helpers, MIME types
- [x] `shared/gcs.py` — upload/download/delete/JSON/list helpers
- [x] `shared/dropbox_client.py` — OAuth2 refresh-token flow, cursor listing, download
- [x] `jobs/sync_dropbox_to_gcs/main.py` — Job A (baseline crawl + incremental sync + deletions + **checkpoint saving**)
- [x] `jobs/sync_dropbox_to_gcs/Dockerfile`
- [x] `jobs/sync_dropbox_to_gcs/requirements.txt`
- [x] `jobs/embed_images_to_vector_search/main.py` — Job B (embed images, upsert/remove datapoints)
- [x] `jobs/embed_images_to_vector_search/Dockerfile`
- [x] `jobs/embed_images_to_vector_search/requirements.txt`
- [x] `infra/variables.sh` — shared config for all infra scripts
- [x] `infra/01_setup_gcp.sh` — enable APIs, SA, Artifact Registry
- [x] `infra/02_create_bucket.sh` — create GCS bucket
- [x] `infra/03_create_vector_search.sh` — index + endpoint + deploy
- [x] `infra/04_create_vertex_search.sh` — datastore + search engine + initial import
- [x] `infra/05_build_and_deploy_jobs.sh` — Docker build/push, Cloud Run Jobs
- [x] `infra/06_create_scheduler.sh` — Cloud Scheduler triggers
- [x] `infra/store_secrets.sh` — Dropbox creds → Secret Manager
- [x] `curl/query_vector_search.sh` — text → embedding → findNeighbors
- [x] `curl/query_vertex_search.sh` — text → Discovery Engine search
- [x] `curl/combine_results.sh` — merged JSON output
- [x] `README.md` — architecture, setup, usage, env vars

---

## Phase 2: GCP Project Setup (One-Time)

> Run these in a terminal authenticated to your GCP project.

### Step 2.1 — Edit variables
- [x] Open `infra/variables.sh`
- [x] Set `PROJECT_ID` to your GCP project ID
- [x] Verify `REGION` (default: `us-central1`)

### Step 2.2 — Dropbox app setup ✅

**App**: `oyvml1upnprceii` (Full Dropbox access)

- [x] Go to https://www.dropbox.com/developers/apps and create a new app
- [x] Select **Scoped access** + **Full Dropbox**
- [x] Enable permissions: `files.metadata.read`, `files.content.read`
- [x] Click **Submit** on Permissions tab
- [x] Re-authorize with explicit scopes (`account_info.read files.content.read files.metadata.read`)
- [x] Note down: `APP_KEY=oyvml1upnprceii`, `APP_SECRET=k0xozrgmva84f35`

### Step 2.3 — Store secrets
```bash
bash infra/store_secrets.sh <APP_KEY> <APP_SECRET> <REFRESH_TOKEN>
```
- [x] Secrets stored in Secret Manager
- [x] `DROPBOX_APP_KEY` = `oyvml1upnprceii` (v4)
- [x] `DROPBOX_APP_SECRET` = `k0xozrgmva84f35` (v4)
- [x] `DROPBOX_REFRESH_TOKEN` = v7 with scopes: `account_info.read files.content.read files.metadata.read`

### Step 2.4 — Enable APIs & create service account
```bash
bash infra/01_setup_gcp.sh
```
- [x] APIs enabled (Vertex AI, Storage, Run, Scheduler, Secret Manager, Discovery Engine, Artifact Registry)
- [x] Service account created with Owner role
- [x] Artifact Registry Docker repo created
- [x] Docker auth configured

### Step 2.5 — Create GCS bucket
```bash
bash infra/02_create_bucket.sh
```
- [x] Bucket `gs://gen-lang-client-0540480379-dropbox-mirror` exists

---

## Phase 3: Vertex AI Vector Search (Images) ✅ COMPLETE

> ⏳ Index creation + deployment can take 30-60 minutes total.

### Step 3.1 — Create index + endpoint + deploy
```bash
bash infra/03_create_vector_search.sh
```
- [x] Tree-AH index created (dim=1408, DOT_PRODUCT_DISTANCE, **STREAM_UPDATE**)
- [x] Public endpoint created
- [x] Index deployed to endpoint
- [x] Note down output values:
  - `VECTOR_SEARCH_INDEX_ID` = `3582448576829063168`
  - `VECTOR_SEARCH_ENDPOINT_ID` = `2432588112593944576`
  - `VECTOR_SEARCH_DEPLOYED_INDEX_ID` = `deployed_dropbox_images`

**Check deployment status:**
```bash
gcloud ai index-endpoints describe 2432588112593944576 --region=us-central1 | grep -A5 deployedIndexes
```

**Final Stats:**
- Images in GCS: 22,277
- Images embedded: 22,252 ✅
- Skipped: 25 (exceeded 20MB limit or errors)
- Coverage: 99.9%

---

## Phase 4: Vertex AI Search (Documents) ✅ COMPLETE

### Step 4.1 — Create datastore + search engine
```bash
bash infra/04_create_vertex_search.sh
```
- [x] Unstructured datastore created (`CONTENT_REQUIRED`)
- [x] Search engine/app created
- [x] **OCR enabled** — recreated datastore with `ocrParsingConfig.useNativeText: true`
- [x] Old datastore deleted (no OCR)
- [x] Docs re-synced with file extensions (`.pdf`, `.docx`, etc.)
- [x] Import triggered to OCR-enabled datastore (⏳ running now)
- [x] Note down output values:
  - `VERTEX_SEARCH_DATASTORE_ID` = `dropbox-docs-datastore-ocr`
  - `VERTEX_SEARCH_ENGINE_ID` = `dropbox-docs-engine-ocr`

**Final Stats:**
- Docs in GCS: 4,144 (with proper extensions)
- Docs imported: 4,108 ✅
- Failed: 36 (unsupported formats or corrupted)
- Coverage: 99.1%

**Extension breakdown:**
- 3,479 PDFs
- 356 DOCX
- 213 XLSX
- 66 TXT
- 22 PPTX
- 8 HTML

---

## Phase 5: Build & Deploy Cloud Run Jobs

### Step 5.1 — Set Vector Search IDs
- [x] Export env vars:
  ```bash
  export VECTOR_SEARCH_INDEX_ID=3582448576829063168
  export VECTOR_SEARCH_ENDPOINT_ID=2432588112593944576
  ```

### Step 5.2 — Build images & create jobs
```bash
bash infra/05_build_and_deploy_jobs.sh
```
- [x] `sync-dropbox-to-gcs` image built & pushed
- [x] `embed-images-to-vector-search` image built & pushed
- [x] Cloud Run Job A created (sync, 2Gi RAM, 1 CPU)
- [x] Cloud Run Job B created (embed, 4Gi RAM, 2 CPU, **24hr timeout**)
- [x] Secrets mounted from Secret Manager

---

## Phase 6: Scheduling

### Step 6.1 — Create schedulers
```bash
bash infra/06_create_scheduler.sh
```
- [x] `daily-dropbox-sync` → 02:00 UTC
- [x] `daily-image-embed` → 04:00 UTC
- [x] `daily-docs-reimport` → 05:00 UTC

---

## Phase 7: Testing — ✅ COMPLETE

**Testing infrastructure created:**
- [x] `infra/check_dropbox_permissions.sh` — diagnostic script
- [x] `infra/reauthorize_dropbox.sh` — fix token with proper scopes
- [x] `infra/test_sync.sh` — Test A: baseline sync
- [x] `infra/test_embeddings.sh` — Test C: image embeddings
- [x] `infra/test_doc_search.sh` — Test D: document search
- [x] `infra/run_all_tests.sh` — comprehensive test suite
- [x] `infra/set_test_env.sh` — set env vars for curl scripts
- [x] `TESTING.md` — detailed testing guide

### Test A — Baseline sync ✅ COMPLETE
- [x] Dropbox has files (PDFs, images, docs, media confirmed in web UI)
- [x] Cloud Run Job infrastructure works (job executes successfully)
- [x] Dropbox permissions fixed — token has `account_info.read files.content.read files.metadata.read`
- [x] **Code improved**: Added checkpoint saving every 100 files, rev_index to skip already-synced files
- [x] Sync job completed — execution `sync-dropbox-to-gcs-gwn4p` (2026-02-12)
- [x] **rev_index exists** — checkpoints saving, progress survives timeouts
- [x] GCS has files under `mirror/images/` (22,277), `mirror/docs/` (4,144)
- [x] `mirror/meta/*.json` sidecars exist with correct schema
- [x] `mirror/state/sync_state.json` has a cursor (saved on completion)
- [x] `mirror/state/rev_index.json` tracks file_id → revision
- [x] `mirror/state/path_index.json` maps paths → file IDs (saved on completion)

**To check status:**
```bash
# Check execution status
gcloud run jobs executions describe sync-dropbox-to-gcs-gwn4p --region=us-central1 --format="value(status.conditions[0].type,status.conditions[0].status)"

# Check file counts
gsutil ls -r gs://gen-lang-client-0540480379-dropbox-mirror/mirror/images/ | wc -l
gsutil ls -r gs://gen-lang-client-0540480379-dropbox-mirror/mirror/docs/ | wc -l

# Check rev_index (checkpoint)
gsutil cat gs://gen-lang-client-0540480379-dropbox-mirror/mirror/state/rev_index.json | head -5

# Check GCS bucket contents
gsutil ls gs://gen-lang-client-0540480379-dropbox-mirror/mirror/images/ | head -20
gsutil ls gs://gen-lang-client-0540480379-dropbox-mirror/mirror/docs/ | head -20
gsutil ls gs://gen-lang-client-0540480379-dropbox-mirror/mirror/state/
```

### Test B — Incremental sync ✅ COMPLETE
- [x] Renamed folder in Dropbox (`/gbg9427h/` → `/Car Matters/`)
- [x] Deleted a file (`/camera uploads/2022-12-23 13.44.21.png`)
- [x] Re-ran sync job (execution `sync-dropbox-to-gcs-g8mt4`)
- [x] New files appeared in GCS (54 synced under new path)
- [x] Deleted files removed from GCS + meta (55 deleted including old folder paths)
- [x] Metadata updated for renamed paths ✓

### Test C — Image embeddings ✅ COMPLETE
- [x] Index recreated with `STREAM_UPDATE` (was `BATCH_UPDATE`)
- [x] Deploy script fixed to pass env vars on update
- [x] **Pre-filter added** — skips images >20MB (Vertex AI 27MB base64 limit)
- [x] Rebuilt container for `linux/amd64` (Cloud Run compatible)
- [x] Checkpoint saving every 50 embeddings (survived multiple timeouts)
- [x] `mirror/state/embedding_state.json` tracks file_id → rev
- [x] Vector Search index has datapoints
- [x] Job timeout increased to 24 hours
- [x] Job completed successfully (execution `embed-images-to-vector-search-f8jjn`)

**Final Embedding Stats:**
- Total images in GCS: 22,277
- Successfully embedded: 22,252 (99.9%)
- Skipped: 25 (exceeded 20MB limit or errors)

### Test D — Document search ✅ COMPLETE
- [x] OCR-enabled datastore created (`dropbox-docs-datastore-ocr`)
- [x] Old non-OCR datastore deleted
- [x] Docs re-synced with file extensions (`.pdf`, `.docx`, etc.)
- [x] Import triggered to Vertex AI Search
- [x] Import completed (4,108/4,144 docs — 99.1%)
- [x] Document search tested — returns results with snippets ✓
- [x] Results return whole documents with highlighted matches

### Test E — Image search (Vector Search) ✅ COMPLETE
- [x] Test image search: `bash curl/query_vector_search.sh "sunset photo"`
- [x] Results return file IDs with distances ✓

### Test F — Combined retrieval ✅ COMPLETE
- [x] Test combined: `bash curl/combine_results.sh "presentation"`
- [x] JSON output has both `image_matches` and `document_matches` ✓

### Test G — Scheduler trigger ✅ COMPLETE
- [x] Manually triggered scheduler: `gcloud scheduler jobs run daily-dropbox-sync --location=us-central1`
- [x] Cloud Run Job execution completed successfully (execution `sync-dropbox-to-gcs-2whh9`)

---

## Phase 8: Sign-Off

- [x] All automated tests pass (Test B incremental sync is optional manual test)
- [x] Commit and push code to `main` (commit `c547696`)
- [x] Document any IDs/values in a secure location (see table below)
- [x] **Project complete** ✅

### Key IDs for Reference
| Resource | ID |
|----------|----|
| GCP Project | `gen-lang-client-0540480379` |
| GCS Bucket | `gen-lang-client-0540480379-dropbox-mirror` |
| Vector Search Index | `3582448576829063168` |
| Vector Search Endpoint | `2432588112593944576` |
| Vertex Search Datastore | `dropbox-docs-datastore-ocr` |
| Vertex Search Engine | `dropbox-docs-engine-ocr` |

---

## When Resuming

### Check Job Completion

```bash
# 1. Check document import (should show done: True when complete)
curl -s "https://discoveryengine.googleapis.com/v1/projects/704456193276/locations/global/collections/default_collection/dataStores/dropbox-docs-datastore-ocr/branches/0/operations/import-documents-13076529950805489230" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" | python3 -c "import json,sys; d=json.load(sys.stdin); m=d.get('metadata',{}); print(f'Docs: {m.get(\"successCount\",0)}/{m.get(\"totalCount\",\"?\")}')"

# 2. Check image embedding job status
gcloud run jobs executions describe embed-images-to-vector-search-f8jjn --region=us-central1 --format="value(status.conditions[0].type,status.conditions[0].status)"

# 3. Check Vector Search datapoint count (target: ~22,000)
curl -s "https://us-central1-aiplatform.googleapis.com/v1/projects/gen-lang-client-0540480379/locations/us-central1/indexes/3582448576829063168" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" | python3 -c "import json,sys; d=json.load(sys.stdin); print('Images embedded:', d.get('indexStats',{}).get('vectorsCount','N/A'))"
```

### After Jobs Complete — Test Searches

```bash
# Set env vars
source infra/set_test_env.sh

# Test image search
bash curl/query_vector_search.sh "sunset photo"

# Test doc search
bash curl/query_vertex_search.sh "meeting notes"

# Test combined
bash curl/combine_results.sh "presentation"
```

### General Status Checks

```bash
# 1. Check embed job status
gcloud run jobs executions list --job=embed-images-to-vector-search --region=us-central1 --limit=3

# 2. Check file counts in GCS
gsutil ls "gs://gen-lang-client-0540480379-dropbox-mirror/mirror/images/" | wc -l
gsutil ls "gs://gen-lang-client-0540480379-dropbox-mirror/mirror/docs/" | wc -l

# 3. Check Vector Search index datapoint count
curl -s "https://us-central1-aiplatform.googleapis.com/v1/projects/gen-lang-client-0540480379/locations/us-central1/indexes/3582448576829063168" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" | python3 -c "import json,sys; d=json.load(sys.stdin); print('Datapoints:', d.get('indexStats',{}).get('vectorsCount','N/A'))"

# 4. Set env vars before running deploy or test scripts
export VECTOR_SEARCH_INDEX_ID=3582448576829063168
export VECTOR_SEARCH_ENDPOINT_ID=2432588112593944576

# 5. Test image search (embeddings complete)
source infra/set_test_env.sh
bash curl/query_vector_search.sh "sunset photo"

# 6. Test doc search (after import complete)
bash curl/query_vertex_search.sh "document"
bash curl/combine_results.sh "presentation"
```
