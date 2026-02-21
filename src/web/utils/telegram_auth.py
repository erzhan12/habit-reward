"""Telegram Login Widget hash verification."""

import hashlib
import hmac
import time


def verify_telegram_auth(data: dict, bot_token: str, max_age_seconds: int = 86400) -> bool:
    """Verify Telegram Login Widget authentication data.

    Implements the official verification algorithm:
    1. Sort all fields alphabetically (excluding 'hash')
    2. Build data_check_string as "key=value\\n" pairs
    3. Compute HMAC-SHA-256 using SHA256(bot_token) as secret key
    4. Compare with received hash

    Args:
        data: Dict with Telegram auth fields (id, first_name, auth_date, hash, etc.)
        bot_token: The Telegram bot token
        max_age_seconds: Maximum age of auth_date before rejection (default 24h)

    Returns:
        True if authentication is valid, False otherwise
    """
    received_hash = data.get("hash")
    if not received_hash:
        return False

    auth_date = data.get("auth_date")
    if not auth_date:
        return False

    # Check auth_date freshness
    try:
        auth_timestamp = int(auth_date)
        if time.time() - auth_timestamp > max_age_seconds:
            return False
    except (ValueError, TypeError):
        return False

    # Build data_check_string from sorted key=value pairs (excluding hash)
    check_pairs = sorted(
        f"{k}={v}" for k, v in data.items() if k != "hash"
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

    return hmac.compare_digest(computed_hash, received_hash)
