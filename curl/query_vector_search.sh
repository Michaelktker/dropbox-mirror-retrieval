#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Query Vector Search for images via cURL.
#
# USAGE:
#   ./query_vector_search.sh "a sunset over the ocean"
#
# Steps:
#   1. Embed the text query via multimodalembedding@001
#   2. Find nearest neighbors in Vector Search
# ─────────────────────────────────────────────────────────────
set -euo pipefail

QUERY_TEXT="${1:?Usage: $0 \"your search query\"}"

# ── Config (override via env vars) ────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
ENDPOINT_ID="${VECTOR_SEARCH_ENDPOINT_ID:?Set VECTOR_SEARCH_ENDPOINT_ID}"
DEPLOYED_INDEX_ID="${VECTOR_SEARCH_DEPLOYED_INDEX_ID:?Set VECTOR_SEARCH_DEPLOYED_INDEX_ID}"
NUM_NEIGHBORS="${NUM_NEIGHBORS:-10}"

TOKEN=$(gcloud auth print-access-token)

# ── Step 1: Get text embedding ────────────────────────────
echo "► Embedding query: \"${QUERY_TEXT}\""

EMBED_RESPONSE=$(curl -s -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/multimodalembedding@001:predict" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [
      {
        "text": "'"${QUERY_TEXT}"'"
      }
    ]
  }')

# Extract the embedding vector
EMBEDDING=$(echo "${EMBED_RESPONSE}" | python3 -c "
import sys, json
resp = json.load(sys.stdin)
vec = resp['predictions'][0]['textEmbedding']
print(json.dumps(vec))
")

echo "  ✓ Embedding obtained (dim=$(echo "${EMBEDDING}" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"))"

# ── Step 2: Find nearest neighbors ───────────────────────
echo "► Querying Vector Search (top ${NUM_NEIGHBORS})…"

# Get the public endpoint domain
ENDPOINT_INFO=$(gcloud ai index-endpoints describe "${ENDPOINT_ID}" \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --format="value(publicEndpointDomainName)" 2>/dev/null)

SEARCH_RESPONSE=$(curl -s -X POST \
  "https://${ENDPOINT_INFO}/v1/projects/${PROJECT_ID}/locations/${REGION}/indexEndpoints/${ENDPOINT_ID}:findNeighbors" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "deployed_index_id": "'"${DEPLOYED_INDEX_ID}"'",
    "queries": [
      {
        "datapoint": {
          "feature_vector": '"${EMBEDDING}"'
        },
        "neighbor_count": '"${NUM_NEIGHBORS}"'
      }
    ]
  }')

echo ""
echo "═══ IMAGE MATCHES ═══"
echo "${SEARCH_RESPONSE}" | python3 -c "
import sys, json
resp = json.load(sys.stdin)
neighbors = resp.get('nearestNeighbors', [{}])[0].get('neighbors', [])
if not neighbors:
    print('  (no results)')
else:
    for n in neighbors:
        dp = n.get('datapoint', {})
        print(f'  id={dp.get(\"datapointId\",\"?\")}  distance={n.get(\"distance\",\"?\"):.4f}')
"
