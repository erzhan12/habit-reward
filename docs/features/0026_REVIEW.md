# Feature 0026 Code Review: Secure External API Access for Habit Completion

## Scope reviewed

- `src/core/models.py` (new `AuthCode`, `APIKey`)
- `src/core/migrations/0009_add_authcode_apikey_models.py`
- `src/core/repositories.py` (`AuthCodeRepository`, `APIKeyRepository`)
- `src/api/services/auth_code_service.py` (`AuthCodeService`, `APIKeyService`)
- `src/api/dependencies/auth.py` (`get_current_user_flexible`)
- `src/api/dependencies/api_key.py` (`get_api_key_user`)
- `src/api/v1/routers/auth.py` (`/request-code`, `/verify-code`, legacy `/login`)
- `src/api/v1/routers/habits.py` (auth dependency updated for completion endpoints)
- `src/bot/handlers/settings_handler.py` (API key management UI)
- `src/bot/messages.py`, `src/bot/keyboards.py` (new settings + API key strings/buttons)

## Implementation coverage vs plan

- ✅ New persistence: `AuthCode` + `APIKey` models and migration exist.
- ✅ Auth code endpoints exist: `POST /v1/auth/request-code`, `POST /v1/auth/verify-code`.
- ✅ API key auth path exists: key creation/list/revoke via Telegram bot; `X-API-Key` accepted for habit completion endpoints via `get_current_user_flexible`.
- ⚠️ Some plan items are partially implemented or missing (details below): brute-force protections, “no enumeration” behavior, tests, and hard deprecation of insecure `/login`.

## Findings

### Critical

1. **Legacy insecure login still enabled**
   - `POST /v1/auth/login` still authenticates with only `telegram_id` (`src/api/v1/routers/auth.py`).
   - This preserves the “anyone who knows a telegram_id can login” vulnerability the feature is meant to eliminate.
   - Recommendation: disable for external use (e.g., `deprecated=True` + `include_in_schema=False`, or require auth-code flow only, or gate behind an internal flag).

2. **Inactive users can authenticate via JWT path in `get_current_user_flexible`**
   - `get_current_user_flexible` returns `get_current_user(credentials)` without an `is_active` check (`src/api/dependencies/auth.py`).
   - This means any endpoint switched to `get_current_user_flexible` (notably habit completion) can be called by an inactive user holding a still-valid token.
   - Recommendation: after JWT verification, enforce the same active check as `get_current_active_user` (or call it directly).

3. **Auth code single-use is not atomic (race condition)**
   - Verify flow does: “read valid code” then “mark used” (`src/api/services/auth_code_service.py` + `src/core/repositories.py`).
   - Two concurrent requests could both pass `get_valid_code()` before either marks the row used, allowing one-time codes to be reused.
   - Recommendation: make verification+consume atomic (transaction + `SELECT ... FOR UPDATE`, or conditional `UPDATE ... WHERE used=False AND expires_at>now` and check affected rows).

### High

4. **Brute-force protection not implemented**
   - Plan calls out “max 5 failed attempts then block for 15 minutes”; no attempt tracking or lockout exists in the current code (`AuthCodeService.verify_code` just returns `None` on failure).
   - Recommendation: implement attempt counters + lockout (DB model, cache/Redis, or per-user backoff), and ensure failures don’t leak whether a `telegram_id` exists.

5. **Potential HTML injection / phishing via unescaped user-controlled fields**
   - Telegram auth-code message uses `parse_mode="HTML"` and interpolates `device_info` without escaping (`src/api/v1/routers/auth.py`).
   - Bot API-key messages/listing use `parse_mode="HTML"` and interpolate `key_name` / `APIKey.name` without escaping (`src/bot/handlers/settings_handler.py`).
   - A malicious client could inject HTML into `device_info` or key names to spoof UI or links.
   - Recommendation: escape user-provided strings (e.g., `html.escape`) before inserting into HTML messages.

### Medium

6. **“No user enumeration” behavior is inconsistent**
   - The plan text emphasizes “same response whether user exists or not”, but `request-code` currently raises `USER_NOT_FOUND` when the user is unknown/inactive (`src/api/v1/routers/auth.py`).
   - Recommendation: decide on the intended security posture and align code + docs (either always return 200 “Code sent” or explicitly accept enumeration risk and remove misleading comments).

7. **API key dependency duplication / unused path**
   - `src/api/dependencies/api_key.py` defines `get_api_key_user`, but it is not used anywhere (flexible auth calls `api_key_service.verify_api_key` directly).
   - Recommendation: either use `get_api_key_user` from `get_current_user_flexible` to centralize behavior/errors, or delete the unused dependency module.

8. **Module boundaries feel blurred**
   - `src/api/services/auth_code_service.py` contains both auth-code and API-key services; `src/bot/handlers/settings_handler.py` imports `api_key_service` from `src/api/...`.
   - This works, but it mixes “API layer” concerns into bot handlers and makes naming misleading.
   - Recommendation: consider relocating key management logic to `src/services/` (framework-neutral) or a `src/core/` service module, and rename the module accordingly.

### Low / Style / Maintenance

9. **Likely lint issue: unused import**
   - `api_key_repository` is imported but unused in `src/bot/handlers/settings_handler.py`.

10. **Missing tests for new auth flows**
   - The plan outlines test coverage for auth-code issuance/verification, API-key validation, combined auth priority, and habit completion via API key.
   - No new tests appear under `tests/api/` for this feature.
   - Recommendation: add focused tests for the core security properties (single use, expiry, rate-limit, inactive users, ownership/403, JWT vs API key precedence).

## Suggested follow-ups (prioritized)

1. Disable or strongly gate `POST /v1/auth/login` for external clients.
2. Enforce `is_active` for JWT in `get_current_user_flexible`.
3. Make auth-code verification atomic; add brute-force attempt protections.
4. Escape user-controlled strings in all HTML Telegram messages.
5. Add minimal test coverage for the security-critical flows.

