# Dropbox → GCS → Vertex AI Search & Multimodal Embeddings

Whole-file retrieval system that mirrors Dropbox to Google Cloud Storage,
indexes **images** via Vertex AI Vector Search (multimodal embeddings) and
**documents** via Vertex AI Search — queried exclusively through **cURL**.

---

## 🚀 Quick Start

**Infrastructure deployed?** → See [TESTING.md](TESTING.md) for unblocking and testing.

**Starting fresh?** → Follow [Setup](#setup-one-time) below.

**Current Status**: Infrastructure complete. **Testing blocked** — Dropbox permissions need fixing. See [TESTING.md](TESTING.md).

---

## Architecture

```
Dropbox (source of truth)
  │
  ▼
Cloud Run Job A  (daily sync)
  │
  ▼
GCS  gs://<PROJECT>-dropbox-mirror/
  ├── mirror/images/<file_id>          ─► Cloud Run Job B ─► Vertex AI Vector Search
  ├── mirror/docs/<file_id>            ─► Vertex AI Search datastore (periodic import)
  ├── mirror/media/<file_id>           (stored only)
  ├── mirror/meta/<file_id>.json       (metadata sidecar)
  └── mirror/state/
        ├── sync_state.json            (Dropbox cursor)
        ├── path_index.json            (path → file_id reverse lookup)
        └── embedding_state.json       (file_id → embedded rev)

Retrieval: cURL only (no Python search API)
  ├── curl/query_vector_search.sh      text → embedding → findNeighbors (images)
  ├── curl/query_vertex_search.sh      text → Discovery Engine search  (docs)
  └── curl/combine_results.sh          both queries, merged JSON output
```

---

## Repo Structure

```
.
├── shared/                            # Shared Python library
│   ├── config.py                      # Env-var config
│   ├── categories.py                  # Extension → category mapping
│   ├── gcs.py                         # GCS helper functions
│   └── dropbox_client.py              # Dropbox SDK wrapper (refresh-token)
│
├── jobs/
│   ├── sync_dropbox_to_gcs/           # Job A — Dropbox → GCS mirror
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── embed_images_to_vector_search/ # Job B — image embeddings → Vector Search
│       ├── main.py
│       ├── Dockerfile
│       └── requirements.txt
│
├── infra/                             # One-time GCP provisioning (gcloud)
│   ├── variables.sh                   # ← EDIT THIS FIRST
│   ├── 01_setup_gcp.sh
│   ├── 02_create_bucket.sh
│   ├── 03_create_vector_search.sh
│   ├── 04_create_vertex_search.sh
│   ├── 05_build_and_deploy_jobs.sh
│   ├── 06_create_scheduler.sh
│   └── store_secrets.sh
│
└── curl/                               # cURL-only retrieval scripts
    ├── query_vector_search.sh
    ├── query_vertex_search.sh
    └── combine_results.sh
```

---

## Prerequisites

| Requirement | Detail |
|---|---|
| Google Cloud project | Billing enabled |
| `gcloud` CLI | Authenticated (`gcloud auth login`) |
| Docker | For building Cloud Run Job images |
| Dropbox app | Scoped access, `files.metadata.read` + `files.content.read` |
| Dropbox refresh token | OAuth2 flow → app key, app secret, refresh token |

---

## Environment Variables

All configuration is via environment variables (no `.env` files).

### Always required

| Variable | Description |
|---|---|
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCS_BUCKET_NAME` | GCS bucket name |
| `DROPBOX_APP_KEY` | Dropbox app key |
| `DROPBOX_APP_SECRET` | Dropbox app secret |
| `DROPBOX_REFRESH_TOKEN` | Dropbox OAuth2 refresh token |

### Required after infra setup

| Variable | Description |
|---|---|
| `GCP_REGION` | Default: `us-central1` |
| `VECTOR_SEARCH_INDEX_ID` | From `03_create_vector_search.sh` output |
| `VECTOR_SEARCH_ENDPOINT_ID` | From `03_create_vector_search.sh` output |
| `VECTOR_SEARCH_DEPLOYED_INDEX_ID` | From `03_create_vector_search.sh` output |
| `VERTEX_SEARCH_DATASTORE_ID` | From `04_create_vertex_search.sh` output |
| `VERTEX_SEARCH_ENGINE_ID` | From `04_create_vertex_search.sh` output |

---

## Setup (One-Time)

### 1. Edit variables

```bash
vim infra/variables.sh   # set PROJECT_ID at minimum
```

### 2. Store Dropbox secrets

```bash
bash infra/store_secrets.sh <APP_KEY> <APP_SECRET> <REFRESH_TOKEN>
```

### 3. Run infra scripts in order

```bash
bash infra/01_setup_gcp.sh
bash infra/02_create_bucket.sh
bash infra/03_create_vector_search.sh    # ⏳ ~30-60 min (index + deploy)
bash infra/04_create_vertex_search.sh
bash infra/05_build_and_deploy_jobs.sh   # edit Vector Search IDs first
bash infra/06_create_scheduler.sh
```

Each script prints the resource IDs you need for the next step.

---

## Manual Execution

```bash
# Run sync (Dropbox → GCS)
gcloud run jobs execute sync-dropbox-to-gcs --region=us-central1

# Run embedding (images → Vector Search)
gcloud run jobs execute embed-images-to-vector-search --region=us-central1
```

Or locally (for development):

```bash
export GCP_PROJECT_ID=my-project
export GCS_BUCKET_NAME=my-project-dropbox-mirror
export DROPBOX_APP_KEY=xxx
export DROPBOX_APP_SECRET=xxx
export DROPBOX_REFRESH_TOKEN=xxx

python jobs/sync_dropbox_to_gcs/main.py

export VECTOR_SEARCH_INDEX_ID=123456
export VECTOR_SEARCH_ENDPOINT_ID=789012
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=deployed_dropbox_images
python jobs/embed_images_to_vector_search/main.py
```

---

## Querying (cURL Only)

### Search images by text

```bash
export GCP_PROJECT_ID=my-project
export VECTOR_SEARCH_ENDPOINT_ID=789012
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=deployed_dropbox_images

bash curl/query_vector_search.sh "a sunset over the ocean"
```

### Search documents by text

```bash
export GCP_PROJECT_ID=my-project
export VERTEX_SEARCH_DATASTORE_ID=dropbox-docs-datastore

bash curl/query_vertex_search.sh "quarterly revenue report"
```

### Combined search (images + docs)

```bash
# Set all env vars above, then:
bash curl/combine_results.sh "team meeting presentation"
```

Output is JSON:

```json
{
  "query": "team meeting presentation",
  "image_matches": [
    {"file_id": "abc123", "distance": 0.87}
  ],
  "document_matches": [
    {"document_id": "xyz", "title": "Q4 Presentation.pptx", "link": "...", "snippet": "..."}
  ]
}
```

---

## File Categories

| Category | Extensions | GCS prefix | Indexed by |
|---|---|---|---|
| images | bmp gif jpg jpeg png | `mirror/images/` | Vector Search (multimodal embeddings, dim=1408) |
| docs | pdf docx xlsx pptx txt html | `mirror/docs/` | Vertex AI Search (unstructured) |
| media | mp3 wav mp4 mov | `mirror/media/` | Stored only (no indexing) |

---

## Metadata Schema

Each file gets a JSON sidecar at `mirror/meta/<file_id>.json`:

```json
{
  "dropbox_file_id": "abc123def456",
  "dropbox_path": "/Photos/sunset.jpg",
  "rev": "015f2a...",
  "mime_type": "image/jpeg",
  "size": 2048576,
  "server_modified": "2025-12-01 10:30:00",
  "category": "images",
  "gcs_uri": "gs://my-project-dropbox-mirror/mirror/images/abc123def456",
  "caption": "sunset.jpg"
}
```

---

## Scheduling

| Job | Schedule | Purpose |
|---|---|---|
| `daily-dropbox-sync` | 02:00 UTC | Dropbox → GCS incremental sync |
| `daily-image-embed` | 04:00 UTC | New/changed images → Vector Search |
| `daily-docs-reimport` | 05:00 UTC | Re-import docs into Vertex AI Search |

---

## Testing

**See [TESTING.md](TESTING.md) for comprehensive test guide.**

Quick diagnostic:

```bash
# Check if Dropbox permissions are correct
bash infra/check_dropbox_permissions.sh

# Fix permissions & re-authorize
bash infra/reauthorize_dropbox.sh

# Run all tests
bash infra/run_all_tests.sh
```

Individual tests:

```bash
# Test sync
bash infra/test_sync.sh

# Test embeddings
bash infra/test_embeddings.sh

# Test document search
bash infra/test_doc_search.sh

# Test queries
bash curl/query_vector_search.sh "test query"
bash curl/query_vertex_search.sh "test query"
bash curl/combine_results.sh "test query"
```

---

## Non-Goals

This project intentionally does **NOT** include:

- RAG pipelines
- Enterprise search UI / connectors
- OCR processing
- AI captioning / tagging
- Document chunking / passage retrieval
- Pub/Sub realtime ingestion
- BigQuery indexing
- Python search backend API