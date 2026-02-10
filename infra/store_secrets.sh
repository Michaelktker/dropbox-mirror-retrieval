#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Store Dropbox credentials in Secret Manager.
#
# USAGE:
#   ./store_secrets.sh <APP_KEY> <APP_SECRET> <REFRESH_TOKEN>
# ─────────────────────────────────────────────────────────────
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <DROPBOX_APP_KEY> <DROPBOX_APP_SECRET> <DROPBOX_REFRESH_TOKEN>"
  exit 1
fi

APP_KEY="$1"
APP_SECRET="$2"
REFRESH_TOKEN="$3"

create_or_update_secret() {
  local name="$1"
  local value="$2"

  if gcloud secrets describe "${name}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "${value}" | gcloud secrets versions add "${name}" \
      --data-file=- --project="${PROJECT_ID}" --quiet
    echo "  Updated secret: ${name}"
  else
    echo "${value}" | gcloud secrets create "${name}" \
      --data-file=- --project="${PROJECT_ID}" \
      --replication-policy=automatic --quiet
    echo "  Created secret: ${name}"
  fi
}

echo "═══ Storing Dropbox secrets ═══"
create_or_update_secret "${SECRET_DROPBOX_APP_KEY}" "${APP_KEY}"
create_or_update_secret "${SECRET_DROPBOX_APP_SECRET}" "${APP_SECRET}"
create_or_update_secret "${SECRET_DROPBOX_REFRESH_TOKEN}" "${REFRESH_TOKEN}"

echo ""
echo "✓ Secrets stored in Secret Manager"
