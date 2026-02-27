"""Shared validation constants for the web layer.

These constants are the canonical source of truth for validation rules.
The frontend (frontend/src/pages/Login.vue) maintains its own copy of
TELEGRAM_USERNAME_PATTERN — keep both in sync when updating.

Verify sync with:
    grep 'TELEGRAM_USERNAME_RE' frontend/src/pages/Login.vue
    grep 'TELEGRAM_USERNAME_PATTERN' src/web/utils/validation.py

Consider adding a pre-commit hook that compares both patterns automatically.
"""

# Telegram usernames: 3-32 lowercase alphanumeric characters or underscores.
# Lowercase only — User.save() normalizes to lowercase, and the DB-level
# CheckConstraint enforces ^[a-z0-9_]{3,32}$.  Accepting uppercase here would
# let the frontend accept "UserName" which is silently stored as "username",
# creating a confusing mismatch.
TELEGRAM_USERNAME_PATTERN = r"^[a-z0-9_]{3,32}$"
