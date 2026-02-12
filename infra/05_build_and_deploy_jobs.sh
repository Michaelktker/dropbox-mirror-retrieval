#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# 05 — Build Docker images, push to Artifact Registry,
#       create Cloud Run Jobs.
#
# PREREQUISITES:
#   - Artifact Registry repo exists    (01_setup_gcp.sh)
#   - Secrets stored in Secret Manager (manual step — see README)
#   - Vector Search & Vertex AI Search IDs known (03, 04 scripts)
#
# USAGE:
#   Edit the VECTOR_SEARCH_* and VERTEX_SEARCH_* values below,
#   then run this script from the repo root.
# ─────────────────────────────────────────────────────────────
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/variables.sh"

# ── Values from infra scripts 03/04 (EDIT THESE) ─────────
VECTOR_SEARCH_INDEX_ID="${VECTOR_SEARCH_INDEX_ID:-REPLACE_ME}"
VECTOR_SEARCH_ENDPOINT_ID="${VECTOR_SEARCH_ENDPOINT_ID:-REPLACE_ME}"
VERTEX_SEARCH_DATASTORE_ID_VAL="${VERTEX_SEARCH_DATASTORE_ID:-${DATASTORE_ID}}"
VERTEX_SEARCH_ENGINE_ID_VAL="${VERTEX_SEARCH_ENGINE_ID:-${SEARCH_ENGINE_ID}}"

echo "═══ Building & pushing sync job image ═══"
docker build \
  -t "${IMAGE_SYNC}" \
  -f "${REPO_ROOT}/jobs/sync_dropbox_to_gcs/Dockerfile" \
  "${REPO_ROOT}"
docker push "${IMAGE_SYNC}"

echo ""
echo "═══ Building & pushing embed job image ═══"
docker build \
  -t "${IMAGE_EMBED}" \
  -f "${REPO_ROOT}/jobs/embed_images_to_vector_search/Dockerfile" \
  "${REPO_ROOT}"
docker push "${IMAGE_EMBED}"

echo ""
echo "═══ Creating Cloud Run Job: ${JOB_SYNC} ═══"
gcloud run jobs create "${JOB_SYNC}" \
  --image="${IMAGE_SYNC}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --task-timeout=3600 \
  --max-retries=2 \
  --memory=2Gi \
  --cpu=1 \
  --service-account="${SA_EMAIL}" \
  --set-env-vars="\
GCP_PROJECT_ID=${PROJECT_ID},\
GCP_REGION=${REGION},\
GCS_BUCKET_NAME=${BUCKET_NAME}" \
  --set-secrets="\
DROPBOX_APP_KEY=${SECRET_DROPBOX_APP_KEY}:latest,\
DROPBOX_APP_SECRET=${SECRET_DROPBOX_APP_SECRET}:latest,\
DROPBOX_REFRESH_TOKEN=${SECRET_DROPBOX_REFRESH_TOKEN}:latest" \
  --quiet || \
gcloud run jobs update "${JOB_SYNC}" \
  --image="${IMAGE_SYNC}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --set-env-vars="\
GCP_PROJECT_ID=${PROJECT_ID},\
GCP_REGION=${REGION},\
GCS_BUCKET_NAME=${BUCKET_NAME}" \
  --quiet

echo ""
echo "═══ Creating Cloud Run Job: ${JOB_EMBED} ═══"
gcloud run jobs create "${JOB_EMBED}" \
  --image="${IMAGE_EMBED}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --task-timeout=3600 \
  --max-retries=2 \
  --memory=4Gi \
  --cpu=2 \
  --service-account="${SA_EMAIL}" \
  --set-env-vars="\
GCP_PROJECT_ID=${PROJECT_ID},\
GCP_REGION=${REGION},\
GCS_BUCKET_NAME=${BUCKET_NAME},\
VECTOR_SEARCH_INDEX_ID=${VECTOR_SEARCH_INDEX_ID},\
VECTOR_SEARCH_ENDPOINT_ID=${VECTOR_SEARCH_ENDPOINT_ID},\
VECTOR_SEARCH_DEPLOYED_INDEX_ID=${VS_DEPLOYED_INDEX_ID},\
VERTEX_SEARCH_DATASTORE_ID=${VERTEX_SEARCH_DATASTORE_ID_VAL},\
VERTEX_SEARCH_ENGINE_ID=${VERTEX_SEARCH_ENGINE_ID_VAL}" \
  --set-secrets="\
DROPBOX_APP_KEY=${SECRET_DROPBOX_APP_KEY}:latest,\
DROPBOX_APP_SECRET=${SECRET_DROPBOX_APP_SECRET}:latest,\
DROPBOX_REFRESH_TOKEN=${SECRET_DROPBOX_REFRESH_TOKEN}:latest" \
  --quiet || \
gcloud run jobs update "${JOB_EMBED}" \
  --image="${IMAGE_EMBED}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --set-env-vars="\
GCP_PROJECT_ID=${PROJECT_ID},\
GCP_REGION=${REGION},\
GCS_BUCKET_NAME=${BUCKET_NAME},\
VECTOR_SEARCH_INDEX_ID=${VECTOR_SEARCH_INDEX_ID},\
VECTOR_SEARCH_ENDPOINT_ID=${VECTOR_SEARCH_ENDPOINT_ID},\
VECTOR_SEARCH_DEPLOYED_INDEX_ID=${VS_DEPLOYED_INDEX_ID},\
VERTEX_SEARCH_DATASTORE_ID=${VERTEX_SEARCH_DATASTORE_ID_VAL},\
VERTEX_SEARCH_ENGINE_ID=${VERTEX_SEARCH_ENGINE_ID_VAL}" \
  --quiet

echo ""
echo "✓ Cloud Run Jobs created"
echo "  ${JOB_SYNC}   → ${IMAGE_SYNC}"
echo "  ${JOB_EMBED}  → ${IMAGE_EMBED}"
echo ""
echo "Manual test:"
echo "  gcloud run jobs execute ${JOB_SYNC} --region=${REGION}"
echo "  gcloud run jobs execute ${JOB_EMBED} --region=${REGION}"
echo ""
echo "Next → run 06_create_scheduler.sh"
