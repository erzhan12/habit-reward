# Feature 0026: Manual Testing Guide

## Overview

This guide provides step-by-step instructions for manually testing Feature 0026: Secure External API Access, which includes:
- **Auth Code Flow** - Secure login for web/mobile apps
- **API Key Authentication** - Automated integrations (fitness apps, scripts, etc.)

Note: `POST /v1/auth/login` (telegram_id-only) is disabled and returns `410` to prevent account takeover.

---

## Prerequisites

Before starting, ensure you have:

1. **API Server Running**
   ```bash
   make api
   ```
   Server should be available at `http://localhost:8000`
   
   Quick sanity check:
   ```bash
   curl -s http://localhost:8000/health
   ```
   Expected: `{"status":"healthy","version":"1.0.0"}`
   
   If `/health` or `/docs` shows a Django-style 404 page ("didn’t match any of these"), you are not running the
   combined ASGI app. Stop any `python manage.py runserver` process or any Uvicorn process started with
   `src.habit_reward_project.asgi:application`, then re-run `make api` (or `make bot-webhook`).

2. **Telegram Bot Running** (for auth code delivery)
   ```bash
   make bot
   ```
   Bot must be running to receive auth codes

3. **Test User Created**
   - User must exist in database with a known `telegram_id` (Telegram-linked / eligible to authenticate)
   - User should have Telegram bot access (so they can actually receive auth codes)

4. **Tools Installed**
   - `curl` - For API requests
   - `jq` - For JSON parsing (optional but helpful)
   - Telegram app - To receive auth codes

---

## A. Auth Code Flow Testing

### Test 1: Request Auth Code

**Action:**
```bash
curl -X POST http://localhost:8000/v1/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID", "device_info": "Test Device"}'
```

**Expected Result:**
- Status: `200 OK`
- Response contains: `{"message": "If the account exists, a code was sent to Telegram", "expires_in_seconds": 300}`
- Check Telegram: You should receive a message with a 6-digit code

**Verification:**
- Code is exactly 6 digits
- Message includes device info ("Test Device")
- Message includes expiration warning

---

### Test 2: Verify Auth Code Successfully

**Action:**
```bash
curl -X POST http://localhost:8000/v1/auth/verify-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID", "code": "123456"}'
```
(Replace `123456` with the actual code from Telegram)

**Expected Result:**
- Status: `200 OK`
- Response contains:
  ```json
  {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
  ```

**Verification:**
- Tokens are valid JWT format
- Can use `access_token` for authenticated requests

---

### Test 3: Verify Code Cannot Be Reused

**Action:**
Use the same code from Test 2 again:
```bash
curl -X POST http://localhost:8000/v1/auth/verify-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID", "code": "SAME_CODE_FROM_TEST_2"}'
```

**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"error": {"code": "INVALID_CODE", "message": "Invalid or expired code"}}`

**Verification:**
- Code is single-use only
- Cannot replay the same code

---

### Test 4: Rate Limiting

**Action:**
Request 4 codes within 1 hour:
```bash
# Request 1
curl -X POST http://localhost:8000/v1/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID"}'

# Request 2 (wait a few seconds)
curl -X POST http://localhost:8000/v1/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID"}'

# Request 3
curl -X POST http://localhost:8000/v1/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID"}'

# Request 4 (should be rate limited)
curl -X POST http://localhost:8000/v1/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID"}'
```

**Expected Result:**
- First 3 requests: `200 OK`
- 4th request: `429 Too Many Requests`
- Response: `{"error": {"code": "RATE_LIMITED", "message": "Too many code requests..."}}`

**Verification:**
- Rate limit is enforced (max 3 requests per hour)

---

### Test 5: Invalid Code Handling

**Action:**
Try verifying with wrong code:
```bash
curl -X POST http://localhost:8000/v1/auth/verify-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID", "code": "000000"}'
```

**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"error": {"code": "INVALID_CODE", "message": "Invalid or expired code"}}`

**Verification:**
- Wrong codes are rejected
- Error message doesn't reveal if user exists (security)

---

### Test 6: Code Expiration

**Action:**
1. Request a code
2. Wait 6+ minutes (code expires after 5 minutes)
3. Try to verify the expired code

