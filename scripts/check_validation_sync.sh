#!/usr/bin/env bash
# Pre-commit hook: verify frontend/backend username validation patterns stay in sync.
#
# Install:
#   cp scripts/check_validation_sync.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Or add to an existing pre-commit hook:
#   scripts/check_validation_sync.sh || exit 1

set -euo pipefail

BACKEND_FILE="src/web/utils/validation.py"
FRONTEND_FILE="frontend/src/pages/Login.vue"

# Extract the backend pattern (Python: TELEGRAM_USERNAME_PATTERN = r"...")
BACKEND_PATTERN=$(sed -n 's/.*TELEGRAM_USERNAME_PATTERN *= *r"\([^"]*\)".*/\1/p' "$BACKEND_FILE")

# Extract the frontend pattern (JS: TELEGRAM_USERNAME_RE = /.../)
FRONTEND_PATTERN=$(sed -n 's/.*TELEGRAM_USERNAME_RE *= *\/\([^/]*\)\/.*/\1/p' "$FRONTEND_FILE")

if [ -z "$BACKEND_PATTERN" ]; then
    echo "ERROR: Could not extract TELEGRAM_USERNAME_PATTERN from $BACKEND_FILE"
    exit 1
fi

if [ -z "$FRONTEND_PATTERN" ]; then
    echo "ERROR: Could not extract TELEGRAM_USERNAME_RE from $FRONTEND_FILE"
    exit 1
fi

if [ "$BACKEND_PATTERN" != "$FRONTEND_PATTERN" ]; then
    echo "ERROR: Username validation patterns are out of sync!"
    echo "  Backend ($BACKEND_FILE): $BACKEND_PATTERN"
    echo "  Frontend ($FRONTEND_FILE): $FRONTEND_PATTERN"
    echo ""
    echo "  Update both patterns to match, then re-commit."
    exit 1
fi

echo "OK: Username validation patterns are in sync."
