# Development Rules & Patterns

## User Validation Pattern

**CRITICAL**: All Telegram bot command handlers MUST validate that the user exists and is active before processing any commands.

```python
# At the top of any handler function
telegram_id = str(update.effective_user.id)

# Validate user exists
user = user_repository.get_by_telegram_id(telegram_id)
if not user:
    await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
    return

# Check if user is active
if not user.is_active:
    await update.message.reply_text(msg('ERROR_USER_INACTIVE', lang))
    return
```

**Why**: Prevents crashes when non-registered users try to use the bot.

## Message Management & Multi-lingual Support

**CRITICAL**: All user-facing strings MUST use message constants from `src/bot/messages.py`. Never use hardcoded strings.

```python
from src.bot.messages import msg
from src.bot.language import get_message_language

async def my_handler(update: Update, context):
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)

    # Simple message
    await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))

    # Message with format variables
    await update.message.reply_text(
        msg('ERROR_REWARD_NOT_FOUND', lang, reward_name='Coffee')
    )
```

**Language Detection**: User language is automatically detected from Telegram settings on `/start` and stored in User model. Supported: `en`, `ru`, `kk`.

**Adding New Messages**:
1. Add constant to `Messages` class in `src/bot/messages.py`
2. Add translations to `_TRANSLATIONS` dictionary
3. Use in handlers: `msg('MY_NEW_MESSAGE', lang)`

### Telegram Message Formatting

**CRITICAL**: All messages MUST use HTML formatting (not Markdown). Always set `parse_mode="HTML"`.

**HTML Tags**:
- **Bold**: `<b>text</b>`
- **Italic**: `<i>text</i>`
- **Code**: `<code>text</code>`
- **Links**: `<a href="URL">text</a>`

**Escape HTML special characters**: `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`

```python
# ✅ Good
await update.message.reply_text(
    msg('SUCCESS_HABIT_COMPLETED', lang, habit_name=habit.name),
    parse_mode="HTML"
)

# ❌ Bad - Never use Markdown
await update.message.reply_text("*Bold text*", parse_mode="Markdown")
```

## Logging Pattern

**CRITICAL**: All Telegram bot command handlers MUST include comprehensive info-level logging to track user messages and bot reactions.

```python
import logging

logger = logging.getLogger(__name__)

async def my_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /my_command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /my_command from user {telegram_id} (@{username})")

    # Log validation failures
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Log processing steps
    logger.info(f"⚙️ Processing command for user {telegram_id}")

    # Log success
    logger.info(f"✅ Command completed successfully for user {telegram_id}")

    # Log outgoing messages
    await update.message.reply_text(formatted_message)
    logger.info(f"📤 Sent success message to {telegram_id}")
```

### Logging Emoji Legend

Use these emojis consistently for easy log scanning:

- 📨 - Incoming message/command from user
- 🖱️ - User interaction (callback/button click)
- ✏️ - User choosing text input
- 🎯 - User selection (habit, reward, etc.)
- 🎁 - User attempting to claim reward
- 🔄 - User attempting to change status
- 📝 - User input/parameters logged
- 🔍 - Search/query results
- 🤖 - AI/NLP processing
- ⚙️ - Processing/operation in progress
- ✅ - Success/completion
- 🔥 - Streak information
- ℹ️ - Informational message
- ⚠️ - Warning (validation failure, not found, etc.)
- ❌ - Error
- 📤 - Outgoing message/response to user

## Repository Pattern

All database operations go through repository classes in `src/core/repositories.py`. Never query Django ORM directly from handlers or services.

**Global Repository Instances**:
```python
from src.core.repositories import (
    user_repository,
    habit_repository,
    habit_log_repository,
    reward_repository,
    reward_progress_repository
)
```

### Django ORM Repository Pattern

All repository methods use `sync_to_async` to bridge synchronous Django ORM with async handlers:

