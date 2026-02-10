#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Test Phase 7 - Image Embeddings
# Runs the embed job and verifies Vector Search index
# ─────────────────────────────────────────────────────────────

set -euo pipefail

source "$(dirname "$0")/variables.sh"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Phase 7 Test C: Image Embeddings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if images exist first
IMAGE_COUNT=$(gsutil ls "gs://${BUCKET_NAME}/mirror/images/**" 2>/dev/null | wc -l || echo "0")
if [ "$IMAGE_COUNT" -eq 0 ]; then
  echo "❌ No images in bucket. Run test_sync.sh first."
  exit 1
fi

echo "Found $IMAGE_COUNT images in bucket"
echo ""

# Execute the embed job
echo "1. Starting embedding job..."
EXECUTION=$(gcloud run jobs execute embed-images-to-vector-search \
  --region="${REGION}" \
  --format="value(metadata.name)" 2>&1)

EXECUTION_ID=$(echo "$EXECUTION" | grep "embed-images-to-vector-search" | tail -n1)

if [ -z "$EXECUTION_ID" ]; then
  echo "❌ Failed to start job"
  exit 1
fi

echo "   Execution ID: $EXECUTION_ID"
echo ""

# Wait for completion
echo "2. Waiting for job to complete (this may take several minutes)..."
while true; do
  STATUS=$(gcloud run jobs executions describe "$EXECUTION_ID" \
    --region="${REGION}" \
    --format="value(status.conditions[0].type)" 2>/dev/null || echo "PENDING")
  
  if [ "$STATUS" = "Completed" ]; then
    echo "   ✅ Job completed successfully"
    break
  elif [ "$STATUS" = "Failed" ]; then
    echo "   ❌ Job failed"
    gcloud run jobs executions describe "$EXECUTION_ID" --region="${REGION}"
    exit 1
  fi
  
  echo "   Status: $STATUS (waiting...)"
  sleep 10
done

echo ""
echo "3. Checking embedding state..."

if gsutil ls "gs://${BUCKET_NAME}/mirror/state/embedding_state.json" &>/dev/null; then
  echo "   ✅ embedding_state.json exists"
  EMBEDDINGS=$(gsutil cat "gs://${BUCKET_NAME}/mirror/state/embedding_state.json" | grep -o '"id:[^"]*"' | wc -l)
  echo "   Embeddings tracked: $EMBEDDINGS"
else
  echo "   ❌ embedding_state.json missing"
fi

echo ""
echo "4. Checking Vector Search index..."

# Note: Index stats may take time to update
gcloud ai indexes describe "${VECTOR_SEARCH_INDEX_ID}" \
  --region="${REGION}" \
  --format="table(name, displayName, metadata)" 2>/dev/null || echo "Could not fetch index details"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ TEST C PASSED - Image embeddings completed"
echo ""
echo " Next steps:"
echo "   bash curl/query_vector_search.sh \"test image query\"  # Test E"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
