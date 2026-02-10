# IMPLEMENTATION PLAN — Dropbox → GCS → Vertex AI

**Status**: Baseline sync **RUNNING** (execution `sync-dropbox-to-gcs-2wm5t`). Dropbox permissions fixed. Remaining: verify sync, run embedding + search tests.

---

## Phase 1: Code & Repo Structure ✅

- [x] `.gitignore`
- [x] `shared/__init__.py`
- [x] `shared/config.py` — env-var config (all required + optional vars)
- [x] `shared/categories.py` — extension → category mapping, GCS key helpers, MIME types
- [x] `shared/gcs.py` — upload/download/delete/JSON/list helpers
- [x] `shared/dropbox_client.py` — OAuth2 refresh-token flow, cursor listing, download
- [x] `jobs/sync_dropbox_to_gcs/main.py` — Job A (baseline crawl + incremental sync + deletions)
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

## Phase 3: Vertex AI Vector Search (Images)

> ⏳ Index creation + deployment can take 30-60 minutes total.

### Step 3.1 — Create index + endpoint + deploy
```bash
bash infra/03_create_vector_search.sh
```
- [x] Tree-AH index created (dim=1408, DOT_PRODUCT_DISTANCE, BATCH_UPDATE)
- [x] Public endpoint created
- [x] Index deployed to endpoint
- [x] Note down output values:
  - `VECTOR_SEARCH_INDEX_ID` = `8915836435542573056`
  - `VECTOR_SEARCH_ENDPOINT_ID` = `7079528871854342144`
  - `VECTOR_SEARCH_DEPLOYED_INDEX_ID` = `deployed_dropbox_images`

**Check deployment status:**
```bash
gcloud ai index-endpoints describe 7079528871854342144 --region=us-central1 | grep -A5 deployedIndexes
```

---

## Phase 4: Vertex AI Search (Documents)

### Step 4.1 — Create datastore + search engine
```bash
bash infra/04_create_vertex_search.sh
```
- [x] Unstructured datastore created (`CONTENT_REQUIRED`)
- [x] Search engine/app created
- [ ] Initial import triggered from `gs://…/mirror/docs/**` (skipped — bucket empty until first sync)
- [x] Note down output values:
  - `VERTEX_SEARCH_DATASTORE_ID` = `dropbox-docs-datastore`
  - `VERTEX_SEARCH_ENGINE_ID` = `dropbox-docs-engine`

---

## Phase 5: Build & Deploy Cloud Run Jobs

### Step 5.1 — Set Vector Search IDs
- [x] Export env vars:
  ```bash
  export VECTOR_SEARCH_INDEX_ID=8915836435542573056
  export VECTOR_SEARCH_ENDPOINT_ID=7079528871854342144
  ```

### Step 5.2 — Build images & create jobs
```bash
bash infra/05_build_and_deploy_jobs.sh
```
- [x] `sync-dropbox-to-gcs` image built & pushed
- [x] `embed-images-to-vector-search` image built & pushed
- [x] Cloud Run Job A created (sync, 2Gi RAM, 1 CPU)
- [x] Cloud Run Job B created (embed, 4Gi RAM, 2 CPU)
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

## Phase 7: Testing — IN PROGRESS

**Testing infrastructure created:**
- [x] `infra/check_dropbox_permissions.sh` — diagnostic script
- [x] `infra/reauthorize_dropbox.sh` — fix token with proper scopes
- [x] `infra/test_sync.sh` — Test A: baseline sync
- [x] `infra/test_embeddings.sh` — Test C: image embeddings
- [x] `infra/test_doc_search.sh` — Test D: document search
- [x] `infra/run_all_tests.sh` — comprehensive test suite
- [x] `infra/set_test_env.sh` — set env vars for curl scripts
- [x] `TESTING.md` — detailed testing guide

