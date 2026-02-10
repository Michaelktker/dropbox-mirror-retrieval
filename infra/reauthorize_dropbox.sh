#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Re-authorize Dropbox app and update refresh token in Secret Manager
# Run this AFTER updating permissions in Dropbox developer console
# ─────────────────────────────────────────────────────────────

set -euo pipefail

APP_KEY="oyvml1upnprceii"
APP_SECRET="k0xozrgmva84f35"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Dropbox Re-Authorization"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "STEP 1: Open this URL in your browser:"
echo ""
echo "  https://www.dropbox.com/oauth2/authorize?client_id=${APP_KEY}&response_type=code&token_access_type=offline&scope=account_info.read%20files.metadata.read%20files.content.read"
echo ""
echo "STEP 2: Authorize the app and copy the authorization code"
echo ""
read -p "Paste the authorization code here: " AUTH_CODE
echo ""

echo "Exchanging code for refresh token..."
RESPONSE=$(curl -s -X POST https://api.dropboxapi.com/oauth2/token \
  -d code="${AUTH_CODE}" \
  -d grant_type=authorization_code \
  -d client_id="${APP_KEY}" \
  -d client_secret="${APP_SECRET}")

# Extract refresh token from JSON response
REFRESH_TOKEN=$(echo "$RESPONSE" | grep -oP '"refresh_token":\s*"\K[^"]+')

if [ -z "$REFRESH_TOKEN" ]; then
  echo "❌ ERROR: Failed to get refresh token"
  echo "Response: $RESPONSE"
  exit 1
fi

echo "✅ Got new refresh token: ${REFRESH_TOKEN:0:20}..."
echo ""
echo "Updating Secret Manager..."

# Update the secret in GCP
echo -n "$REFRESH_TOKEN" | gcloud secrets versions add DROPBOX_REFRESH_TOKEN --data-file=-

echo ""
echo "✅ Secret updated successfully!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  bash infra/test_sync.sh         # Run baseline sync test"
echo ""
