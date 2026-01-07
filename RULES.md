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

## Django Initialization for Entry Points

**CRITICAL**: Any entry point (script, Streamlit app, bot main) that imports from `src.core.repositories` or `src.core.models` MUST configure Django before those imports.

Django models require `DJANGO_SETTINGS_MODULE` to be set and `django.setup()` to be called before any Django modules are imported. Without this, you'll get `django.core.exceptions.ImproperlyConfigured`.

**Required Pattern**:
```python
"""Entry point script."""
# ruff: noqa: E402

import os
import django

# Configure Django before any imports that use Django models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')
django.setup()

# Now safe to import Django-dependent modules
from src.core.repositories import user_repository
from src.config import settings
```

**Files that require this**:
- `src/dashboard/app.py` - Streamlit dashboard entry point
- `src/bot/main.py` - Telegram bot polling mode entry point
- Any standalone script that uses repositories

**Note**: The `# ruff: noqa: E402` comment is required because we're importing Django setup code before other imports, which violates PEP 8's import ordering rule. This is intentional and necessary.

**Why**: The `src.core.repositories` module imports Django models (`from src.core.models import ...`), and Django models cannot be imported until Django is configured. This initialization must happen at the very top of the entry point file, before any other imports that might transitively import Django models.

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

### Date Formatting Standard

**CRITICAL**: All user-facing dates MUST use the format **"09 Dec 2025"** (format string: `"%d %b %Y"`).

```python
from datetime import date

# ✅ Good - Standard format
target_date = date(2025, 12, 9)
date_display = target_date.strftime("%d %b %Y")  # "09 Dec 2025"

# ❌ Bad - Don't use verbose format
date_display = target_date.strftime("%B %d, %Y")  # "December 09, 2025"

# ❌ Bad - Don't show ISO format to users
date_display = str(target_date)  # "2025-12-09"
```

**Why this format?**:
- **Concise**: Takes less screen space on mobile
- **International**: Day-first format is more globally recognized
- **Unambiguous**: 3-letter month abbreviation (Dec) is clear in all languages
- **Consistent**: Same format across all success/error messages

**Where to apply**:
- Habit completion success messages
- Backdate confirmations
- Duplicate entry error messages
- Date picker displays
- Any user-visible date output

**Implementation locations**:
- `src/bot/handlers/menu_handler.py` - Menu flow handlers
- `src/bot/handlers/habit_done_handler.py` - Habit completion handlers
- `src/bot/handlers/backdate_handler.py` - Backdate flow handlers

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
- `category` (CharField, optional, null=True): Category field for analytical purposes. **NOT managed via Telegram** (Feature 0024). Habits created via Telegram have `category=None`. Category remains available via REST API and Django admin for external clients.

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
- User enters habit name
- User selects weight (10-100)
- User selects grace days (0, 1, 2, or 3)
- User selects exempt days (None or Weekends)
- Settings displayed in confirmation
- **Note**: Category selection was removed from Telegram in Feature 0024. The flow previously included category selection but this was simplified for better UX.

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

## Code Quality & Linting

**CRITICAL**: All code must pass the linting checks before committing.

### Linting Requirements

Run linting check:
```bash
uv run ruff check src/
```

Fix common issues automatically:
```bash
uv run ruff check src/ --fix
```

### Common Linting Issues

1. **Unused Imports**: Remove all unused imports
   ```python
   # ❌ Bad
   from fastapi import Depends, Header  # Header not used

   # ✅ Good
   from fastapi import Depends
   ```

2. **Ambiguous Variable Names**: Avoid single letters that look like numbers (especially `l`, `O`, `I`)
   ```python
   # ❌ Bad - looks like number 1
   habit_logs = [l for l in logs if l.habit_id == habit_id]

   # ✅ Good
   habit_logs = [log for log in logs if log.habit_id == habit_id]
   ```

3. **Whitespace & Formatting**: Follow PEP 8 standards (handled by ruff --fix)

### Before Committing

Always run:
```bash
uv run ruff check src/
```

