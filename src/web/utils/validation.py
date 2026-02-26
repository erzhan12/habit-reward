"""Shared validation constants for the web layer.

These constants are the canonical source of truth for validation rules.
The frontend (frontend/src/pages/Login.vue) maintains its own copy of
TELEGRAM_USERNAME_PATTERN — keep both in sync when updating.
"""

# Telegram usernames: 3-32 alphanumeric characters or underscores.
TELEGRAM_USERNAME_PATTERN = r"^[a-zA-Z0-9_]{3,32}$"
