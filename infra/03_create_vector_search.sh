#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# 03 — Create Vertex AI Vector Search index + endpoint + deploy
#
# NOTE: Index creation can take 20-40 minutes.
#       Endpoint creation ~5 min; deploy ~30 min.
#       This script polls until each step completes.
# ─────────────────────────────────────────────────────────────
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

DIMENSIONS=1408

echo "═══ Creating Vector Search tree-AH index (dim=${DIMENSIONS}, STREAM_UPDATE) ═══"

# Create temporary metadata file - with indexUpdateMethod for streaming updates
METADATA_FILE=$(mktemp)
cat > "${METADATA_FILE}" <<EOF
{
  "contentsDeltaUri": "",
  "config": {
    "dimensions": ${DIMENSIONS},
    "approximateNeighborsCount": 150,
    "distanceMeasureType": "DOT_PRODUCT_DISTANCE",
    "shardSize": "SHARD_SIZE_SMALL",
    "algorithm_config": {
      "treeAhConfig": {
        "leafNodeEmbeddingCount": 500,
        "leafNodesToSearchPercent": 10
      }
    }
  }
}
EOF

# Create index (async — returns operation name)
# Using --index-update-method=STREAM_UPDATE for real-time upserts
INDEX_OP=$(gcloud ai indexes create \
  --display-name="${VS_INDEX_DISPLAY_NAME}" \
  --metadata-schema-uri="gs://google-cloud-aiplatform/schema/matchingengine/metadata/nearest_neighbor_search_1.0.0.yaml" \
  --metadata-file="${METADATA_FILE}" \
  --index-update-method=STREAM_UPDATE \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(name)" 2>&1 | tail -1)

# Clean up temp file
rm -f "${METADATA_FILE}"

echo "Index operation: ${INDEX_OP}"
echo "Waiting for index creation (this can take 20-40 min)…"
gcloud ai operations wait "${INDEX_OP}" --region="${REGION}" --project="${PROJECT_ID}" 2>/dev/null || true

# Get the index ID
INDEX_ID=$(gcloud ai indexes list \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --filter="displayName=${VS_INDEX_DISPLAY_NAME}" \
  --format="value(name)" | head -1 | awk -F'/' '{print $NF}')

echo "Index ID: ${INDEX_ID}"

echo ""
echo "═══ Creating Vector Search public endpoint ═══"
gcloud ai index-endpoints create \
  --display-name="${VS_ENDPOINT_DISPLAY_NAME}" \
  --public-endpoint-enabled \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet

ENDPOINT_ID=$(gcloud ai index-endpoints list \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --filter="displayName=${VS_ENDPOINT_DISPLAY_NAME}" \
  --format="value(name)" | head -1 | awk -F'/' '{print $NF}')

echo "Endpoint ID: ${ENDPOINT_ID}"

echo ""
echo "═══ Deploying index to endpoint ═══"
gcloud ai index-endpoints deploy-index "${ENDPOINT_ID}" \
  --deployed-index-id="${VS_DEPLOYED_INDEX_ID}" \
  --index="${INDEX_ID}" \
  --display-name="${VS_INDEX_DISPLAY_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet

echo ""
echo "════════════════════════════════════════════════"
echo "✓ Vector Search ready"
echo ""
echo "  INDEX_ID            = ${INDEX_ID}"
echo "  ENDPOINT_ID         = ${ENDPOINT_ID}"
echo "  DEPLOYED_INDEX_ID   = ${VS_DEPLOYED_INDEX_ID}"
echo ""
echo "Set these as env vars for Cloud Run Jobs:"
echo "  VECTOR_SEARCH_INDEX_ID=${INDEX_ID}"
echo "  VECTOR_SEARCH_ENDPOINT_ID=${ENDPOINT_ID}"
echo "  VECTOR_SEARCH_DEPLOYED_INDEX_ID=${VS_DEPLOYED_INDEX_ID}"
echo "════════════════════════════════════════════════"
echo ""
echo "Next → run 04_create_vertex_search.sh"
