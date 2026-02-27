# Habit Reward System

A gamified habit-reward system that tracks habits with per-habit streaks, uses variable ratio rewards with streak multipliers, and supports cumulative rewards with lifecycle status tracking.

## Features

- **Per-Habit Streak Tracking**: Each habit maintains its own streak independently
- **Weighted Random Rewards**: Variable ratio reward system with streak multipliers
- **Cumulative Rewards**: Collect pieces toward larger rewards with status tracking (🕒 Pending, ⏳ Achieved, ✅ Completed)
- **Telegram Bot Interface**: Easy-to-use bot for logging habits and managing rewards
- **OpenAI NLP Integration**: Natural language processing for habit classification
- **Streamlit Dashboard**: Visual analytics and progress tracking
- **Django Backend**: SQLite (production default) via Django ORM (PostgreSQL optional)

## Architecture

```
habit_reward/
├── src/
│   ├── models/          # Pydantic data models
│   ├── core/             # Django models and repositories
│   ├── services/         # Business logic layer
│   ├── bot/              # Telegram bot handlers
│   ├── dashboard/        # Streamlit dashboard components
│   └── api/              # REST API endpoints
├── tests/                # Unit tests
├── pyproject.toml        # Project configuration and dependencies (uv)
└── .env                  # Environment configuration
```

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer
- Telegram Bot Token (from @BotFather)
- OpenAI API Key (optional, for NLP features)

### Setup Steps

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or on macOS: brew install uv
   ```

2. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd habit_reward
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```
   This will create a virtual environment and install all dependencies automatically.

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up database**
   ```bash
   # Run Django migrations
   uv run python manage.py migrate
   
   # Create a superuser for Django admin (optional)
   uv run python manage.py createsuperuser
   ```

## Usage

### Running the Telegram Bot

```bash
./run_bot.sh
# Or: uv run python -m src.bot.main
```

**Available Bot Commands:**
- `/start` - Welcome message and help
- `/habit_done` - Log a completed habit
- `/streaks` - View current streaks for all habits
- `/list_rewards` - See all available rewards
- `/my_rewards` - Check cumulative reward progress
- `/claim_reward <name>` - Claim an achieved reward
- `/set_reward_status <name> <status>` - Update reward status

### Running the Dashboard

```bash
./run_dashboard.sh
# Or: uv run streamlit run src/dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

**Dashboard Features:**
- Recent habit completions table
- Cumulative reward progress cards with progress bars
- Actionable rewards section with claim buttons
- Reward value overview (total earned, claimed, pending)
- Per-habit streak chart

## How It Works

### Streak Calculation

Each habit maintains its own streak:
1. First completion: streak = 1
2. Completed yesterday: increment streak
3. Already completed today: return current streak
4. Missed days: reset to 1

### Reward Weight Formula

```
total_weight = habit_weight × streak_multiplier
where streak_multiplier = 1 + (streak_count × 0.1)
```

### Weighted Random Selection

1. Fetch all active rewards (including "none" type)
2. Adjust each reward weight by total_weight
3. Perform weighted random selection
4. If cumulative: increment pieces, check if achieved

### Cumulative Rewards

- **🕒 Pending**: Still collecting pieces
- **⏳ Achieved**: Pieces >= required, ready to claim
- **✅ Completed**: Claimed by user

## Development

### Running Tests

```bash
uv run pytest tests/
```

### Running Tests with Coverage

```bash
uv run pytest --cov=src tests/
```

### Project Structure

- **Models** (`src/models/`): Pydantic models for data validation
- **Repositories** (`src/core/repositories.py`): Data access layer using repository pattern with Django ORM
- **Services** (`src/services/`): Business logic layer
  - `streak_service.py`: Streak calculation
  - `reward_service.py`: Reward selection and cumulative progress
  - `habit_service.py`: Main orchestration
  - `nlp_service.py`: OpenAI habit classification
- **Bot** (`src/bot/`): Telegram bot interface
- **Dashboard** (`src/dashboard/`): Streamlit visualization

## Configuration

All configuration is managed via environment variables in `.env`:

```env
# Required
TELEGRAM_BOT_TOKEN=your_token_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=your_key_here