Ensure output shows: `All checks passed!`

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

### Piece Value (`piece_value`) Field

The `Reward.piece_value` field is optional metadata used for analytics and dashboard views (e.g., total monetary value of earned rewards). It SHOULD NOT be managed through the Telegram bot reward flows for now:

- ADD_REWARD and EDIT_REWARD command flows MUST NOT prompt the user to enter or edit any "piece price" / `piece_value` value.
- When creating or editing rewards from the bot, rely on the model default (`NULL`/`None`) for `piece_value` unless explicitly set by backend/admin or API flows.
- Future features may re-enable editing `piece_value` via bot or dashboard; keep implementation flexible but do not expose this field in current Telegram UX.

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

## Django Admin Configuration

### Displaying ID Fields in Details View

To show the primary key (ID) field in Django admin details view:
1. Add `'id'` to `readonly_fields` (primary keys are read-only)
2. Add `'id'` to the appropriate fieldset (typically first field in the first fieldset)

**Example** (`src/core/admin.py`):
```python
@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Habit Information', {
            'fields': ('id', 'user', 'name', 'weight', 'category', 'active')
        }),
        # ...
    )
```

**Why**: ID fields are useful for debugging, API references, and cross-referencing records.

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

## Backdate Habit Completion Pattern

**Feature**: Allows users to log habits for past dates (up to 7 days back) through the Telegram bot.

### Implementation Architecture

**Three-layer approach**:

1. **Repository Layer** (`src/core/repositories.py`):
   - `get_log_for_habit_on_date()` - Check for duplicate completions on specific date
   - `get_logs_for_habit_in_daterange()` - Get completions within date range (for calendar view)

2. **Service Layer**:
   - `HabitService.process_habit_completion(target_date=None)` - Accepts optional target_date parameter
   - `StreakService.calculate_streak_for_date()` - Calculate streak for specific past date
   - `HabitService.get_habit_completions_for_daterange()` - Get completion dates for calendar display

3. **Bot Handler Layer** (`src/bot/handlers/backdate_handler.py`):
   - ConversationHandler with three states: SELECTING_HABIT → SELECTING_DATE → CONFIRMING_COMPLETION
   - Entry points: `/backdate` command or callback from other handlers

### Key Design Decisions

**HabitLog Model Fields**:
- `timestamp` (auto_now_add) - When the log was created (always "now")
- `last_completed_date` (DateField) - The actual completion date (can be backdated)

**Why separate fields?**: Allows audit trail (when logged) while supporting backdating (when completed).

**Validation Rules** (7-day limit):
```python
# In HabitService.process_habit_completion()
max_backdate_days = 7
earliest_allowed = today - timedelta(days=max_backdate_days)

if target_date > today:
    raise ValueError("Cannot log habits for future dates")
if target_date < earliest_allowed:
    raise ValueError(f"Cannot backdate more than {max_backdate_days} days")
if target_date < habit.created_at.date():
    raise ValueError("Cannot backdate before habit was created")
```

**Duplicate Prevention**:
```python
existing_log = await self.habit_log_repo.get_log_for_habit_on_date(
    user.id, habit.id, target_date
)
if existing_log:
    raise ValueError(f"Habit already completed on {target_date}")
```

### Streak Calculation for Backdating

**Two methods in StreakService**:

1. `calculate_streak()` - For today's completions (normal flow)
2. `calculate_streak_for_date()` - For backdated completions (checks gap between last completion and target date)

**Why two methods?**: Backdating into the middle of existing logs requires different logic than appending to the end.

### UI/UX Patterns

**Date Picker Keyboard** (`build_date_picker_keyboard()`):
- Shows 7-day calendar (today and 6 days back)
- Displays checkmarks (✓) on dates that already have completions
- Dates with completions have different callback_data (disabled)
- Organized in rows of 4 buttons

**Confirmation Flow**:
1. Select habit
2. Select date from calendar
3. Confirm with preview: "Log {habit} for {date}?"
4. Process completion

### Error Handling