### Test A — Baseline sync ⏳ RUNNING
- [x] Dropbox has files (PDFs, images, docs, media confirmed in web UI)
- [x] Cloud Run Job infrastructure works (job executes successfully)
- [x] Dropbox permissions fixed — token has `account_info.read files.content.read files.metadata.read`
- [x] Sync job started — execution `sync-dropbox-to-gcs-2wm5t` (2026-02-10 11:22 UTC)
- [x] Logs confirm files syncing: Camera Uploads → `mirror/images/`
- [ ] Verify GCS has files under `mirror/images/`, `mirror/docs/`, `mirror/media/`
- [ ] Verify `mirror/meta/*.json` sidecars exist with correct schema
- [ ] Verify `mirror/state/sync_state.json` has a cursor
- [ ] Verify `mirror/state/path_index.json` maps paths → file IDs

**To check status when resuming:**
```bash
# Check if sync completed
gcloud run jobs executions describe sync-dropbox-to-gcs-2wm5t --region=us-central1 --format="value(status.conditions[0].type,status.conditions[0].status)"

# Check GCS bucket contents
gsutil ls gs://gen-lang-client-0540480379-dropbox-mirror/mirror/images/ | head -20
gsutil ls gs://gen-lang-client-0540480379-dropbox-mirror/mirror/docs/ | head -20
gsutil ls gs://gen-lang-client-0540480379-dropbox-mirror/mirror/state/
```

### Test B — Incremental sync
- [ ] Rename a folder in Dropbox
- [ ] Add a new file, delete another
- [ ] Re-run sync job
- [ ] Verify new file appeared in GCS
- [ ] Verify deleted file removed from GCS + meta
- [ ] Verify metadata updated for renamed paths

### Test C — Image embeddings
- [ ] Run embed job:
  ```bash
  gcloud run jobs execute embed-images-to-vector-search --region=us-central1
  ```
- [ ] Verify `mirror/state/embedding_state.json` tracks file_id → rev
- [ ] Verify Vector Search index has datapoints (via `gcloud ai indexes describe`)

### Test D — Document search
- [ ] Wait for Vertex AI Search indexing to complete (~minutes)
- [ ] Test document search:
  ```bash
  source infra/set_test_env.sh
  bash curl/query_vertex_search.sh "test document query"
  ```
- [ ] Verify results return whole documents

### Test E — Image search (Vector Search)
- [ ] Test image search:
  ```bash
  source infra/set_test_env.sh
  bash curl/query_vector_search.sh "a photo of a cat"
  ```
- [ ] Verify results return file IDs with distances

### Test F — Combined retrieval
- [ ] Test combined:
  ```bash
  source infra/set_test_env.sh
  bash curl/combine_results.sh "meeting presentation"
  ```
- [ ] Verify JSON output has both `image_matches` and `document_matches`

### Test G — Scheduler trigger
- [ ] Manually trigger scheduler:
  ```bash
  gcloud scheduler jobs run daily-dropbox-sync --location=us-central1
  ```
- [ ] Verify Cloud Run Job execution completes successfully

---

## Phase 8: Sign-Off

- [ ] All tests pass
- [ ] Commit and push code to `main`
- [ ] Document any IDs/values in a secure location
- [ ] Project complete

---

## When Resuming

```bash
# 1. Check if baseline sync completed
gcloud run jobs executions describe sync-dropbox-to-gcs-2wm5t \
  --region=us-central1 \
  --format="value(status.conditions[0].type,status.conditions[0].status)"

# 2. If completed successfully, verify GCS contents
gsutil ls gs://gen-lang-client-0540480379-dropbox-mirror/mirror/ | head -20

# 3. Run image embeddings
gcloud run jobs execute embed-images-to-vector-search --region=us-central1

# 4. Test search queries
source infra/set_test_env.sh
bash curl/query_vector_search.sh "sunset photo"
bash curl/query_vertex_search.sh "document"
bash curl/combine_results.sh "presentation"
```