# Optional
DEFAULT_USER_TELEGRAM_ID=your_telegram_id_here
```

### Web Login Configuration

| Variable | Default | Description |
|---|---|---|
| `WEB_LOGIN_THREAD_POOL_SIZE` | `10` | Max concurrent background login workers (DB writes + Telegram send). |
| `WEB_LOGIN_MAX_QUEUED` | `50` | Max queued login requests before returning HTTP 503. |
| `WEB_LOGIN_EXPIRY_MINUTES` | `5` | How long users have to confirm a login request in Telegram. |
| `AUTH_RATE_LIMIT` | `10/m` | Rate limit for login request and complete endpoints (per IP). |
| `AUTH_STATUS_RATE_LIMIT` | `30/m` | Rate limit for status polling endpoint (per IP). |
| `TRUST_X_FORWARDED_FOR` | `False` | Trust X-Forwarded-For header for client IP. **Only enable behind a trusted reverse proxy** (nginx/Caddy) that overwrites this header. When exposed directly to the internet, clients can spoof their IP. **WARNING:** In production (`DEBUG=False`), enabling this without a reverse proxy is a security risk — attackers can forge their IP to bypass rate limiting and IP-based access controls. |

#### Bot Login Endpoint Rate Limits

- `POST /auth/bot-login/request/` uses `AUTH_RATE_LIMIT` (default `10/m`).
- `POST /auth/bot-login/complete/` uses `AUTH_RATE_LIMIT` (default `10/m`).
- `GET /auth/bot-login/status/<token>/` uses `AUTH_STATUS_RATE_LIMIT` (default `30/m`).

#### Security Design

The bot login flow implements several security properties:

- **Anti-enumeration**: Unknown usernames receive the same response as known ones (same token, same timing) to prevent attackers from discovering valid usernames.
- **Timing resistance**: All status checks include 50-200ms random jitter from a CSPRNG to mask timing differences between cache hits, DB lookups, and different code paths.
- **Atomic replay prevention**: Tokens are marked as "used" atomically via SQL UPDATE with a WHERE clause, preventing race conditions where the same token could be used twice.
- **Rate limiting**: All endpoints are rate-limited per IP address to prevent brute force attacks and abuse.
| `CONN_MAX_AGE` | `600` | Database connection reuse timeout in seconds (reduces overhead in thread pool workers). |
| `WEB_LOGIN_JITTER_MIN` | `0.05` | Minimum timing jitter (seconds) added to status polling responses. |
| `WEB_LOGIN_JITTER_MAX` | `0.2` | Maximum timing jitter (seconds) added to status polling responses. |

#### Queue Overflow Handling

When `WEB_LOGIN_MAX_QUEUED` is exceeded (i.e., there are more pending login requests than the queue can hold), new requests receive an **HTTP 503 Service Unavailable** response with:

```json
{"error": "Service temporarily unavailable. Please try again shortly."}
```

This acts as a circuit breaker to prevent unbounded resource consumption under load. To tune for production:

- **`WEB_LOGIN_THREAD_POOL_SIZE`**: Controls how many login requests are processed concurrently (DB write + Telegram API call). Each worker blocks for the duration of a Telegram API round-trip (~200ms–2s). Start with 10 for low traffic, increase to 25–50 for higher concurrency. Requires PostgreSQL for values above ~10 (SQLite locks under concurrent writes).
- **`WEB_LOGIN_MAX_QUEUED`**: Requests beyond the thread pool capacity queue here before 503 is returned. Set to 2–5x the thread pool size. For example, with `THREAD_POOL_SIZE=25`, set `MAX_QUEUED=100` to absorb bursts of ~125 simultaneous logins.

Monitor queue saturation with:

```bash
grep 'Login thread pool queue full' /path/to/logs/app.log
```

If you see frequent 503s, increase both values and ensure your database connection pool (`CONN_MAX_AGE`) can support the additional workers.

#### Tuning Thread Pool and Queue Size

If you observe HTTP 503 errors during peak login times, increase `WEB_LOGIN_THREAD_POOL_SIZE` and/or `WEB_LOGIN_MAX_QUEUED`. Monitor with:

```bash
grep 'Login thread pool queue full' /path/to/logs/app.log
```

- **`WEB_LOGIN_THREAD_POOL_SIZE`**: Each worker handles one DB write + one Telegram API call. If Telegram responses are slow (>1s), you need more workers. Start with 10 and increase if you see queuing.
- **`WEB_LOGIN_MAX_QUEUED`**: Requests beyond the thread pool queue here. If this fills up, new requests get 503. Set this to 2-5x the thread pool size. A value of 50 supports bursts of ~60 simultaneous logins.

### Scheduled Tasks

The `cleanup_expired_logins` management command deletes expired `WebLoginRequest` records to prevent unbounded table growth. Schedule it hourly via cron:

```cron
0 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py cleanup_expired_logins >> /var/log/cleanup.log 2>&1
```

Or with `uv`:

```cron
0 * * * * cd /path/to/project && uv run python manage.py cleanup_expired_logins >> /var/log/cleanup.log 2>&1
```

## Algorithms

### Per-Habit Streak Algorithm

```
INPUT: user_id, habit_id
OUTPUT: current_streak

