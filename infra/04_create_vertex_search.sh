#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# 04 — Create Vertex AI Search datastore + search engine
# ─────────────────────────────────────────────────────────────
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

echo "═══ Creating unstructured data store ═══"
curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores?dataStoreId=${DATASTORE_ID}" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "Dropbox Docs Datastore",
    "industryVertical": "GENERIC",
    "contentConfig": "CONTENT_REQUIRED",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"]
  }' | python3 -m json.tool || true

echo ""
echo "═══ Creating search engine / app ═══"
curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines?engineId=${SEARCH_ENGINE_ID}" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "Dropbox Docs Search Engine",
    "dataStoreIds": ["'"${DATASTORE_ID}"'"],
    "solutionType": "SOLUTION_TYPE_SEARCH",
    "searchEngineConfig": {
      "searchTier": "SEARCH_TIER_STANDARD",
      "searchAddOns": ["SEARCH_ADD_ON_LLM"]
    }
  }' | python3 -m json.tool || true

echo ""
echo "═══ Triggering initial import from GCS ═══"
curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores/${DATASTORE_ID}/branches/default_branch/documents:import" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${BUCKET_NAME}"'/mirror/docs/**"]
    },
    "reconciliationMode": "INCREMENTAL"
  }' | python3 -m json.tool || true

echo ""
echo "════════════════════════════════════════════════"
echo "✓ Vertex AI Search configured"
echo ""
echo "  DATASTORE_ID      = ${DATASTORE_ID}"
echo "  SEARCH_ENGINE_ID  = ${SEARCH_ENGINE_ID}"
echo ""
echo "Set these as env vars for Cloud Run Jobs:"
echo "  VERTEX_SEARCH_DATASTORE_ID=${DATASTORE_ID}"
echo "  VERTEX_SEARCH_ENGINE_ID=${SEARCH_ENGINE_ID}"
echo "════════════════════════════════════════════════"
echo ""
echo "Next → run 05_build_and_deploy_jobs.sh"
