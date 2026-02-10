#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# 02 — Create GCS bucket
# ─────────────────────────────────────────────────────────────
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

echo "═══ Creating bucket gs://${BUCKET_NAME} ═══"
if ! gsutil ls -b "gs://${BUCKET_NAME}" &>/dev/null; then
  gsutil mb -l "${REGION}" "gs://${BUCKET_NAME}"
else
  echo "Bucket already exists"
fi

echo ""
echo "✓ Bucket: gs://${BUCKET_NAME}"
echo ""
echo "Logical prefixes (created on first write):"
echo "  mirror/images/"
echo "  mirror/docs/"
echo "  mirror/media/"
echo "  mirror/meta/"
echo "  mirror/state/"
echo ""
echo "Next → run 03_create_vector_search.sh"
