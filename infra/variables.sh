#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Shared variables sourced by all infra scripts.
# Edit these values ONCE before running any script.
# ─────────────────────────────────────────────────────────────

export PROJECT_ID="gen-lang-client-0540480379"
export REGION="us-central1"
export BUCKET_NAME="${PROJECT_ID}-dropbox-mirror"

# Artifact Registry
export AR_REPO="dropbox-mirror"
export AR_LOCATION="${REGION}"

# Service account
export SA_NAME="dropbox-mirror-sa"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Cloud Run Jobs
export JOB_SYNC="sync-dropbox-to-gcs"
export JOB_EMBED="embed-images-to-vector-search"

# Container images
export IMAGE_SYNC="${AR_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${JOB_SYNC}:latest"
export IMAGE_EMBED="${AR_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${JOB_EMBED}:latest"

# Vector Search
export VS_INDEX_DISPLAY_NAME="dropbox-image-index"
export VS_ENDPOINT_DISPLAY_NAME="dropbox-image-endpoint"
export VS_DEPLOYED_INDEX_ID="deployed_dropbox_images"

# Vertex AI Search (Discovery Engine) — with OCR enabled
export DATASTORE_ID="dropbox-docs-datastore-ocr"
export SEARCH_ENGINE_ID="dropbox-docs-engine-ocr"

# Cloud Scheduler
export SCHEDULER_SYNC="daily-dropbox-sync"
export SCHEDULER_EMBED="daily-image-embed"
export SCHEDULER_REIMPORT="daily-docs-reimport"

# Dropbox credentials — stored in Secret Manager
export SECRET_DROPBOX_APP_KEY="DROPBOX_APP_KEY"
export SECRET_DROPBOX_APP_SECRET="DROPBOX_APP_SECRET"
export SECRET_DROPBOX_REFRESH_TOKEN="DROPBOX_REFRESH_TOKEN"
