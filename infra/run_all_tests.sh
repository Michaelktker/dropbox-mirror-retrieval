#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Run all Phase 7 tests in sequence
# Use this after fixing Dropbox permissions
# ─────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " PHASE 7: COMPREHENSIVE TESTING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will run all tests in sequence. Press Ctrl+C to abort."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  exit 0
fi

# Test A: Baseline Sync
echo ""
echo "═════════════════════════════════════════════════════════════"
echo " TEST A: Baseline Sync"
echo "═════════════════════════════════════════════════════════════"
bash "${SCRIPT_DIR}/test_sync.sh" || {
  echo "❌ Test A failed. Fix issues before continuing."
  exit 1
}

# Test C: Image Embeddings
echo ""
echo "═════════════════════════════════════════════════════════════"
echo " TEST C: Image Embeddings"
echo "═════════════════════════════════════════════════════════════"
bash "${SCRIPT_DIR}/test_embeddings.sh" || {
  echo "❌ Test C failed. Check logs and continue manually if needed."
}

# Test D: Document Search
echo ""
echo "═════════════════════════════════════════════════════════════"
echo " TEST D: Document Search"
echo "═════════════════════════════════════════════════════════════"
bash "${SCRIPT_DIR}/test_doc_search.sh" || {
  echo "⚠️  Test D needs time to complete. Try queries later."
}

# Test E: Image Search
echo ""
echo "═════════════════════════════════════════════════════════════"
echo " TEST E: Image Search (Vector Search)"
echo "═════════════════════════════════════════════════════════════"
bash "${SCRIPT_DIR}/../curl/query_vector_search.sh" "photo of nature" || {
  echo "⚠️  Vector search query failed. Index may need time to update."
}

# Test F: Combined Retrieval
echo ""
echo "═════════════════════════════════════════════════════════════"
echo " TEST F: Combined Retrieval"
echo "═════════════════════════════════════════════════════════════"
bash "${SCRIPT_DIR}/../curl/combine_results.sh" "meeting presentation" || {
  echo "⚠️  Combined query failed. Check individual search endpoints."
}

# Test G: Scheduler
echo ""
echo "═════════════════════════════════════════════════════════════"
echo " TEST G: Scheduler Trigger"
echo "═════════════════════════════════════════════════════════════"
echo "Manually triggering daily-dropbox-sync scheduler..."
gcloud scheduler jobs run daily-dropbox-sync --location=us-central1 || {
  echo "⚠️  Scheduler trigger failed. Check scheduler configuration."
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " TESTING SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo " ✅ Automated tests completed"
echo ""
echo " Manual verification needed:"
echo "  • Test B: Incremental sync (modify Dropbox files, re-run sync)"
echo "  • Verify Vector Search index populated"
echo "  • Verify Document Search returns relevant results"
echo "  • Verify schedulers run daily at configured times"
echo ""
echo " If all looks good, update IMPLEMENTATION_PLAN.md Phase 7"
echo " and mark Phase 8 complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