**User-friendly error mapping** in `confirm_backdate_completion()`:
```python
try:
    result = await habit_service.process_habit_completion(
        user_telegram_id=telegram_id,
        habit_name=habit_name,
        target_date=target_date
    )
except ValueError as e:
    # Map service errors to localized user messages
    if "already completed" in str(e).lower():
        msg('ERROR_BACKDATE_DUPLICATE', lang, ...)
    elif "future date" in str(e).lower():
        msg('ERROR_BACKDATE_FUTURE', lang)
    # ... etc
```

**Why map errors?**: Service layer raises generic ValueError with technical messages; handlers convert to user-friendly localized messages.

### Multi-lingual Support

**All backdate messages** in `src/bot/messages.py` with translations:
- `HELP_BACKDATE_SELECT_HABIT`
- `HELP_BACKDATE_SELECT_DATE`
- `HELP_BACKDATE_CONFIRM`
- `SUCCESS_BACKDATE_COMPLETED`
- `ERROR_BACKDATE_DUPLICATE`
- `ERROR_BACKDATE_TOO_OLD`
- `ERROR_BACKDATE_FUTURE`
- `ERROR_BACKDATE_BEFORE_CREATED`
- `BUTTON_TODAY`, `BUTTON_YESTERDAY`, `BUTTON_SELECT_DATE`

**Supported languages**: English, Russian, Kazakh

### Context Management Pattern

**Store intermediate state in `context.user_data`**:
```python
# Store after habit selection
context.user_data['backdate_habit_id'] = habit_id
context.user_data['backdate_habit_name'] = habit.name

# Retrieve when confirming
habit_name = context.user_data.get('backdate_habit_name')
target_date = context.user_data.get('backdate_date')

# Clean up on completion/cancellation
context.user_data.pop('backdate_habit_id', None)
context.user_data.pop('backdate_habit_name', None)
context.user_data.pop('backdate_date', None)
```

**Why**: ConversationHandler states don't persist data between callbacks; use context.user_data for flow continuity.

### Known Limitations

**Streak Propagation**: When a past completion is inserted via backdating, the system DOES NOT recalculate streak counts for existing future logs. This means:

- **Example scenario**: User completes habit today (streak=1), then backdates same habit to yesterday
  - The backdated log gets streak=2 (correct, based on yesterday being consecutive)
  - Today's log KEEPS streak=1 (not recalculated)
  - This is intentional to avoid expensive cascading updates across all future logs

**Why this is acceptable**:
- The most recent log still shows the correct current streak via `get_current_streak()`
- Future completions will calculate correctly based on the most recent log
- Backdating is designed for filling missed entries, not reconstructing historical data

**Alternative considered**: Recalculating all logs after the backdated entry was deemed too complex and error-prone for the initial implementation. Future enhancement could add a "Recalculate Streaks" admin action if needed.

### Testing Considerations

**Manual test scenarios**:
1. Backdate to yesterday - should work
2. Backdate to 7 days ago - should work (boundary)
3. Backdate to 8 days ago - should fail (too old)
4. Backdate to future date - should fail
5. Backdate same habit twice on same date - should fail (duplicate)
6. Backdate before habit creation - should fail
7. Backdate fills gap in streak - streak should recalculate correctly (for the backdated entry)
8. Calendar should show checkmarks on completed dates
9. **Known limitation**: Existing future logs keep their old streak counts (see above)

**Unit test focus areas**:
- `get_log_for_habit_on_date()` - duplicate detection
- `get_last_log_before_date()` - querying logs before target date
- `calculate_streak_for_date()` - gap handling with grace days and exempt weekdays
- Validation logic in `process_habit_completion()`

## REST API (Feature 0022)

### Architecture

The REST API uses FastAPI alongside the existing Django application:

```
Mobile/Web Client
    ↓ HTTP/JSON
FastAPI REST API Layer (src/api/)
    ↓
Existing Service Layer (src/services/)
    ↓
Django ORM Repositories (src/core/repositories.py)
    ↓
PostgreSQL/SQLite
```