```python
from asgiref.sync import sync_to_async
from src.core.models import User

class UserRepository:
    async def get_by_telegram_id(self, telegram_id: str) -> User | None:
        try:
            return await sync_to_async(User.objects.get)(telegram_id=telegram_id)
        except User.DoesNotExist:
            return None

    async def create(self, user_data: dict) -> User:
        return await sync_to_async(User.objects.create)(**user_data)
```

**Performance**: Always use `select_related()` and `prefetch_related()` for ForeignKey relationships to avoid N+1 queries:

```python
# ✅ Good - Prefetch related data
async def get_by_user_and_reward(self, user_id: str, reward_id: str):
    return await sync_to_async(
        RewardProgress.objects.select_related('user', 'reward').get
    )(user_id=user_id, reward_id=reward_id)

# ❌ Bad - Causes N+1 queries
async def get_by_user_and_reward(self, user_id: str, reward_id: str):
    return await sync_to_async(RewardProgress.objects.get)(
        user_id=user_id, reward_id=reward_id
    )
    # Accessing progress.reward.pieces_required triggers extra query!
```

### Django Model Instantiation Pattern

**CRITICAL**: Always pass dictionaries to repository `create()` methods instead of instantiating Django model objects directly.

```python
# ✅ Good - Pass dict to repository
progress = await self.progress_repo.create({
    'user_id': user_id,
    'reward_id': reward_id,
    'pieces_earned': 0,
    'claimed': False
})

# ❌ Bad - Don't instantiate models in services
from src.core.models import RewardProgress
progress = RewardProgress(user_id=user_id, reward_id=reward_id)  # Avoid this!
```

**Auto-set Fields** (Never pass these to create()):
- `timestamp` fields with `auto_now_add=True`
- `updated_at` fields with `auto_now=True`
- `date_joined` field from `AbstractUser`
- Fields with `default` values (can be omitted)

**Django User Model Field Mappings**:
```python
# Old Airtable field → New Django field
'active' → 'is_active'           # BooleanField from AbstractUser
'created_at' → 'date_joined'     # DateTimeField from AbstractUser
```

### Computed Values Pattern

**Use regular methods instead of `@property` for computed values.** This provides better async compatibility.

**RewardProgress Computed Methods**:
- `get_status()` - Returns RewardStatus (CLAIMED, ACHIEVED, or PENDING)
- `get_pieces_required()` - Gets pieces_required from linked reward
- `get_progress_percent()` - Calculates percentage completion (0-100)
- `get_status_emoji()` - Extracts emoji from status value

```python
# ✅ Good - Use method calls
if progress.get_status() == RewardStatus.ACHIEVED:
    pieces_needed = progress.get_pieces_required()
    percent = progress.get_progress_percent()

# ❌ Bad - Properties no longer exist
if progress.status == RewardStatus.ACHIEVED:  # AttributeError!
```

**Important**: Always use `select_related('reward')` when querying RewardProgress to avoid N+1 queries when calling `get_pieces_required()`.

### Async-Safe ForeignKey Access Pattern

**CRITICAL**: Django model methods that access ForeignKey relationships MUST NOT trigger synchronous database queries when called from async contexts.

**The Problem**: When a Django model method accesses a ForeignKey field (e.g., `self.reward.pieces_required`), it triggers a database query if the related object is not loaded. In async contexts, this causes `SynchronousOnlyOperation` errors.

**The Solution - Cache ForeignKey Values**:

1. **In Repository Methods**: After fetching objects with `select_related()`, cache the needed FK values:

```python
# In RewardProgressRepository
@staticmethod
def _attach_cached_pieces_required(progress: RewardProgress) -> RewardProgress:
    """Attach cached pieces_required to avoid ForeignKey access in async contexts."""
    if progress and hasattr(progress, 'reward'):
        progress._cached_pieces_required = progress.reward.pieces_required
    return progress

async def get_by_user_and_reward(self, user_id, reward_id):
    progress = await sync_to_async(
        RewardProgress.objects.select_related('reward').get
    )(user_id=user_id, reward_id=reward_id)
    return self._attach_cached_pieces_required(progress)
```

2. **In Model Methods**: Use the cached value instead of accessing the ForeignKey:

