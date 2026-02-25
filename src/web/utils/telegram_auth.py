"""Telegram Login Widget hash verification."""

import hashlib
import hmac
import time

from django.conf import settings


REQUIRED_FIELDS = {"id", "auth_date", "hash"}
OPTIONAL_FIELDS = {"first_name", "last_name", "username", "photo_url"}
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


def verify_telegram_auth(
    data: dict[str, str],
    bot_token: str,
    max_age_seconds: int | None = None,
) -> bool:
    """Verify Telegram Login Widget authentication data.

    Implements the official verification algorithm:
    1. Validate required fields and types
    2. Filter to allowed fields only (defense in depth)
    3. Sort all fields alphabetically (excluding 'hash')
    4. Build data_check_string as "key=value\\n" pairs
    5. Compute HMAC-SHA-256 using SHA256(bot_token) as secret key
    6. Compare with received hash

    Args:
        data: Dict with Telegram auth fields (id, first_name, auth_date, hash, etc.)
        bot_token: The Telegram bot token
        max_age_seconds: Maximum age of auth_date before rejection. Defaults to
            settings.TELEGRAM_AUTH_MAX_AGE (e.g. 86400=24h; use 300 for 5min).

    Returns:
        True if authentication is valid, False otherwise
    """
    if max_age_seconds is None:
        max_age_seconds = settings.TELEGRAM_AUTH_MAX_AGE
    # Validate required fields present
    if not all(field in data for field in REQUIRED_FIELDS):
        return False

    # Validate id and auth_date are numeric
    try:
        int(data["id"])
        int(data["auth_date"])
    except (ValueError, TypeError):
        return False

    # Filter to allowed fields only (strip unexpected keys)
    filtered = {k: v for k, v in data.items() if k in ALLOWED_FIELDS}

    # Check auth_date freshness
    auth_timestamp = int(filtered["auth_date"])
    if time.time() - auth_timestamp > max_age_seconds:
        return False

    # Build data_check_string from sorted key=value pairs (excluding hash)
    check_pairs = sorted(
        f"{k}={v}" for k, v in filtered.items() if k != "hash"
    )
    data_check_string = "\n".join(check_pairs)

    # Secret key = SHA256(bot_token)
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()

    # Compute HMAC-SHA-256
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_hash, filtered["hash"])
