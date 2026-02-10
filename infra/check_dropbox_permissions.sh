#!/usr/bin/env bash
# Quick diagnostic script to check Dropbox permissions issue

set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Dropbox Permission Diagnostic"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get current refresh token
echo "1. Checking current refresh token..."
REFRESH_TOKEN=$(gcloud secrets versions access latest --secret=DROPBOX_REFRESH_TOKEN 2>/dev/null || echo "")

if [ -z "$REFRESH_TOKEN" ]; then
  echo "   ❌ No refresh token found in Secret Manager"
  exit 1
fi

echo "   ✅ Refresh token exists: ${REFRESH_TOKEN:0:20}..."
echo ""

set +e  # Disable exit on error for API calls

# Exchange for access token
echo "2. Testing token exchange..."
APP_KEY=$(gcloud secrets versions access latest --secret=DROPBOX_APP_KEY)
APP_SECRET=$(gcloud secrets versions access latest --secret=DROPBOX_APP_SECRET)

ACCESS_RESPONSE=$(curl -s -X POST https://api.dropboxapi.com/oauth2/token \
  -d grant_type=refresh_token \
  -d refresh_token="$REFRESH_TOKEN" \
  -d client_id="$APP_KEY" \
  -d client_secret="$APP_SECRET")

# Check if response contains an error
if echo "$ACCESS_RESPONSE" | grep -q '"error"'; then
  echo "   ❌ Token exchange failed"
  echo "   Error: $(echo "$ACCESS_RESPONSE" | grep -oP '"error_description":\s*"\K[^"]+' || echo "Unknown error")"
  echo ""
  echo "   Full response:"
  echo "   $ACCESS_RESPONSE"
  echo ""
  echo "   This usually means the refresh token is invalid or expired."
  echo "   Run: bash infra/reauthorize_dropbox.sh"
  echo ""
  exit 1
fi

ACCESS_TOKEN=$(echo "$ACCESS_RESPONSE" | grep -oP '"access_token":\s*"\K[^"]+' || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
  echo "   ❌ Failed to extract access token"
  echo "   Response: $ACCESS_RESPONSE"
  exit 1
fi

echo "   ✅ Got access token: ${ACCESS_TOKEN:0:20}..."
echo ""

# Test file listing
echo "3. Testing file list permission..."
LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST https://api.dropboxapi.com/2/files/list_folder \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"path":"","limit":1}')

HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
BODY=$(echo "$LIST_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  echo "   ❌ FAILED (HTTP $HTTP_CODE)"
  echo ""
  echo "   Response: $BODY"
  echo ""
  if echo "$BODY" | grep -qi "scope"; then
    echo "   The token is MISSING required scopes."
    echo "   Your refresh token only has 'account_info.read' scope."
    echo ""
    echo "   TO FIX — re-authorize with explicit scopes:"
    echo "   1. Make sure permissions are enabled AND submitted at:"
    echo "      https://www.dropbox.com/developers/apps/info/oyvml1upnprceii"
    echo "   2. Run: bash infra/reauthorize_dropbox.sh"
  fi
  echo ""
  exit 1
else
  echo "   ✅ File listing works!"
  if echo "$BODY" | grep -q '"entries"'; then
    echo "   Found entries in Dropbox"
  fi
  echo ""
  echo "   Permissions are correct! You can proceed with testing."
  echo ""
  echo "   Next steps:"
  echo "     bash infra/test_sync.sh              # Test baseline sync"
  echo "     bash infra/run_all_tests.sh          # Run all tests"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
