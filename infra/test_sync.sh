#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Test Phase 7 - Baseline Sync
# Runs the sync job and verifies GCS bucket content
# ─────────────────────────────────────────────────────────────

set -euo pipefail

source "$(dirname "$0")/variables.sh"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Phase 7 Test A: Baseline Sync"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Execute the sync job
echo "1. Starting sync job..."
EXECUTION=$(gcloud run jobs execute sync-dropbox-to-gcs \
  --region="${REGION}" \
  --format="value(metadata.name)" 2>&1)

EXECUTION_ID=$(echo "$EXECUTION" | grep "sync-dropbox-to-gcs" | tail -n1)

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
echo "3. Checking GCS bucket content..."
echo ""

# Check for images
IMAGE_COUNT=$(gsutil ls "gs://${BUCKET_NAME}/mirror/images/**" 2>/dev/null | wc -l || echo "0")
echo "   Images: $IMAGE_COUNT files"

# Check for documents
DOC_COUNT=$(gsutil ls "gs://${BUCKET_NAME}/mirror/docs/**" 2>/dev/null | wc -l || echo "0")
echo "   Documents: $DOC_COUNT files"

# Check for media
MEDIA_COUNT=$(gsutil ls "gs://${BUCKET_NAME}/mirror/media/**" 2>/dev/null | wc -l || echo "0")
echo "   Media: $MEDIA_COUNT files"

# Check for metadata
META_COUNT=$(gsutil ls "gs://${BUCKET_NAME}/mirror/meta/**" 2>/dev/null | wc -l || echo "0")
echo "   Metadata files: $META_COUNT files"

# Check state files
echo ""
echo "4. Checking state files..."

if gsutil ls "gs://${BUCKET_NAME}/mirror/state/sync_state.json" &>/dev/null; then
  echo "   ✅ sync_state.json exists"
  echo "   Cursor:"
  gsutil cat "gs://${BUCKET_NAME}/mirror/state/sync_state.json" | grep -o '"cursor":"[^"]*"' | head -c 80
  echo "..."
else
  echo "   ❌ sync_state.json missing"
fi

if gsutil ls "gs://${BUCKET_NAME}/mirror/state/path_index.json" &>/dev/null; then
  echo "   ✅ path_index.json exists"
  PATHS=$(gsutil cat "gs://${BUCKET_NAME}/mirror/state/path_index.json" | grep -o '"[^"]*":' | wc -l)
  echo "   Paths indexed: $PATHS"
else
  echo "   ❌ path_index.json missing"
fi

echo ""
echo "5. Sample files in bucket:"
gsutil ls "gs://${BUCKET_NAME}/mirror/**" | head -n 20

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$IMAGE_COUNT" -gt 0 ] || [ "$DOC_COUNT" -gt 0 ]; then
  echo " ✅ TEST A PASSED - Files synced successfully"
  echo ""
  echo " Next steps:"
  echo "   bash infra/test_embeddings.sh   # Test C: Image embeddings"
  echo "   bash infra/test_doc_search.sh   # Test D: Document search"
else
  echo " ⚠️  WARNING: No files found in bucket"
  echo ""
  echo " Check job logs:"
  echo "   gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=sync-dropbox-to-gcs\" --limit=50 --format=json"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