1. last_log = get_last_log(user_id, habit_id)
2. IF last_log is None: RETURN 1
3. last_date = last_log.last_completed_date
4. today = current_date()
5. IF last_date == today: RETURN last_log.streak_count
6. IF last_date == yesterday: RETURN last_log.streak_count + 1
7. ELSE: RETURN 1
```

### Weighted Random Reward Selection

```
INPUT: total_weight
OUTPUT: selected_reward

1. rewards = get_all_active_rewards()
2. adjusted_weights = [r.weight * total_weight for r in rewards]
3. selected = random.choices(rewards, weights=adjusted_weights, k=1)[0]
4. RETURN selected
```

### Cumulative Progress Update

```
INPUT: user_id, reward_id
OUTPUT: reward_progress

1. progress = get_or_create_progress(user_id, reward_id)
2. progress.pieces_earned += 1
3. IF progress.pieces_earned >= reward.pieces_required:
     progress.status = "⏳ Achieved"
4. ELSE:
     progress.status = "🕒 Pending"
5. RETURN progress
```

## Web Login Flow

The web interface uses a bot-based Confirm/Deny login — no passwords.

```
 Browser                   Django                    Telegram Bot
    │                         │                           │
    │  POST /request/         │                           │
    │  {"username":"alice"}   │                           │
    │────────────────────────>│                           │
    │                         │ generate token            │
    │                         │ cache wl_pending:{token}  │
    │  200 {token, expires}   │                           │
    │<────────────────────────│                           │
    │                         │──[thread pool]──────────> │
    │                         │  send Confirm/Deny buttons│
    │                         │                           │
    │  GET /status/{token}/   │                           │
    │────────────────────────>│                           │
    │  {"status":"pending"}   │                           │
    │<────────────────────────│                           │
    │                         │                           │
    │          ...polling...  │    User taps Confirm      │
    │                         │<──────────────────────────│
    │                         │  update status=confirmed  │
    │                         │                           │
    │  GET /status/{token}/   │                           │
    │────────────────────────>│                           │
    │  {"status":"confirmed"} │                           │
    │<────────────────────────│                           │
    │                         │                           │
    │  POST /complete/        │                           │
    │  {"token":"..."}        │                           │
    │────────────────────────>│                           │
    │                         │ mark token as "used"      │
    │                         │ create Django session     │
    │  200 {redirect: "/"}    │                           │
    │<────────────────────────│                           │
