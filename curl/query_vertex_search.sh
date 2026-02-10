#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Query Vertex AI Search for documents via cURL.
#
# USAGE:
#   ./query_vertex_search.sh "quarterly revenue report"
# ─────────────────────────────────────────────────────────────
set -euo pipefail

QUERY_TEXT="${1:?Usage: $0 \"your search query\"}"

# ── Config ────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
DATASTORE_ID="${VERTEX_SEARCH_DATASTORE_ID:?Set VERTEX_SEARCH_DATASTORE_ID}"
PAGE_SIZE="${PAGE_SIZE:-10}"

TOKEN=$(gcloud auth print-access-token)

SERVING_CONFIG="projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores/${DATASTORE_ID}/servingConfigs/default_search"

echo "► Searching docs for: \"${QUERY_TEXT}\""

SEARCH_RESPONSE=$(curl -s -X POST \
  "https://discoveryengine.googleapis.com/v1/${SERVING_CONFIG}:search" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "'"${QUERY_TEXT}"'",
    "pageSize": '"${PAGE_SIZE}"',
    "contentSearchSpec": {
      "snippetSpec": {
        "returnSnippet": true
      }
    }
  }')

echo ""
echo "═══ DOCUMENT MATCHES ═══"
echo "${SEARCH_RESPONSE}" | python3 -c "
import sys, json
resp = json.load(sys.stdin)
results = resp.get('results', [])
if not results:
    print('  (no results)')
else:
    for i, r in enumerate(results, 1):
        doc = r.get('document', {})
        doc_id = doc.get('id', '?')
        derived = doc.get('derivedStructData', {})
        link = derived.get('link', '')
        title = derived.get('title', doc_id)
        snippets = derived.get('snippets', [])
        snippet_text = snippets[0].get('snippet', '') if snippets else ''
        print(f'  {i}. {title}')
        print(f'     id:      {doc_id}')
        if link:
            print(f'     link:    {link}')
        if snippet_text:
            print(f'     snippet: {snippet_text[:120]}')
        print()
total = resp.get('totalSize', 0)
print(f'  Total: {total} document(s)')
"