**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"error": {"code": "INVALID_CODE", "message": "Invalid or expired code"}}`

**Verification:**
- Codes expire after 5 minutes
- Expired codes cannot be used

---

### Test 7: User Enumeration Protection

**Action:**
Request code for non-existent user:
```bash
curl -X POST http://localhost:8000/v1/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "999999999"}'
```

**Expected Result:**
- Status: `200 OK` (NOT 404)
- Response: `{"message": "If the account exists, a code was sent to Telegram", "expires_in_seconds": 300}`
- No code actually sent (no Telegram message)

**Verification:**
- Same response for existing and non-existing users
- Prevents user enumeration attacks

---

## B. API Key Flow Testing

### Test 1: Create API Key via Telegram Bot

**Action:**
1. Open Telegram and start conversation with your bot
2. Send: `/settings`
3. Select: "🔑 API Keys"
4. Select: "➕ Create New Key"
5. Enter a name (e.g., "Test Key")
6. Copy the generated key (starts with `hrk_`)

**Expected Result:**
- Key is displayed ONCE
- Key format: `hrk_` followed by ~43 characters
- Warning message: "Copy now - you won't see it again!"

**Verification:**
- Key has correct prefix
- Key is long enough (cryptographically secure)
- Key is only shown once

---

### Debug: Verify API Key Stored in DB (Hash)

API keys are stored hashed in the `api_keys` table (SQLite: `db.sqlite3`). You will not see the plaintext key again.

**List keys:**
```bash
sqlite3 db.sqlite3 "select id, user_id, name, is_active, created_at, last_used_at, expires_at, key_hash from api_keys order by created_at desc limit 20;"
```

**Verify a specific key matches a row (compute SHA256 hash locally):**
```bash
.venv/bin/python - <<'PY'
import hashlib
raw_key = "hrk_1ImsL27xacD5U7YvCWCQ6iEL3q0AkOLWVFZS-v-tuEU"
print(hashlib.sha256(raw_key.encode()).hexdigest())
PY
```
Compare the printed hash to `api_keys.key_hash`. Do not paste your real key into chat logs.

### Test 2: Authenticate with API Key

**Action:**
```bash
curl -X GET http://localhost:8000/v1/users/me \
  -H "X-API-Key: hrk_1ImsL27xacD5U7YvCWCQ6iEL3q0AkOLWVFZS-v-tuEU" \
  -H "Content-Type: application/json"
```

**Expected Result:**
- Status: `200 OK`
- Response contains user information:
  ```json
  {
    "id": 1,
    "telegram_id": "YOUR_TELEGRAM_ID",
    "name": "Your Name",
    "language": "en"
  }
  ```

**Verification:**
- API key authenticates successfully
- Returns correct user data

If you get `401`:
- `MISSING_TOKEN` means you're hitting an endpoint that requires JWT (should not happen for `/v1/users/me` in this feature).
- `INVALID_API_KEY` usually means the key wasn’t created/stored, was copied incorrectly, or was revoked.

---

### Test 3: Complete Habit with API Key

**Prerequisites:**
- Have at least one habit created
- Know the habit ID

**Action:**
```bash
curl -X POST http://localhost:8000/v1/habits/31/complete \
  -H "X-API-Key: hrk_1ImsL27xacD5U7YvCWCQ6iEL3q0AkOLWVFZS-v-tuEU" \
  -H "Content-Type: application/json" \
  -d '{"target_date": "2026-01-02"}'
```

**Expected Result:**
- Status: `200 OK`
- Response:
  ```json
  {
    "habit_confirmed": true,
    "streak_count": 1,
    "log_id": 123
  }
  ```

**Verification:**
- Habit completion works with API key
- No JWT token needed

---

### Test 4: Invalid API Key

**Action:**
```bash
curl -X GET http://localhost:8000/v1/users/me \
  -H "X-API-Key: hrk_invalid_key_12345" \
  -H "Content-Type: application/json"
```

**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"error": {"code": "INVALID_API_KEY", "message": "Invalid or expired API key"}}`

**Verification:**
- Invalid keys are rejected
- Clear error message

---

### Test 5: Revoke API Key

**Action:**
1. Open Telegram bot
2. Send: `/settings` → "🔑 API Keys" → "❌ Revoke Key"
3. Select the key to revoke
4. Confirm revocation

**Expected Result:**
- Key is revoked (marked as inactive)
- Confirmation message shown

**Verification:**
- Revoked key no longer works (see Test 6)

---

