#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# 01 — Enable APIs, create service account, Artifact Registry
# ─────────────────────────────────────────────────────────────
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

echo "═══ Setting project to ${PROJECT_ID} ═══"
gcloud config set project "${PROJECT_ID}"

echo "═══ Enabling APIs ═══"
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  discoveryengine.googleapis.com \
  artifactregistry.googleapis.com \
  --quiet

echo "═══ Creating service account ═══"
if ! gcloud iam service-accounts describe "${SA_EMAIL}" &>/dev/null; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="Dropbox Mirror SA"
fi

echo "═══ Granting Owner role (per spec) ═══"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/owner" \
  --condition=None \
  --quiet

echo "═══ Creating Artifact Registry repo ═══"
if ! gcloud artifacts repositories describe "${AR_REPO}" \
    --location="${AR_LOCATION}" &>/dev/null; then
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${AR_LOCATION}" \
    --description="Dropbox mirror job images"
fi

echo "═══ Configuring Docker auth for Artifact Registry ═══"
gcloud auth configure-docker "${AR_LOCATION}-docker.pkg.dev" --quiet

echo ""
echo "✓ APIs enabled"
echo "✓ Service account: ${SA_EMAIL}"
echo "✓ Artifact Registry: ${AR_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"
echo ""
echo "Next → run 02_create_bucket.sh"
