#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Set environment variables for testing
# Source this file before running curl scripts
#
# USAGE:
#   source infra/set_test_env.sh
# ─────────────────────────────────────────────────────────────

# Load infrastructure variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

# Export for curl scripts
export GCP_PROJECT_ID="${PROJECT_ID}"
export GCP_REGION="${REGION}"

# Vector Search IDs
export VECTOR_SEARCH_INDEX_ID="8915836435542573056"
export VECTOR_SEARCH_ENDPOINT_ID="7079528871854342144"
export VECTOR_SEARCH_DEPLOYED_INDEX_ID="deployed_dropbox_images"

# Vertex AI Search IDs
export VERTEX_SEARCH_DATASTORE_ID="dropbox-docs-datastore"
export VERTEX_SEARCH_ENGINE_ID="dropbox-docs-engine"

# Display config
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Environment configured for testing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  GCP_PROJECT_ID:                   ${GCP_PROJECT_ID}"
echo "  GCP_REGION:                       ${GCP_REGION}"
echo "  VECTOR_SEARCH_INDEX_ID:           ${VECTOR_SEARCH_INDEX_ID}"
echo "  VECTOR_SEARCH_ENDPOINT_ID:        ${VECTOR_SEARCH_ENDPOINT_ID}"
echo "  VERTEX_SEARCH_DATASTORE_ID:       ${VERTEX_SEARCH_DATASTORE_ID}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "You can now run curl scripts:"
echo "  bash curl/query_vector_search.sh \"test query\""
echo "  bash curl/query_vertex_search.sh \"test query\""
echo "  bash curl/combine_results.sh \"test query\""
echo ""