```python
# ✅ Good - Async-safe pattern
class RewardProgress(models.Model):
    def get_status(self):
        pieces_required = self._get_pieces_required_safe()
        if self.pieces_earned >= pieces_required:
            return self.RewardStatus.ACHIEVED

    def _get_pieces_required_safe(self):
        # Check for cached value first
        if hasattr(self, '_cached_pieces_required'):
            return self._cached_pieces_required

        # Check if FK is loaded in Django's cache
        if hasattr(self, '_state') and 'reward' in self._state.fields_cache:
            return self.reward.pieces_required

        # Fallback with clear error message
        raise ValueError(
            "RewardProgress requires reward to be prefetched or cached"
        )
```

**Why This Works**: Repository methods access ForeignKeys inside `sync_to_async()` wrappers (sync context), cache values as simple attributes, then model methods access cached attributes (no DB query).

## Service Layer

Business logic lives in services (`src/services/`):
- `habit_service.py` - Orchestrates habit completion flow
- `streak_service.py` - Calculates streaks
- `reward_service.py` - Handles reward selection and cumulative progress
- `nlp_service.py` - NLP-based habit classification (optional)
- `audit_log_service.py` - Bot interaction audit trail

Services coordinate between repositories and contain no direct database calls.

### Multi-User Service Pattern

**CRITICAL**: After implementing multi-user support, many service methods now require `user_id` as a parameter. All handlers MUST pass the user ID when calling these methods.

**Affected methods:**
- `habit_service.get_all_active_habits(user_id)` - Requires user_id
- `habit_service.get_active_habits_pending_for_today(user_id)` - Requires user_id
- `habit_service.get_habit_by_name(user_id, habit_name)` - Requires user_id

**Pattern when user object is available:**
```python
user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
if not user:
    await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
    return

habits = await maybe_await(habit_service.get_all_active_habits(user.id))
```

**Pattern when only telegram_id is available:**
```python
# Get user for multi-user support
user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
if not user:
    logger.error(f"❌ User {telegram_id} not found")
    await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
    return

habits = await maybe_await(habit_service.get_all_active_habits(user.id))
```

**Why**: Without user_id, service methods will fail with `TypeError: missing 1 required positional argument: 'user_id'`. This happens because the system now supports multiple users, and data must be filtered by user.

### NLP Service Optional Pattern

The NLP service is optional and gracefully degrades when LLM_API_KEY is not configured:

```python
class NLPService:
    def __init__(self):
        self.enabled = False
        self.client = None

        if not settings.LLM_API_KEY:
            logger.warning("⚠️ LLM_API_KEY not configured. NLP disabled.")
            return

        try:
            self.client = OpenAI(api_key=settings.LLM_API_KEY)
            self.enabled = True
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize client: {e}")
            return

    def classify_habit_from_text(self, user_text: str, available_habits: list[str]) -> list[str]:
        if not self.enabled or not self.client:
            return []  # Return empty list when disabled
        # Normal classification logic...
```

### Streak Service Pattern

The `StreakService` has two distinct methods:

1. **`calculate_streak(user_id, habit_id)`** - Used when LOGGING a new habit
   - Returns what the NEXT streak will be after logging
   - If `last_completed_date == yesterday`: increments streak
   - If `last_completed_date == today`: returns current streak
   - If `last_completed_date < yesterday`: applies flexible streak logic (see below)

2. **`get_current_streak(user_id, habit_id)`** - Used when DISPLAYING current streak
   - Returns the CURRENT streak from the most recent log
   - Does NOT increment or calculate - just retrieves stored value

**Why Two Methods?**: Using `calculate_streak()` for display caused incorrect results when viewing streaks on Day 2 (habits not done today were incorrectly incremented).

### Flexible Streak Tracking (Feature 0017)

**CRITICAL**: Streaks now support grace days and exempt weekdays for more flexible tracking.

**Habit Fields**:
- `allowed_skip_days` (Integer, default=0): Number of consecutive days user can skip without breaking streak
- `exempt_weekdays` (JSONField, default=[]): List of weekday numbers (1=Mon, 7=Sun) that don't count against streak