**Key Files**:
- `src/api/main.py` - FastAPI application factory
- `src/api/config.py` - API-specific settings (JWT, CORS)
- `src/api/dependencies/auth.py` - JWT authentication
- `src/api/v1/routers/` - Versioned API endpoints
- `asgi.py` - Combined ASGI entry point for Django + FastAPI

### Running the API

```bash
# Development
uvicorn asgi:app --reload --port 8000

# Access API docs
# http://localhost:8000/api/docs (Swagger UI)
# http://localhost:8000/api/redoc (ReDoc)
```

### JWT Authentication Pattern

**Token Flow**:
1. Client calls `POST /api/v1/auth/login` with `telegram_id`
2. Server returns `access_token` (15min) + `refresh_token` (7 days)
3. Client includes `Authorization: Bearer <access_token>` header
4. When access token expires, call `POST /api/v1/auth/refresh`

**Token Payload**:
```json
{
  "sub": "user_id",
  "telegram_id": "123456789",
  "exp": 1234567890,
  "type": "access"
}
```

**Using Authentication Dependency**:
```python
from typing import Annotated
from fastapi import Depends
from src.api.dependencies.auth import get_current_active_user
from src.core.models import User

@router.get("/protected")
async def protected_route(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    # current_user is the authenticated, active User instance
    return {"user_id": current_user.id}
```

### API Router Pattern

All routers follow consistent patterns:

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api.dependencies.auth import get_current_active_user
from src.api.exceptions import NotFoundException, ForbiddenException

router = APIRouter()

class ItemResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True  # Enable ORM mode

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> ItemResponse:
    item = await maybe_await(item_repository.get_by_id(item_id))

    if item is None:
        raise NotFoundException(message=f"Item {item_id} not found")

    if item.user_id != current_user.id:
        raise ForbiddenException(message="Access denied")

    return ItemResponse(id=item.id, name=item.name)
```

### Exception Handling

Use custom exceptions that map to HTTP status codes:

```python
from src.api.exceptions import (
    UnauthorizedException,  # 401
    ForbiddenException,     # 403
    NotFoundException,      # 404
    ConflictException,      # 409
    ValidationException,    # 422
)

# All exceptions return standardized JSON:
{
    "error": {
        "code": "HABIT_NOT_FOUND",
        "message": "Habit 'Running' not found",
        "details": {}
    }
}
```

### API Endpoint Summary

**Authentication** (`/api/v1/auth`):
- `POST /login` - Login with telegram_id
- `POST /refresh` - Refresh access token
- `POST /logout` - Logout

**Users** (`/api/v1/users`):
- `GET /me` - Get current user
- `PATCH /me` - Update user profile
- `GET /me/settings` - Get user settings

**Habits** (`/api/v1/habits`):
- `GET /` - List habits
- `GET /{id}` - Get habit
- `POST /` - Create habit
- `PATCH /{id}` - Update habit
- `DELETE /{id}` - Soft delete habit
- `POST /{id}/complete` - Complete habit
- `POST /batch-complete` - Complete multiple habits

**Habit Logs** (`/api/v1/habit-logs`):
- `GET /` - List logs (with date filters)
- `GET /{id}` - Get log
- `DELETE /{id}` - Revert completion

**Rewards** (`/api/v1/rewards`):
- `GET /` - List rewards with progress
- `GET /progress` - Get all progress
- `GET /{id}` - Get reward with progress
- `POST /` - Create reward
- `PATCH /{id}` - Update reward
- `DELETE /{id}` - Delete reward
- `POST /{id}/claim` - Claim achieved reward

**Streaks** (`/api/v1/streaks`):
- `GET /` - Get all habit streaks
- `GET /{habit_id}` - Get habit streak detail

### Configuration

API settings in `.env`:

```bash
# JWT Configuration
API_SECRET_KEY=your-secret-key-here  # Auto-generated if not set
API_ACCESS_TOKEN_EXPIRE_MINUTES=15
API_REFRESH_TOKEN_EXPIRE_DAYS=7
API_ALGORITHM=HS256

