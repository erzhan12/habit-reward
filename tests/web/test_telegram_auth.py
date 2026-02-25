"""Tests for Telegram Login Widget hash verification."""

import hashlib
import hmac
import time

from src.web.utils.telegram_auth import verify_telegram_auth

BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def _make_auth_data(bot_token=BOT_TOKEN, **overrides):
    """Build valid Telegram auth data with correct HMAC hash."""
    data = {
        "id": "999999999",
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "auth_date": str(int(time.time())),
    }
    data.update(overrides)

    # Compute valid hash
    check_pairs = sorted(f"{k}={v}" for k, v in data.items() if k != "hash")
    data_check_string = "\n".join(check_pairs)
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    data["hash"] = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return data


def test_valid_hash():
    """Valid auth data should pass verification."""
    data = _make_auth_data()
    assert verify_telegram_auth(data, BOT_TOKEN) is True


def test_tampered_first_name():
    """Modifying a field after signing should fail."""
    data = _make_auth_data()
    data["first_name"] = "Hacker"
    assert verify_telegram_auth(data, BOT_TOKEN) is False


def test_wrong_bot_token():
    """Verifying with a different bot token should fail."""
    data = _make_auth_data()
    assert verify_telegram_auth(data, "wrong:token") is False


def test_missing_hash():
    """Data without hash field should fail."""
    data = _make_auth_data()
    del data["hash"]
    assert verify_telegram_auth(data, BOT_TOKEN) is False


def test_missing_auth_date():
    """Data without auth_date should fail."""
    data = {"id": "123", "first_name": "Test", "hash": "abc"}
    assert verify_telegram_auth(data, BOT_TOKEN) is False


def test_expired_auth_date():
    """Auth data older than max_age_seconds should fail."""
    data = _make_auth_data(auth_date=str(int(time.time()) - 100000))
    assert verify_telegram_auth(data, BOT_TOKEN) is False


def test_custom_max_age():
    """Custom max_age_seconds should be respected."""
    # 10 seconds ago
    data = _make_auth_data(auth_date=str(int(time.time()) - 10))
    # With 5-second max age, should fail
    assert verify_telegram_auth(data, BOT_TOKEN, max_age_seconds=5) is False
    # With 60-second max age, should pass
    assert verify_telegram_auth(data, BOT_TOKEN, max_age_seconds=60) is True


def test_invalid_auth_date_format():
    """Non-numeric auth_date should fail."""
    data = _make_auth_data()
    data["auth_date"] = "not-a-number"
    # Hash will be wrong too, but auth_date check comes first
    assert verify_telegram_auth(data, BOT_TOKEN) is False


def test_non_numeric_id():
    """Non-numeric id should fail early."""
    data = _make_auth_data()
    data["id"] = "not-a-number"
    assert verify_telegram_auth(data, BOT_TOKEN) is False


def test_missing_id():
    """Data without id field should fail."""
    data = _make_auth_data()
    del data["id"]
    assert verify_telegram_auth(data, BOT_TOKEN) is False


def test_unexpected_fields_stripped():
    """Extra fields injected into data should be stripped before HMAC check."""
    data = _make_auth_data()
    # Add unexpected field — if not stripped, HMAC will include it and fail
    data["evil_field"] = "injected"
    assert verify_telegram_auth(data, BOT_TOKEN) is True


def test_concurrent_timestamp():
    """auth_date equal to current time should pass."""
    data = _make_auth_data(auth_date=str(int(time.time())))
    assert verify_telegram_auth(data, BOT_TOKEN) is True
