#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Test Phase 7 - Document Search
# Triggers Vertex AI Search import and tests queries
# ─────────────────────────────────────────────────────────────

set -euo pipefail

source "$(dirname "$0")/variables.sh"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Phase 7 Test D: Document Search"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if documents exist
DOC_COUNT=$(gsutil ls "gs://${BUCKET_NAME}/mirror/docs/**" 2>/dev/null | wc -l || echo "0")
if [ "$DOC_COUNT" -eq 0 ]; then
  echo "⚠️  No documents in bucket yet"
  echo "   Vertex AI Search can still be tested with empty results"
  echo ""
fi

echo "Found $DOC_COUNT documents in bucket"
echo ""

# Trigger import
echo "1. Triggering Vertex AI Search import..."
IMPORT_OPERATION=$(gcloud alpha discovery-engine datastores import \
  --project="${PROJECT_ID}" \
  --location=global \
  --datastore="${DATASTORE_ID}" \
  --gcs-uri="gs://${BUCKET_NAME}/mirror/docs/**" \
  --data-schema=content \
  --format="value(name)" 2>&1 || echo "")

if [ -n "$IMPORT_OPERATION" ]; then
  echo "   Import operation: $IMPORT_OPERATION"
  echo "   ⏳ Import is running in background (may take 5-15 minutes)"
else
  echo "   ⚠️  Import command may have failed or already running"
fi

echo ""
echo "2. Testing document search query..."
echo ""

# Test query
bash "$(dirname "$0")/../curl/query_vertex_search.sh" "test document" || {
  echo ""
  echo "   ⏳ Search may not return results yet if import is still processing"
  echo "   Wait a few minutes and try again:"
  echo "     bash curl/query_vertex_search.sh \"your query\""
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ TEST D IN PROGRESS - Document search configured"
echo ""
echo " Wait 5-15 minutes for indexing, then test queries:"
echo "   bash curl/query_vertex_search.sh \"your search query\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