# CORS
API_CORS_ORIGINS=https://yourfrontend.com,https://app.example.com
```

### Testing API Endpoints

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "123456789"}'

# Use access token
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"

# Complete a habit
curl -X POST http://localhost:8000/api/v1/habits/1/complete \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"target_date": "2025-12-10"}'
```

## REST API Implementation (Feature 0022)

### Architecture Overview

The REST API layer is in `src/api/` with the following structure:

```
src/api/
├── main.py                 # FastAPI app factory
├── config.py              # API configuration (JWT, CORS)
├── exceptions.py          # Custom exception handlers
├── dependencies/
│   └── auth.py            # JWT utilities and auth dependencies
├── middleware/
│   ├── logging.py         # Request ID and timing logging
│   └── rate_limiting.py   # Optional rate limiting (Phase 3)
└── v1/
    └── routers/
        ├── auth.py        # Login, refresh, logout
        ├── users.py       # User profile and settings
        ├── habits.py      # Habit CRUD and completion
        ├── rewards.py     # Reward CRUD and claiming
        ├── habit_logs.py  # Habit log history and revert
        └── streaks.py     # Streak information
```

### Key Implementation Notes

**Authentication**: JWT-based with access tokens (15 min) and refresh tokens (7 days). All protected endpoints require `Authorization: Bearer <token>` header.

**Endpoints**: 27 endpoints across 6 resource areas. Base path is `/v1/`. Health check available at `/health`.

**Error Responses**: Standardized format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

**Ownership Validation**: All endpoints validate that users can only access their own resources (habits, rewards, logs). Returns 403 Forbidden for cross-user access attempts.

### Known Critical Issues (From 0022_REVIEW.md)

**P0 - Critical (Fix Before Production):**

1. **Habit Log Revert Bug** (`src/api/v1/routers/habit_logs.py:214-218`)
   - Endpoint accepts `log_id` but calls `habit_service.revert_habit_completion()` with `habit_id`
   - This reverts the MOST RECENT log for that habit, not the requested log
   - If user has multiple logs for same habit, wrong one gets deleted
   - Fix: Modify service to accept `log_id` parameter

2. **JWT Secret Regenerates on Restart** (`src/api/config.py:11`)
   - If `API_SECRET_KEY` env var not set, new random key generated each restart
   - Invalidates all existing tokens on deployment
   - Fix: Require explicit `API_SECRET_KEY` or persist to file

**P1 - High (Fix Soon):**

3. **Broken Active Filter** (`src/api/v1/routers/habits.py:150-154`)
   - `GET /v1/habits?active=false` still returns only active habits
   - Both branches call same `get_all_active()` method
   - Fix: Add `get_all()` method to repository

4. **Inefficient Log Lookup** (`src/api/v1/routers/habit_logs.py:150-151`)
   - Fetches up to 1000 logs from DB just to find one by ID
   - O(n) instead of O(1) operation
   - Fix: Add `get_by_id()` method to `habit_log_repository`

### API Test Script

Comprehensive test suite at `scripts/test_api.sh`:
- 70+ test assertions across all endpoints
- Multi-user isolation testing
- Error scenario validation
- Edge case coverage

**Run with:**
```bash
# Start API server
uvicorn asgi:app --port 8000

# In another terminal
./scripts/test_api.sh
```

### Database Endpoint Locations (IMPORTANT!)

- API endpoints: `/v1/*` (e.g., `/v1/habits`)
- Health check: `/health` (NOT `/v1/health`)
- OpenAPI docs: `/docs`
- ReDoc: `/redoc`

### Token Blacklist Not Implemented

**Note**: The logout endpoint doesn't implement token blacklisting. Tokens remain valid until expiration (15 min for access, 7 days for refresh). This is noted as TODO in the code - implement with Redis for production.

### Future Work (Phase 3)

- Analytics endpoints (`/v1/analytics/*`)
- Rate limiting middleware
- API tests (`tests/api/`)
- Webhook notifications (optional)