```

**Security properties:**
- **Anti-enumeration**: Known and unknown usernames produce identical responses and timing (background work is deferred to a thread pool).
- **Timing jitter**: Status polling adds 50-200ms random jitter (configurable) from `secrets.SystemRandom()`.
- **Replay prevention**: Confirmed tokens are atomically marked `used` via `UPDATE … WHERE status='confirmed'`.
- **Rate limiting**: All endpoints are rate-limited per IP (`AUTH_RATE_LIMIT`, `AUTH_STATUS_RATE_LIMIT`).
- **CSP nonce**: Production responses include a per-request CSP nonce for `style-src`.

### Monitoring & Observability

Key metrics to track for the web login flow:

| Metric | How to monitor | Action threshold |
|---|---|---|
| Login queue depth | `grep 'Login thread pool queue full' app.log` | Increase `WEB_LOGIN_THREAD_POOL_SIZE` if frequent |
| Token generation retries | `grep 'Failed to generate unique token' app.log` | Should never appear — investigate if it does |
| Cache hit/miss rate | Monitor your cache backend (Redis `INFO stats`, memcached stats) | High miss rate may indicate cache eviction pressure |
| Request-to-confirmation time | Measure time between `POST /request/` and status becoming `confirmed` | If >30s, check Telegram API latency |
| 503 error rate | `grep 'temporarily unavailable' app.log` or HTTP 503 count | Increase `WEB_LOGIN_MAX_QUEUED` if >1% of requests |
| Permanent Telegram errors | `grep 'Permanent Telegram error' app.log` (logged at CRITICAL) | Check bot token validity and bot block status |

### Troubleshooting

**Telegram API unreachable:**
- Status polling returns `"error"` after the background thread fails.
- Check: `grep 'Telegram.*error' app.log` — temporary errors (network) vs permanent errors (invalid token, bot blocked).
- Verify bot token: `curl https://api.telegram.org/bot<TOKEN>/getMe`

**Cache backend failure:**
- The system degrades gracefully to DB-only mode. Status checks are slower but functional.
- Check: `grep 'Cache write failed' app.log` — frequent entries indicate a cache backend issue.
- Users may see slightly longer "pending" periods as the DB write completes in the background thread.

**Stuck pending requests:**
- Check `telegram_message_id` on the `WebLoginRequest` record — if NULL, the Telegram message was never sent.
- Verify bot token validity and that the user hasn't blocked the bot.
- Run `python manage.py cleanup_expired_logins` to clear stale records.

**Too many 429 (rate limit) errors:**
- Increase `AUTH_RATE_LIMIT` (default `10/m`) for login requests, or `AUTH_STATUS_RATE_LIMIT` (default `30/m`) for status polling.
- If behind a reverse proxy, ensure `TRUST_X_FORWARDED_FOR=True` AND set `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https")` in settings. Example nginx config:
  ```nginx
  proxy_set_header X-Forwarded-For $remote_addr;
  proxy_set_header X-Forwarded-Proto $scheme;
  ```
  Without this, rate limiting will see all requests coming from the proxy IP instead of real client IPs, making rate limits ineffective.

## Monitoring Web Login in Production

1. **503 errors (thread pool exhaustion)**: Monitor HTTP 503 responses or `grep 'Login thread pool queue full' app.log`. If frequent, increase `WEB_LOGIN_THREAD_POOL_SIZE` (PostgreSQL: 50-100, SQLite: max 10) and `WEB_LOGIN_MAX_QUEUED`.

2. **Cache hit rate**: Monitor your cache backend for `wl_pending:*` key hit/miss rates. A high miss rate indicates cache eviction pressure or misconfiguration. Check with Redis `INFO stats` or memcached `stats`.

3. **Telegram API failures**: Watch for `wl_failed:*` cache keys — these indicate background Telegram send failures. `grep 'Permanent Telegram error' app.log` (CRITICAL level) means the bot token is invalid or the bot was blocked. `grep 'Temporary Telegram error' app.log` means transient network issues.

