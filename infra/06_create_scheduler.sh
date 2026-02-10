#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# 06 — Create Cloud Scheduler triggers for daily runs
# ─────────────────────────────────────────────────────────────
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

# Cloud Run Jobs API endpoint
RUN_API="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs"

echo "═══ Creating scheduler: ${SCHEDULER_SYNC} (daily 02:00 UTC) ═══"
gcloud scheduler jobs create http "${SCHEDULER_SYNC}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --schedule="0 2 * * *" \
  --time-zone="UTC" \
  --uri="${RUN_API}/${JOB_SYNC}:run" \
  --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}" \
  --quiet || \
gcloud scheduler jobs update http "${SCHEDULER_SYNC}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --schedule="0 2 * * *" \
  --quiet

echo ""
echo "═══ Creating scheduler: ${SCHEDULER_EMBED} (daily 04:00 UTC) ═══"
gcloud scheduler jobs create http "${SCHEDULER_EMBED}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --schedule="0 4 * * *" \
  --time-zone="UTC" \
  --uri="${RUN_API}/${JOB_EMBED}:run" \
  --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}" \
  --quiet || \
gcloud scheduler jobs update http "${SCHEDULER_EMBED}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --schedule="0 4 * * *" \
  --quiet

echo ""
echo "═══ Creating scheduler: ${SCHEDULER_REIMPORT} (daily 05:00 UTC) ═══"
# Re-import docs into Vertex AI Search datastore
REIMPORT_URI="https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores/${DATASTORE_ID}/branches/default_branch/documents:import"

gcloud scheduler jobs create http "${SCHEDULER_REIMPORT}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --schedule="0 5 * * *" \
  --time-zone="UTC" \
  --uri="${REIMPORT_URI}" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"gcsSource":{"inputUris":["gs://'"${BUCKET_NAME}"'/mirror/docs/**"]},"reconciliationMode":"INCREMENTAL"}' \
  --oauth-service-account-email="${SA_EMAIL}" \
  --quiet || \
gcloud scheduler jobs update http "${SCHEDULER_REIMPORT}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --schedule="0 5 * * *" \
  --quiet

echo ""
echo "✓ Schedulers created"
echo "  ${SCHEDULER_SYNC}      → 02:00 UTC daily"
echo "  ${SCHEDULER_EMBED}     → 04:00 UTC daily"
echo "  ${SCHEDULER_REIMPORT}  → 05:00 UTC daily"
echo ""
echo "Manual trigger:"
echo "  gcloud scheduler jobs run ${SCHEDULER_SYNC} --location=${REGION}"
