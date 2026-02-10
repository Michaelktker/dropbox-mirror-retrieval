#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Combined retrieval: query BOTH Vector Search (images) and
# Vertex AI Search (docs), output merged JSON.
#
# USAGE:
#   ./combine_results.sh "team meeting presentation"
# ─────────────────────────────────────────────────────────────
set -euo pipefail

QUERY_TEXT="${1:?Usage: $0 \"your search query\"}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Config ────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
ENDPOINT_ID="${VECTOR_SEARCH_ENDPOINT_ID:?Set VECTOR_SEARCH_ENDPOINT_ID}"
DEPLOYED_INDEX_ID="${VECTOR_SEARCH_DEPLOYED_INDEX_ID:?Set VECTOR_SEARCH_DEPLOYED_INDEX_ID}"
DATASTORE_ID="${VERTEX_SEARCH_DATASTORE_ID:?Set VERTEX_SEARCH_DATASTORE_ID}"
NUM_NEIGHBORS="${NUM_NEIGHBORS:-5}"
PAGE_SIZE="${PAGE_SIZE:-5}"

TOKEN=$(gcloud auth print-access-token)

echo "► Combined retrieval for: \"${QUERY_TEXT}\""
echo ""

# ── 1. Get text embedding ────────────────────────────────
EMBED_RESPONSE=$(curl -s -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/multimodalembedding@001:predict" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"instances": [{"text": "'"${QUERY_TEXT}"'"}]}')

EMBEDDING=$(echo "${EMBED_RESPONSE}" | python3 -c "
import sys, json
resp = json.load(sys.stdin)
print(json.dumps(resp['predictions'][0]['textEmbedding']))
")

# ── 2. Vector Search (images) ────────────────────────────
ENDPOINT_DOMAIN=$(gcloud ai index-endpoints describe "${ENDPOINT_ID}" \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --format="value(publicEndpointDomainName)" 2>/dev/null)

VS_RESPONSE=$(curl -s -X POST \
  "https://${ENDPOINT_DOMAIN}/v1/projects/${PROJECT_ID}/locations/${REGION}/indexEndpoints/${ENDPOINT_ID}:findNeighbors" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "deployed_index_id": "'"${DEPLOYED_INDEX_ID}"'",
    "queries": [{"datapoint": {"feature_vector": '"${EMBEDDING}"'}, "neighbor_count": '"${NUM_NEIGHBORS}"'}]
  }')

# ── 3. Vertex AI Search (docs) ───────────────────────────
SERVING_CONFIG="projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores/${DATASTORE_ID}/servingConfigs/default_search"

DOC_RESPONSE=$(curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1/${SERVING_CONFIG}:search" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query": "'"${QUERY_TEXT}"'", "pageSize": '"${PAGE_SIZE}"', "contentSearchSpec": {"snippetSpec": {"returnSnippet": true}}}')

# ── 4. Combine into single JSON ──────────────────────────
python3 -c "
import json, sys

query = '''${QUERY_TEXT}'''

# Parse Vector Search response
vs = json.loads('''${VS_RESPONSE}''')
neighbors = vs.get('nearestNeighbors', [{}])[0].get('neighbors', [])
image_matches = []
for n in neighbors:
    dp = n.get('datapoint', {})
    image_matches.append({
        'file_id': dp.get('datapointId', ''),
        'distance': n.get('distance', 0),
    })

# Parse Vertex AI Search response
doc = json.loads('''${DOC_RESPONSE}''')
results = doc.get('results', [])
doc_matches = []
for r in results:
    d = r.get('document', {})
    derived = d.get('derivedStructData', {})
    snippets = derived.get('snippets', [])
    doc_matches.append({
        'document_id': d.get('id', ''),
        'title': derived.get('title', ''),
        'link': derived.get('link', ''),
        'snippet': snippets[0].get('snippet', '') if snippets else '',
    })

output = {
    'query': query,
    'image_matches': image_matches,
    'document_matches': doc_matches,
}

print(json.dumps(output, indent=2))
"
