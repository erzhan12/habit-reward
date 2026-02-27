# Security

## Threat Model

The Habit Reward system uses Telegram-based authentication (Confirm/Deny buttons) instead of passwords. The primary threat model covers:

1. **Username enumeration** — An attacker probing the login endpoint to discover valid usernames.
2. **Timing side-channels** — Measuring response times to distinguish valid from invalid usernames or different internal states.
3. **Token brute-force** — Guessing login tokens to hijack a session.
4. **Token replay** — Reusing a consumed token to create a duplicate session.
5. **Rate-limit bypass** — Circumventing per-IP rate limits via IP spoofing (X-Forwarded-For).
6. **Cross-site attacks** — CSRF, XSS, and injection via user-controlled inputs (username, User-Agent).

## Security Properties

### Anti-Enumeration

Both known and unknown usernames receive an identical HTTP 200 response with a token and generic message. All DB writes and Telegram API calls are deferred to a background thread pool, so response timing is constant regardless of user existence. An attacker cannot distinguish valid from invalid usernames by observing:

- Response body (same structure for both)
- Response status code (always 200)
- Response timing (constant-time synchronous path)
- Status polling behavior (cache-only tokens for unknown users expire silently via TTL)

### Timing Attack Resistance

- **Status polling jitter**: `check_status` adds 50-200ms random jitter (configurable via `WEB_LOGIN_JITTER_MIN`/`WEB_LOGIN_JITTER_MAX`) from a `secrets.SystemRandom()` CSPRNG.
- **Jitter scope**: Applied to `pending`, `expired`, and `error` statuses — these have cache-dependent code paths with measurably different timing. Terminal statuses (`confirmed`, `denied`, `used`) are excluded as they only appear after a real DB write and don't leak information.
- **Background processing**: Token generation, cache writes, and HTTP response happen synchronously. DB writes and Telegram sends happen asynchronously in a bounded thread pool.

### Token Security

- **256-bit entropy**: Login tokens use `secrets.token_urlsafe(32)` (256 bits), making brute-force infeasible.
- **Format validation**: Tokens are validated for length (40-50 chars) and character set (URL-safe base64) before processing.
- **Atomic replay prevention**: Confirmed tokens are atomically marked `used` via `UPDATE ... WHERE status='confirmed'`, preventing race conditions.
- **Single-use guarantee**: `mark_as_used` returns the count of updated rows — if 0, the token was already consumed.

### Rate Limiting

All authentication endpoints are rate-limited per IP via `django-ratelimit`:

| Endpoint | Setting | Default |
|---|---|---|
| `POST /auth/bot-login/request/` | `AUTH_RATE_LIMIT` | `10/m` |
| `GET /auth/bot-login/status/<token>/` | `AUTH_STATUS_RATE_LIMIT` | `30/m` |
| `POST /auth/bot-login/complete/` | `AUTH_RATE_LIMIT` | `10/m` |

### X-Forwarded-For Trust

`TRUST_X_FORWARDED_FOR` must only be enabled behind a trusted reverse proxy that overwrites the header. Without a proxy, clients can spoof their IP to bypass rate limiting. Django system checks (`web.E001`, `web.E002`) warn when this is misconfigured.

### Input Validation

- **Username**: Validated against `^[a-z0-9_]{3,32}$` (lowercase only — input is lowercased before validation on both frontend and backend). A pre-commit hook verifies both patterns stay in sync.
- **User-Agent**: Truncated to 1024 chars, filtered for non-printable characters, parsed via `user-agents` library (never used as raw HTML).
- **Telegram messages**: Sent with `parse_mode=None` (plain text) as defense-in-depth against injection.
- **DB constraints**: `telegram_username` has a database-level `CHECK` constraint ensuring format validity.

### GDPR

- **IP anonymization**: IP addresses are hashed via SHA-256 (16-hex-char prefix) before logging. Raw IPs are never stored.
- **No IP in device_info**: The device description sent to Telegram excludes IP addresses entirely.
- **Minimal data**: Only `telegram_id` is stored for user identification.

## Circuit Breakers

- **Thread pool queue**: When `WEB_LOGIN_MAX_QUEUED` is exceeded, new requests return HTTP 503 (prevents unbounded resource consumption).
- **Cache failure threshold**: After 10 consecutive cache write failures, `CacheWriteError` is raised and the login request returns 503 (surfaces cache misconfiguration instead of silently degrading).

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly by opening a private issue or contacting the maintainers directly. Do not disclose vulnerabilities publicly until a fix is available.