4. **Recommended thread pool sizes**:
   - Low traffic (<10 concurrent logins): `WEB_LOGIN_THREAD_POOL_SIZE=10`, `WEB_LOGIN_MAX_QUEUED=50`
   - Medium traffic (10-50 concurrent): `WEB_LOGIN_THREAD_POOL_SIZE=25`, `WEB_LOGIN_MAX_QUEUED=100`
   - High traffic (50+ concurrent): `WEB_LOGIN_THREAD_POOL_SIZE=50-100`, `WEB_LOGIN_MAX_QUEUED=200` (requires PostgreSQL)

## Security Considerations

### Anti-Enumeration Protection

The bot login flow is designed to prevent username enumeration attacks:

- **Identical responses**: Both known and unknown usernames receive the same HTTP 200 response with a token and generic message. No branching in the response path reveals user existence.
- **Constant-time responses**: All DB writes and Telegram API calls are deferred to a background thread pool, so the HTTP response time is identical regardless of whether the user exists. An attacker cannot distinguish valid from invalid usernames by measuring response latency.
- **Cache-only tokens for unknown users**: Unknown usernames get a cache-only token that expires silently after TTL, indistinguishable from a real pending request during status polling.

### Timing Attack Protections

- **Status polling jitter**: The `check_status` endpoint adds random jitter (50-200ms, configurable via `WEB_LOGIN_JITTER_MIN`/`WEB_LOGIN_JITTER_MAX`) from a CSPRNG (`secrets.SystemRandom()`) to mask timing differences between cache hits, DB lookups, and different code paths.
- **Background processing**: Token generation, cache writes, and HTTP response happen synchronously. DB writes and Telegram sends happen asynchronously in a bounded thread pool, ensuring the response path is constant-time.

### Token Security

- **256-bit entropy**: Login tokens use `secrets.token_urlsafe(32)` (256 bits of entropy), making brute-force guessing infeasible.
- **Atomic replay prevention**: Confirmed tokens are atomically marked `used` via `UPDATE ... WHERE status='confirmed'`, preventing race conditions where the same token could be consumed twice.
- **Single-use guarantee**: The `mark_as_used` repository method returns the count of updated rows — if 0, the token was already consumed.

### Rate Limiting

All authentication endpoints are rate-limited per IP via `django-ratelimit`:

- `POST /auth/bot-login/request/` — `AUTH_RATE_LIMIT` (default `10/m`)
- `GET /auth/bot-login/status/<token>/` — `AUTH_STATUS_RATE_LIMIT` (default `30/m`)
- `POST /auth/bot-login/complete/` — `AUTH_RATE_LIMIT` (default `10/m`)

### Input Validation

- **Username validation**: Telegram usernames are validated against a canonical regex pattern (`^[a-zA-Z0-9_]{3,32}$`) shared between frontend and backend. A pre-commit hook (`scripts/check_validation_sync.sh`) verifies both patterns stay in sync.
- **Token format validation**: Tokens are validated for expected length and character set before processing.
- **User-Agent sanitization**: UA strings are truncated, filtered for non-printable characters, and parsed via the `user-agents` library (never used as raw HTML).
- **Database-level constraints**: The `telegram_username` field has a DB-level `CHECK` constraint ensuring format validity even for bulk operations that bypass `save()`.

## Ethical Considerations

1. **Data Privacy**: Only telegram_id stored, full user control via Django admin
2. **Transparent Logic**: All calculations logged and visible
3. **Motivation vs Addiction**: "None" rewards always included, streak multiplier capped
4. **Extensibility**: Repository pattern enables easy database migration

## Future Enhancements

- [ ] Multi-user support with user registration flow
- [ ] Conversational reward creation via bot
- [ ] Custom habit categories and tags
- [ ] Weekly/monthly reports
- [ ] Social features (share achievements)
- [ ] Mobile app interface
- [ ] REST API for third-party integrations
- [ ] Analytics and insights (best times, patterns)

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests to ensure they pass
6. Submit a pull request

## License

[Choose appropriate license]

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [Your contact information]

## Acknowledgments

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Data storage via Django ORM (SQLite by default; PostgreSQL optional)
- NLP powered by [OpenAI](https://openai.com)
- Dashboard created with [Streamlit](https://streamlit.io)
