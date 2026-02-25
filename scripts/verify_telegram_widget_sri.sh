#!/usr/bin/env bash
# Verify or print the SRI (Subresource Integrity) hash for the Telegram Login Widget script.
# Used in CI to fail when Telegram updates the widget and frontend/src/pages/Login.vue is stale.
#
# Usage:
#   ./scripts/verify_telegram_widget_sri.sh          # Verify: exit 0 if match, 1 if not
#   ./scripts/verify_telegram_widget_sri.sh --print  # Print current hash for manual update

set -e

WIDGET_URL="https://telegram.org/js/telegram-widget.js?22"
LOGIN_VUE="frontend/src/pages/Login.vue"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT"

if ! command -v curl &>/dev/null || ! command -v openssl &>/dev/null; then
  echo "Error: curl and openssl are required." >&2
  exit 2
fi

CURRENT_HASH_B64=$(curl -sL "$WIDGET_URL" | openssl dgst -sha384 -binary | openssl base64 -A)
CURRENT_SRI="sha384-$CURRENT_HASH_B64"

if [[ "${1:-}" == "--print" ]]; then
  echo "$CURRENT_SRI"
  exit 0
fi

# Verify: extract stored hash from Login.vue (script.integrity = "..." or WIDGET_SRI = "...")
if [[ ! -f "$LOGIN_VUE" ]]; then
  echo "Error: $LOGIN_VUE not found." >&2
  exit 2
fi

STORED_SRI=$(grep -E '(script\.integrity\s*=\s*"sha384-|WIDGET_SRI\s*=\s*"sha384-)' "$LOGIN_VUE" | grep -oE 'sha384-[A-Za-z0-9+/=_-]+' | head -1)
if [[ -z "$STORED_SRI" ]]; then
  echo "Error: Could not find script.integrity in $LOGIN_VUE" >&2
  exit 2
fi

if [[ "$STORED_SRI" == "$CURRENT_SRI" ]]; then
  echo "SRI OK: Telegram widget hash matches $LOGIN_VUE"
  exit 0
fi

echo "SRI mismatch: Telegram widget hash changed." >&2
echo "  Stored (in $LOGIN_VUE): $STORED_SRI" >&2
echo "  Current (from $WIDGET_URL): $CURRENT_SRI" >&2
echo "  Update the integrity attribute in $LOGIN_VUE and re-run this script to verify." >&2
echo "  Or run: ./scripts/verify_telegram_widget_sri.sh --print" >&2
exit 1