**Streak Calculation Algorithm**:
1. If `last_date == today`: return current streak
2. If `last_date == yesterday`: return current streak + 1
3. If gap > 1 day:
   - Calculate all dates in gap (exclusive)
   - For each date, get weekday using `date.isoweekday()` (1=Mon, 7=Sun)
   - Filter out dates that fall on `exempt_weekdays`
   - Count remaining "missed" days
   - If `missed_days <= allowed_skip_days`: **preserve streak** (return current + 1)
   - Otherwise: **break streak** (return 1)

**Example**: Habit with weekends exempt (6=Sat, 7=Sun), last done Friday, today is Monday
- Gap: Saturday, Sunday
- Weekdays: 6, 7
- Both exempt → missed_days = 0
- Result: Streak preserved ✅

**Bot UI Flow** (Add/Edit Habit):
- User selects grace days (0, 1, 2, or 3)
- User selects exempt days (None or Weekends)
- Settings displayed in confirmation

**Implementation Notes**:
- Weekday numbering: 1=Monday, 7=Sunday (Python's `isoweekday()`)
- Exempt weekends stored as `[6, 7]` in database
- Both fields are **always required** when creating/editing habits

## Import Pattern

When importing repositories, always use:
```python
from src.core.repositories import user_repository, habit_repository, ...
```

These are singleton instances defined at the bottom of the repository file.

## Django Transactions

**CRITICAL**: Use Django transactions for operations that require multiple database changes to succeed or fail atomically.

```python
from django.db import transaction
from asgiref.sync import sync_to_async

async def atomic_operation():
    def _transaction():
        with transaction.atomic():
            # All operations inside this block are atomic
            habit_log = HabitLog.objects.get(id=log_id)
            habit_log.delete()

            # Update related records
            progress = RewardProgress.objects.get(id=progress_id)
            progress.pieces_earned -= 1
            progress.save()

            # If any operation fails, ALL changes are rolled back

    await sync_to_async(_transaction)()
```

### When to Use Transactions

1. **Deleting records with side effects** (e.g., reverting habit completion)
2. **Creating multiple related records** (e.g., user + initial settings)
3. **Updating multiple tables** that must stay consistent
4. **Financial operations** (e.g., claiming rewards with monetary value)

### Habit Completion Transaction Pattern

**CRITICAL**: Habit completion operations MUST wrap both reward progress updates and habit log creation in an atomic transaction.

```python
# Wrap both operations in atomic transaction
async with self._atomic():
    reward_progress = None
    if got_reward:
        # Update reward progress
        reward_progress = await maybe_await(
            self.reward_service.update_reward_progress(
                user_id=user.id,
                reward_id=selected_reward.id,
            )
        )

    # Create habit log
    habit_log = HabitLog(...)
    await maybe_await(self.habit_log_repo.create(habit_log))
```

**Why**: Without atomic transaction, you can get orphaned progress entries (0 pieces, no logs) if one operation succeeds but the other fails.

### Reward Progress Validation Notes

**IMPORTANT**: Do NOT validate `pieces_earned` by counting total HabitLogs for recurring multi-piece rewards.

**Why HabitLog count ≠ pieces_earned**: For recurring rewards (rewards that reset after claiming), HabitLogs accumulate across ALL cycles, while RewardProgress tracks only the CURRENT cycle.

**Example**: "MacBook Pro" (10 pieces required)
- Cycle 1: User earns 10 pieces → claims → pieces_earned=0, claimed=True
- Cycle 2: User earns 3 pieces → pieces_earned=3
- HabitLogs: 13 total (across all cycles)
- ✅ `pieces_earned=3` is CORRECT (current cycle)
- ❌ Counting total HabitLogs (13) would be WRONG

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_bot_handlers.py -v

# Run with coverage
uv run pytest --cov=src tests/
```

### Testing Bot Handlers Pattern

Use `@patch` to mock repositories and Telegram objects:

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User as TelegramUser

@pytest.fixture
def mock_telegram_update():
    """Create mock Telegram update."""
    telegram_user = TelegramUser(id=999999999, first_name="Test", is_bot=False)
    message = Mock(spec=Message)
    message.reply_text = AsyncMock()

    update = Mock(spec=Update)
    update.effective_user = telegram_user
    update.message = message
    return update

@pytest.mark.asyncio
@patch('src.bot.main.user_repository')
async def test_start_command_user_not_found(mock_user_repo, mock_telegram_update):
    """Test TC1.1: User not found."""
    mock_user_repo.get_by_telegram_id.return_value = None

    await start_command(mock_telegram_update, context=None)

    mock_telegram_update.message.reply_text.assert_called_once_with(
        "❌ User not found. Please contact admin to register."
    )
```

### Local-Only Tests

Some tests are marked with `@pytest.mark.local_only` to prevent execution in CI/CD:

```python
@pytest.mark.local_only
@pytest.mark.asyncio
async def test_audit_log_feature():
    """This test ONLY runs locally, never in GitHub Actions."""
    # Test implementation...
```

**Running tests:**
```bash
# Local: Run ALL tests (including local_only)
uv run pytest tests/ -v

# CI behavior: Skip local_only tests
uv run pytest tests/ -v -m "not local_only"
```

**Why local-only tests?**: Complex integration tests, long-running tests, or tests for experimental features.

## Unified Reward System

**CRITICAL**: All rewards use a unified cumulative approach. There is no distinction between "cumulative" and "non-cumulative" rewards.

### Core Concepts

**All rewards track progress with `pieces_required`**:
- Instant rewards: `pieces_required = 1`
- Multi-piece rewards: `pieces_required > 1`

**3-State Status Workflow**:
1. **🕒 Pending**: `pieces_earned < pieces_required` - User is making progress
2. **⏳ Achieved**: `pieces_earned >= pieces_required && !claimed` - Ready to claim
3. **✅ Claimed**: `claimed == true` - User has claimed the reward

**Status is fully computed in Python** via the `get_status()` method - Never set status manually.

### Service Layer Pattern

```python
# Always use update_reward_progress() for ANY reward
reward_progress = reward_service.update_reward_progress(
    user_id=user.id,
    reward_id=reward.id
)

# When user claims a reward
reward_service.mark_reward_claimed(user_id, reward_id)
# This resets pieces_earned to 0 and sets claimed=True
```

**Key methods**:
- `update_reward_progress()` - Increments pieces_earned with smart status handling:
  - **ACHIEVED status**: Will NOT increment (prevents over-counting)
  - **CLAIMED status**: Resets `claimed=False` first, then increments
  - **PENDING status**: Increments normally
- `mark_reward_claimed()` - Resets pieces_earned to 0 and sets claimed=True

**Proper reward cycle**:
1. **Pending** (0/N) → User earns pieces → **Pending** (1/N, 2/N, etc.)
2. **Achieved** (N/N) → User cannot earn more (counter frozen)
3. **User claims** → `mark_reward_claimed()` → **Claimed** (0/N)
4. **User earns next piece** → Resets claimed=False → **Pending** (1/N)
5. Cycle repeats

### Daily Frequency Control

**Field**: `Reward.max_daily_claims`
- `NULL` or `0` = unlimited (can be awarded multiple times per day)
- `1` = once per day maximum
- `2+` = that many pieces per day maximum

**Key Behaviors**:
1. **Piece-based counting**: Daily limit counts individual PIECES awarded, not completions
2. **ALL pieces count**: Counts ALL pieces awarded today (claimed AND unclaimed)
3. **Lottery exclusion**: Rewards at daily limit are excluded from selection
4. **Completion blocking**: Rewards already completed (pieces_earned >= pieces_required) are also excluded

**Implementation**:
- `get_todays_pieces_by_reward(user_id, reward_id)`: Counts ALL pieces awarded today
- `select_reward()`: Filters out completed rewards and rewards at daily limit
- `mark_reward_claimed()`: Resets `pieces_earned=0` when claiming

**Example**: `max_daily_claims=1`, `pieces_required=5`
- Day 1: Earn 1 piece → 1/5 (cannot earn more today)
- Day 2: Earn 1 piece → 2/5 (cannot earn more today)
- ...takes 5 days minimum to complete

## Caddy Deployment (Simplified)

**Architecture**: 2 containers (Web + Caddy)
- **Web**: Django + Telegram Bot + SQLite
- **Caddy**: Automatic HTTPS reverse proxy

**Key Benefits**:
- Automatic SSL (no certbot needed)
- Simple 15-line Caddyfile
- SQLite database (easy backups)
- Bind mounts for data persistence

**Files**:
- `deployment/caddy/Caddyfile` - Caddy configuration
- `deployment/docker/docker-compose.caddy.yml` - 2-service compose
- `.github/workflows/deploy-caddy.yml` - Automated CI/CD

**Deployment**:
```bash
# First-time
cd /home/deploy/habit_reward_bot
mkdir -p data staticfiles
cd docker
docker-compose --env-file ../.env -f docker-compose.caddy.yml up -d

# Updates (automatic via GitHub Actions)
git push origin main
```

**Data Persistence**:
```yaml
volumes:
  - ./data:/app/data              # SQLite database
  - ./staticfiles:/app/staticfiles
```

**Database Location**: `/home/deploy/habit_reward_bot/data/db.sqlite3`

**Backup**: `cp data/db.sqlite3 backups/db_$(date +%Y%m%d).sqlite3`

**SSL**: Fully automatic - Caddy obtains and renews certificates (no manual intervention).

### Security: Domain Blocking

Caddy catch-all block rejects all requests except legitimate domains:

```caddy
# Your legitimate domains first
habitreward.org { ... }

# Catch-all MUST come last
:80, :443 {
    respond "Domain not configured" 444
    log {
        output file /var/log/caddy/blocked.log
    }
}
```

Blocks: Direct IP access, unknown domains, router exploits, domain fronting.

## Bot Audit Logging

**CRITICAL**: All high-level Telegram bot interactions are logged to `BotAuditLog` model for debugging and user support.

### When to Use Audit Logging

Log these high-level events via `audit_log_service`:
1. **Commands** - User executes bot commands
2. **Habit Completions** - User completes habit and earns reward
3. **Reward Claims** - User claims achieved reward
4. **Reward Reverts** - Habit completion reverted
5. **Button Clicks** - Significant state changes only
6. **Errors** - Exceptions during user interactions

**Do NOT log**: Low-level operations, database queries, intermediate states.

### Implementation

```python
from src.services.audit_log_service import audit_log_service
from src.utils.async_compat import maybe_await

# Log command
await maybe_await(
    audit_log_service.log_command(
        user_id=user.id,
        command="/start",
        snapshot={"language": lang}
    )
)

# Log habit completion
await maybe_await(
    audit_log_service.log_habit_completion(
        user_id=user.id,
        habit=habit,
        reward=selected_reward if got_reward else None,
        habit_log=habit_log,
        snapshot={
            "habit_name": habit.name,
            "streak_count": streak_count,
            "selected_reward_name": selected_reward.name if got_reward else None,
            "reward_progress": {
                "pieces_earned": progress.pieces_earned,
                "pieces_required": progress.get_pieces_required(),
            } if progress else None
        }
    )
)

# Log errors
await maybe_await(
    audit_log_service.log_error(
        user_id=user.id,
        error_message=f"Error claiming reward: {str(e)}",
        context={"command": "claim_reward", "reward_id": reward_id}
    )
)
```

### Querying Audit Logs

```python
# Get user's event timeline (last 24 hours)
timeline = await maybe_await(
    audit_log_service.get_user_timeline(user_id=user.id, hours=24)
)

# Trace reward corruption
events = await maybe_await(
    audit_log_service.trace_reward_corruption(
        user_id=user.id,
        reward_id=reward.id
    )
)
```

**Django Admin**: Logs accessible at `/admin/core/botauditlog/` (read-only, filterable by event type/date).

**Retention**: 90 days (automatic cleanup via `python manage.py cleanup_audit_logs`).

**Why**: Trace data corruption, reconstruct user interactions, debug issues with state snapshots.

## Django Admin Custom Actions

**CRITICAL**: Django admin runs in WSGI (synchronous) context. Never use `asyncio.run()` or async service layer methods in admin actions.

### Async/Sync Context Issue

**Problem**: Our services use async methods (via `run_sync_or_async()`), but Django admin actions run in synchronous WSGI context. Using `asyncio.run()` causes:
```
RuntimeError: You cannot submit onto CurrentThreadExecutor from its own thread
```

**Solution**: Use pure Django ORM in admin actions instead of calling async services.

```python
# ❌ Bad - Causes CurrentThreadExecutor error
@admin.action(description='Revert selected habit logs')
def revert_selected_logs(self, request, queryset):
    for log in queryset:
        # Don't do this!
        asyncio.run(habit_service.revert_habit_completion(
            user_telegram_id=log.user.telegram_id,
            habit_id=log.habit.id
        ))

# ✅ Good - Use synchronous Django ORM
@admin.action(description='Revert selected habit logs')
def revert_selected_logs(self, request, queryset):
    from django.db import transaction

    for log in queryset:
        with transaction.atomic():
            # Direct Django ORM operations
            user = log.user
            habit = log.habit
            reward = log.reward

            # Delete log
            log.delete()

            # Update related records if needed
            if reward:
                progress = RewardProgress.objects.get(user=user, reward=reward)
                progress.pieces_earned -= 1
                progress.save()

            # Create audit log
            BotAuditLog.objects.create(
                user=user,
                event_type=BotAuditLog.EventType.HABIT_REVERTED,
                habit=habit,
                reward=reward,
                snapshot={...}
            )
```

### Consistency with Bot Actions

**CRITICAL**: When creating admin actions that mirror bot functionality (e.g., habit reversion), ensure consistent audit logging.

**Key requirements**:
1. Use the same event type (e.g., `HABIT_REVERTED` not `REWARD_REVERTED`)
2. Populate the same fields (both `habit` and `reward`)
3. Always create audit logs (not conditionally based on reward existence)
4. Use the same business logic for related updates (e.g., reward progress decrement)

**Example**: The "Revert selected habit logs" admin action creates audit logs identical to the `/revert_habit` bot command.

### Admin Action Best Practices

1. **Prefetch Related Objects**: Use `select_related()` to avoid N+1 queries
   ```python
   queryset = queryset.select_related('user', 'habit', 'reward')
   ```

2. **Use Transactions**: Wrap multi-step operations in `transaction.atomic()`

3. **Validate Data**: Check for required relationships before processing
   ```python
   if not log.user or not log.habit:
       error_messages.append(f"Log #{log.id}: Missing required data")
       continue
   ```

4. **Provide User Feedback**: Use Django messages framework
   ```python
   self.message_user(
       request,
       f"Successfully processed {count} records.",
       messages.SUCCESS
   )
   ```

5. **Handle Errors Gracefully**: Track success/failure counts and show detailed errors
   ```python
   success_count = 0
   failed_count = 0
   error_messages = []

   for item in queryset:
       try:
           # Process...
           success_count += 1
       except Exception as e:
           failed_count += 1
           error_messages.append(f"Item #{item.id}: {str(e)}")
   ```

### Event Type Enum Usage

**CRITICAL**: Always use enum constants for event types, never strings.

```python
# ✅ Good - Type-safe enum
BotAuditLog.objects.create(
    event_type=BotAuditLog.EventType.HABIT_REVERTED,
    ...
)

# ❌ Bad - Typos cause NULL values in database
BotAuditLog.objects.create(
    event_type='habit_revert',  # Typo! Field will be NULL
    ...
)
```

**Why**: Django's `TextChoices` validates enum values. Invalid strings are silently rejected, resulting in NULL database values.