### Test 6: Use Revoked Key

**Action:**
Try to use the revoked key:
```bash
curl -X GET http://localhost:8000/v1/users/me \
  -H "X-API-Key: hrk_REVOKED_KEY_HERE" \
  -H "Content-Type: application/json"
```

**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"error": {"code": "INVALID_API_KEY", "message": "Invalid or expired API key"}}`

**Verification:**
- Revoked keys are rejected
- Security: keys can be disabled immediately

---

### Test 7: JWT Priority Over API Key

**Action:**
Use both JWT and API key in the same request:
```bash
# First get a JWT token via auth code flow
# 1) Request code (check Telegram for the 6-digit code)
curl -s -X POST http://localhost:8000/v1/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID"}'

# 2) Verify code to obtain access token
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/verify-code \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID", "code": "CODE_FROM_TELEGRAM"}' | jq -r '.access_token')

# Then use both
curl -X GET http://localhost:8000/v1/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Key: hrk_YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json"
```

**Expected Result:**
- Status: `200 OK`
- Request succeeds using JWT (API key is ignored)

**Verification:**
- JWT takes priority when both are present
- API key is only used when JWT is missing

---

### (Optional) Deprecated Login Endpoint Is Disabled

**Action:**
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "YOUR_TELEGRAM_ID"}'
```

**Expected Result:**
- Status: `410 Gone`
- Response: `{"error": {"code": "DEPRECATED_LOGIN", ...}}`

---

## C. Security Testing

### Test 1: Cross-User Access Prevention

**Action:**
1. Create API key for User A
2. Create a habit for User B
3. Try to complete User B's habit using User A's API key

**Expected Result:**
- Status: `404 Not Found` or `403 Forbidden`
- Habit cannot be accessed

**Verification:**
- Users cannot access other users' resources
- API keys are scoped to their owner

---

### Test 2: Missing Authentication

**Action:**
```bash
curl -X GET http://localhost:8000/v1/users/me \
  -H "Content-Type: application/json"
```

**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"error": {"code": "AUTH_REQUIRED", "message": "Authentication required..."}}`

**Verification:**
- Protected endpoints require authentication
- Clear error message

---

### Test 3: Key Format Validation

**Action:**
Try API key without `hrk_` prefix:
```bash
curl -X GET http://localhost:8000/v1/users/me \
  -H "X-API-Key: invalid_format_key" \
  -H "Content-Type: application/json"
```

**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"error": {"code": "INVALID_API_KEY", ...}}`

**Verification:**
- Key format is validated
- Invalid formats are rejected

---

## D. Automated Testing

For automated testing, use the provided script:

```bash
./scripts/test_auth_api.sh
```

This script:
- Creates test users
- Generates API keys
- Tests auth code flow
- Tests API key authentication
- Tests habit completion with API keys
- Provides test summary

---

## Troubleshooting

### Auth Code Not Received

- **Check:** Bot is running (`make bot`)
- **Check:** User exists in database
- **Check:** User's `telegram_id` is correct
- **Check:** Bot has permission to message user

### API Key Not Working

- **Check:** Key is copied correctly (no extra spaces)
- **Check:** Key has `hrk_` prefix
- **Check:** Key hasn't been revoked
- **Check:** Key hasn't expired (if expiration was set)

### Rate Limiting Issues

- **Wait:** Rate limit resets after 1 hour
- **Note:** Rate limit is per user (telegram_id)
- **Workaround:** Use different telegram_id for testing

---

## Test Checklist

- [ ] Auth code request succeeds
- [ ] Auth code received in Telegram
- [ ] Auth code verification succeeds
- [ ] Used code cannot be reused
- [ ] Rate limiting works (4th request blocked)
- [ ] Invalid code rejected
- [ ] Expired code rejected
- [ ] User enumeration protection works
- [ ] API key created via bot
- [ ] API key authenticates successfully
- [ ] Habit completion works with API key
- [ ] Invalid API key rejected
- [ ] Revoked key rejected
- [ ] JWT takes priority over API key
- [ ] Cross-user access prevented
- [ ] Missing auth returns 401

---

## Notes

- Auth codes expire after 5 minutes
- Rate limit: 3 requests per hour per user
- API keys are shown only once during creation
- API keys can be revoked anytime via Telegram bot
- JWT tokens expire after 15 minutes (access) or 7 days (refresh)
