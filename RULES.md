# Development Rules & Patterns

## User Validation Pattern

**CRITICAL**: All Telegram bot command handlers MUST validate that the user exists and is active before processing any commands.

### Implementation Pattern

```python
# At the top of any handler function
telegram_id = str(update.effective_user.id)

# Validate user exists
user = user_repository.get_by_telegram_id(telegram_id)
if not user:
    await update.message.reply_text(
        "❌ User not found. Please contact admin to register."
    )
    return

# Check if user is active
if not user.active:
    await update.message.reply_text(
        "❌ Your account is not active. Please contact admin."
    )
    return
```

### Files Following This Pattern
- `src/bot/main.py` - `/start` and `/help` commands (lines 27-42, 61-76)
- `src/bot/handlers/streak_handler.py` - `/streaks` command (lines 18-21)
- `src/services/habit_service.py` - `process_habit_completion()` method (lines 65-68)

### Error Messages
Use consistent error messages across all handlers via message constants:
- **User not found**: `msg('ERROR_USER_NOT_FOUND', lang)`
- **User inactive**: `msg('ERROR_USER_INACTIVE', lang)`

See `src/bot/messages.py` for all available message constants.

### Why This Matters
- Prevents crashes when non-registered users try to use the bot
- Enforces business logic (only active users can log habits and earn rewards)
- Provides clear, user-friendly error messages
- Ensures TC1.1 and TC1.3 test cases pass

## Message Management & Multi-lingual Support

**CRITICAL**: All user-facing strings MUST use message constants from `src/bot/messages.py`. Never use hardcoded strings in handlers or formatters.

### Implementation Pattern

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

### Available Message Categories

All message constants are defined in `src/bot/messages.py`:
- **Error messages**: `ERROR_USER_NOT_FOUND`, `ERROR_USER_INACTIVE`, `ERROR_NO_HABITS`, etc.
- **Info messages**: `INFO_NO_REWARD_PROGRESS`, `INFO_REWARD_ACTIONABLE`, etc.
- **Success messages**: `SUCCESS_HABIT_COMPLETED`, `SUCCESS_REWARD_CLAIMED`, etc.
- **Help/usage messages**: `HELP_CLAIM_REWARD_USAGE`, `HELP_HABIT_SELECTION`, etc.
- **Headers**: `HEADER_REWARD_PROGRESS`, `HEADER_STREAKS`, etc.
- **Format messages**: `FORMAT_STREAK`, `FORMAT_PROGRESS`, etc.

### Language Detection

User language is automatically detected and stored:
1. **On first `/start`**: Detected from Telegram user settings via `update.effective_user.language_code`
2. **Stored in database**: User model has `language` field (default: 'en')
3. **Fallback chain**: User DB preference → Telegram preference → Default ('en')

Supported languages (configured in `src/config.py`):
- `en` - English (default)
- `ru` - Russian
- `kk` - Kazakh

### Adding New Messages

When adding new user-facing messages:

1. Add constant to `Messages` class in `src/bot/messages.py`:
```python
class Messages:
    MY_NEW_MESSAGE = "Default English text here"
```

2. Add translations to `_TRANSLATIONS` dictionary:
```python
_TRANSLATIONS = {
    'ru': {
        'MY_NEW_MESSAGE': "Русский перевод здесь"
    },
    'kk': {
        'MY_NEW_MESSAGE': "Қазақша аударма осында"
    }
}
```

3. Use in handlers:
```python
await update.message.reply_text(msg('MY_NEW_MESSAGE', lang))
```

### Formatter Functions

All formatter functions in `src/bot/formatters.py` accept a `language` parameter:

```python
# Always pass language to formatters
message = format_habit_completion_message(result, lang)
message = format_streaks_message(streaks, lang)
message = format_rewards_list_message(rewards, lang)
message = format_reward_progress_message(progress, reward, lang)
```

### Telegram Message Formatting

**CRITICAL**: All Telegram bot messages MUST use HTML formatting (not Markdown). Always set `parse_mode="HTML"` when sending messages.

#### HTML Formatting Rules

Use HTML tags for text formatting:
- **Bold**: `<b>text</b>` or `<strong>text</strong>`
- **Italic**: `<i>text</i>` or `<em>text</em>`
- **Underline**: `<u>text</u>`
- **Code**: `<code>text</code>`
- **Pre-formatted**: `<pre>text</pre>`
- **Links**: `<a href="URL">text</a>`

#### Character Escaping

HTML special characters MUST be escaped:
- `<` → `&lt;`
- `>` → `&gt;`
- `&` → `&amp;`

**No need to escape**: underscores, dots, hyphens, or parentheses (unlike Markdown)

#### Implementation Pattern

```python
# ✅ Good - Always use HTML
await update.message.reply_text(
    msg('SUCCESS_HABIT_COMPLETED', lang, habit_name=habit.name),
    parse_mode="HTML"
)

# ✅ Good - Escape HTML special characters when needed
reward_name = "Coffee & Tea"
message = f"<b>Reward:</b> {reward_name.replace('&', '&amp;')}"
await update.message.reply_text(message, parse_mode="HTML")

# ❌ Bad - Never use Markdown
await update.message.reply_text(
    "*Bold text*",
    parse_mode="Markdown"  # Don't use Markdown!
)

# ❌ Bad - Missing parse_mode
await update.message.reply_text(
    "<b>Bold text</b>"  # Won't render without parse_mode="HTML"
)
```

#### Message Constants

All message constants in `src/bot/messages.py` use HTML formatting:

```python
# Example message constants
SUCCESS_HABIT_COMPLETED = "✅ <b>Habit completed:</b> {habit_name}"
HEADER_STREAKS = "🔥 <b>Your Current Streaks:</b>\n"
INFO_REWARD_ACTIONABLE = "⏳ <b>Reward achieved!</b> You can claim it now!"
```

#### Why HTML Over Markdown?

1. **No escaping headaches**: No need to escape underscores, dots, hyphens in text
2. **More reliable**: Better rendering consistency in Telegram
3. **Clearer syntax**: HTML tags are more explicit than Markdown symbols
4. **Better control**: More formatting options available
5. **Standard**: HTML is a widely understood standard

See Telegram Bot API documentation for full HTML formatting reference.

### Django Migration Path

The current dictionary-based approach is designed for easy migration to Django's `gettext` i18n framework:

1. Current (Phase 1):
```python
ERROR_USER_NOT_FOUND = "User not found..."
msg('ERROR_USER_NOT_FOUND', lang)
```

2. Future (Phase 2 - Django):
```python
from django.utils.translation import gettext_lazy as _
ERROR_USER_NOT_FOUND = _("User not found...")
```

See `docs/features/0002_PLAN.md` for full Django migration guide.

## Logging Pattern

**CRITICAL**: All Telegram bot command handlers MUST include comprehensive info-level logging to track user messages and bot reactions. This provides visibility into user interactions, helps with debugging, and creates an audit trail.

### Implementation Pattern

```python
import logging

# At module level
logger = logging.getLogger(__name__)

async def my_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /my_command."""
    # 1. Log incoming message with user context
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /my_command from user {telegram_id} (@{username})")
    
    # 2. Log any user input/parameters
    if context.args:
        user_input = " ".join(context.args)
        logger.info(f"📝 User {telegram_id} provided input: '{user_input}'")
    
    # 3. Log validation failures
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return
    
    # 4. Log processing steps
    logger.info(f"⚙️ Processing command for user {telegram_id}")
    result = some_service.process_data(user.id)
    
    # 5. Log success with relevant metrics
    logger.info(f"✅ Command completed successfully for user {telegram_id}. Result: {result}")
    
    # 6. Log outgoing messages
    await update.message.reply_text(formatted_message)
    logger.info(f"📤 Sent success message to {telegram_id}")
    
    # 7. Log errors with full context
    except ValueError as e:
        logger.error(f"❌ Error processing command for user {telegram_id}: {str(e)}")
        await update.message.reply_text(msg('ERROR_GENERAL', lang, error=str(e)))
        logger.info(f"📤 Sent error message to {telegram_id}")
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

### What to Log

**Always log:**
1. **Incoming commands/messages**: User ID, username, command name, and any parameters
2. **User input**: Text messages, callback data, button selections
3. **Validation failures**: User not found, inactive user, invalid input
4. **Processing steps**: Key operations being performed
5. **Success metrics**: Points earned, streaks, status changes, counts
6. **Outgoing messages**: What message was sent to the user
7. **Errors**: Full error context with user ID

**Never log:**
- Sensitive data (passwords, tokens, API keys)
- Personal information beyond user ID and username
- Full message objects (too verbose)

### Files Following This Pattern

All bot handlers now include comprehensive logging:
- `src/bot/main.py` - `/start`, `/help` commands
- `src/bot/handlers/habit_done_handler.py` - `/habit_done` flow with custom text and NLP
- `src/bot/handlers/reward_handlers.py` - All reward commands
- `src/bot/handlers/streak_handler.py` - `/streaks` command

See `LOGGING_ENHANCEMENT_SUMMARY.md` for detailed documentation and `LOGGING_EXAMPLES.md` for real-world examples.

### Benefits

1. **Complete Visibility**: Every user interaction is logged with context
2. **Debugging**: Easy to trace issues and understand user flows
3. **Monitoring**: Track user engagement and command usage
4. **Performance**: Identify slow operations or bottlenecks
5. **Audit Trail**: Complete record of user actions and bot responses
6. **User Context**: Always includes Telegram ID and username for correlation

### For New Commands

When creating new bot commands, copy the logging pattern from existing handlers:
- Start with incoming message log
- Log each decision point and processing step
- Log all outgoing messages
- Use consistent emoji indicators
- Include user context in every log

## Repository Pattern

All database operations go through repository classes in `src/airtable/repositories.py`:
- `user_repository` - User CRUD operations
- `habit_repository` - Habit CRUD operations
- `habit_log_repository` - Habit log CRUD operations
- `reward_repository` - Reward CRUD operations
- `reward_progress_repository` - Reward progress CRUD operations

Never query Airtable directly from handlers or services. Always use the repository layer.

### Airtable Computed Fields

**CRITICAL**: Never attempt to set computed/formula fields when creating or updating Airtable records.

**Common Computed Fields**:
- `RewardProgress.pieces_required` - Formula field that looks up value from linked Reward record
- `RewardProgress.status` - Formula field that computes status based on progress

**Pattern**: Only set editable fields in repository create/update methods:

```python
# ✅ Good - Only set editable fields
record = self.table.create({
    "user_id": [progress.user_id],
    "reward_id": [progress.reward_id],
    "pieces_earned": progress.pieces_earned
    # pieces_required is computed from linked Reward
})

# ❌ Bad - Trying to set computed field
record = self.table.create({
    "user_id": [progress.user_id],
    "reward_id": [progress.reward_id],
    "pieces_earned": progress.pieces_earned,
    "pieces_required": progress.pieces_required  # ERROR: Computed field!
})
```

**Error to watch for**: `422 Client Error: INVALID_VALUE_FOR_COLUMN - Field cannot accept a value because the field is computed`

**Files affected**: `src/airtable/repositories.py:178` (RewardProgressRepository.create)

## Service Layer

Business logic lives in services (`src/services/`):
- `habit_service.py` - Orchestrates habit completion flow
- `streak_service.py` - Calculates streaks
- `reward_service.py` - Handles reward selection and cumulative progress
- `nlp_service.py` - NLP-based habit classification

Services coordinate between repositories and contain no direct Airtable calls.

### Streak Service Pattern

**CRITICAL**: The `StreakService` has two distinct methods for different use cases:

1. **`calculate_streak(user_id, habit_id)`** - Used when LOGGING a new habit
   - Returns what the NEXT streak will be after logging
   - If `last_completed_date == yesterday`: increments streak (consecutive day)
   - If `last_completed_date == today`: returns current streak (already logged today)
   - If `last_completed_date < yesterday`: resets to 1 (streak broken)
   - Used by: `habit_service.py` when processing habit completion

2. **`get_current_streak(user_id, habit_id)`** - Used when DISPLAYING current streak status
   - Returns the CURRENT streak from the most recent log
   - Does NOT increment or calculate - just retrieves stored value
   - Used by: `get_all_streaks_for_user()` for the `/streaks` command

**Why Two Methods?**

Bug discovered (2025-10): Using `calculate_streak()` for display caused incorrect results:
- Day 1: User logs "pushups" and "water" (both streak=1)
- Day 2: User logs only "pushups" (streak=2)
- Day 2: User checks `/streaks`
  - **Expected**: pushups=2, water=1
  - **Bug**: pushups=2, water=2 (incorrectly incremented because last_date was yesterday)

**Solution**: Created `get_current_streak()` that simply returns the stored streak value without any date-based calculation. This is correct for display purposes because the streak value in the log already represents the accurate state at the time of last completion.

**Files Modified**:
- `src/services/streak_service.py:68-93` - Added `get_current_streak()` method
- `src/services/streak_service.py:117` - Changed `get_all_streaks_for_user()` to use `get_current_streak()`
- `tests/test_streak_service.py:100-173` - Added comprehensive test for multi-habit scenario

## Import Pattern

When importing repositories, always use:
```python
from src.airtable.repositories import user_repository, habit_repository, ...
```

These are singleton instances defined at the bottom of each repository file.

## Testing

### Running Tests

Always run automated tests before committing:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_bot_handlers.py -v

# Run specific test
uv run pytest tests/test_bot_handlers.py::TestStartCommand::test_user_not_found -v

# Run with coverage report
uv run pytest --cov=src tests/
```

### Test Structure

Tests are located in `tests/` directory:
- `test_bot_handlers.py` - Telegram bot command handler tests (TC1.1, TC1.2, TC1.3)
- `test_habit_service.py` - Habit service business logic tests
- `test_streak_service.py` - Streak calculation tests
- `test_reward_service.py` - Reward selection and progress tests

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
    # Mock: user doesn't exist
    mock_user_repo.get_by_telegram_id.return_value = None

    # Execute
    await start_command(mock_telegram_update, context=None)

    # Assert error message sent
    mock_telegram_update.message.reply_text.assert_called_once_with(
        "❌ User not found. Please contact admin to register."
    )
```

### Key Testing Principles

1. **Mock External Dependencies**: Always mock Airtable repositories and Telegram objects
2. **Test All Paths**: Test success cases, error cases, and edge cases
3. **Async Tests**: Use `@pytest.mark.asyncio` for async handler functions
4. **Clear Test Names**: Use descriptive test names that explain what's being tested
5. **Assert Side Effects**: Verify that correct messages are sent and repositories are called

### Before Committing

Checklist:
1. ✅ All automated tests pass: `uv run pytest tests/ -v`
2. ✅ Manual testing of affected features in TEST_CASES.md
3. ✅ Bot starts without errors: `python src/bot/main.py`
4. ✅ No regressions in existing functionality

## Unified Reward System

**CRITICAL**: The reward system uses a unified cumulative approach where ALL rewards track progress. There is no distinction between "cumulative" and "non-cumulative" rewards.

### Core Concepts

**All rewards are cumulative with `pieces_required`**:
- Instant rewards: `pieces_required = 1` (claimable immediately after earning 1 piece)
- Multi-piece rewards: `pieces_required > 1` (requires multiple completions before claimable)

**3-State Status Workflow**:
1. **🕒 Pending**: `pieces_earned < pieces_required` - User is making progress
2. **⏳ Achieved**: `pieces_earned >= pieces_required && !claimed` - Ready to claim
3. **✅ Claimed**: `claimed == true` - User has claimed the reward

**Status is fully computed by Airtable formula** - Never set status manually in code.

### Data Models

**src/models/reward.py**:
- `pieces_required: int = Field(default=1)` - Required for ALL rewards
- `piece_value: float | None` - Monetary value per piece
- Removed: `is_cumulative` field (no longer needed)
- Removed: `RewardType.CUMULATIVE` enum value

**src/models/reward_progress.py**:
- `claimed: bool = Field(default=False)` - Whether user has claimed this reward
- `status: RewardStatus` - Computed by Airtable based on pieces_earned and claimed
- Status enum: `PENDING`, `ACHIEVED`, `CLAIMED` (renamed from COMPLETED)

### Service Layer Pattern

**src/services/reward_service.py**:

```python
# Always use update_reward_progress() for ANY reward (not just cumulative)
reward_progress = reward_service.update_reward_progress(
    user_id=user.id,
    reward_id=reward.id
)

# When user claims a reward
reward_service.mark_reward_claimed(user_id, reward_id)
# This resets pieces_earned to 0 and sets claimed=True, showing "0/N Claimed"
# Next time they earn a piece, claimed is automatically reset to False
```

**Key methods**:
- `update_reward_progress()` - Increments pieces_earned for any reward with smart status handling
  - **ACHIEVED status**: Will NOT increment (prevents over-counting beyond goal)
  - **CLAIMED status**: Resets `claimed=False` first, then increments (starts new cycle)
  - **PENDING status**: Increments normally
  - This ensures the counter doesn't go beyond the goal (e.g., won't show 2/1)
- `mark_reward_claimed()` - Resets pieces_earned to 0 and sets claimed=True when user claims achieved reward
  - **Important**: Resets counter to 0 and sets `claimed=True`
  - Status changes from "Achieved" (N/N) → "Claimed" (0/N) via Airtable formula
  - User will see "0/N Claimed" until they earn the next piece
  - When they earn the next piece, `update_reward_progress()` automatically resets `claimed=False`

**Removed methods** (as of Feature 0006):
- `update_cumulative_progress()` - renamed to `update_reward_progress()`
- `mark_reward_completed()` - renamed to `mark_reward_claimed()`
- `set_reward_status()` - status is now fully computed by Airtable

**Bug Fix (2025-10-22)**: Fixed issue where reward counter would continue incrementing after reaching the goal (e.g., showing "2/1" instead of "1/1"). The proper reward cycle is now:
1. **Pending** (0/N) → User earns pieces → **Pending** (1/N, 2/N, etc.)
2. **Achieved** (N/N) → User cannot earn more pieces (counter frozen at N/N)
3. **User claims** → `mark_reward_claimed()` → **Claimed** (0/N)
4. **User earns next piece** → `update_reward_progress()` resets `claimed=False` → **Pending** (1/N)
5. Cycle repeats from step 1

Key behaviors:
- Counter cannot exceed goal (prevents 2/1 bug)
- After claiming, counter shows 0/N with "Claimed" status
- Next piece earned automatically starts new cycle at 1/N "Pending"

**src/services/habit_service.py**:
```python
# Always update progress for ANY reward that was awarded
if got_reward:
    reward_progress = self.reward_service.update_reward_progress(
        user_id=user.id,
        reward_id=selected_reward.id
    )
```

### Repository Pattern

**src/airtable/repositories.py**:

RewardRepository:
- Removed `is_cumulative` field from create/update operations
- `pieces_required` defaults to 1 if not present in Airtable

RewardProgressRepository:
- Added `claimed` field handling in `_record_to_progress()`
- Status enum parsing updated to support CLAIMED status

### Bot Handlers

**src/bot/handlers/reward_handlers.py**:
- Use `mark_reward_claimed()` instead of `mark_reward_completed()`
- Status is read-only, computed by Airtable

**src/bot/formatters.py**:
- Always show progress for any reward (not just cumulative)
- Check `pieces_required > 1` instead of `is_cumulative`
- Removed `RewardType.CUMULATIVE` from emoji mapping

### Airtable Schema Requirements

**RewardProgress table**:
- Add `claimed` field (Checkbox, default: unchecked)
- Update `status` formula:
  ```
  IF(
    {claimed},
    "✅ Claimed",
    IF(
      {pieces_earned} >= {pieces_required},
      "⏳ Achieved",
      "🕒 Pending"
    )
  )
  ```

**Rewards table**:
- Set `pieces_required = 1` for all existing instant rewards
- Remove `is_cumulative` field (optional, after code deployment)

### Migration from Old System

**Before Feature 0005**:
- Dual types: cumulative vs non-cumulative rewards
- Only cumulative rewards created RewardProgress entries
- 4-state status with "🌱 Just started"
- `mark_reward_completed()` had broken implementation (empty dict)

**After Feature 0005**:
- Unified: all rewards are cumulative with pieces_required
- ALL rewards create RewardProgress entries
- 3-state status: PENDING → ACHIEVED → CLAIMED
- `mark_reward_claimed()` properly sets claimed=True

### Common Patterns

**Creating instant reward** (awarded once):
```python
reward = Reward(
    name="Coffee break",
    type=RewardType.REAL,
    pieces_required=1,  # Instant
    weight=1.0
)
```

**Creating multi-piece reward** (requires 10 completions):
```python
reward = Reward(
    name="Massage session",
    type=RewardType.REAL,
    pieces_required=10,  # Collect 10 pieces
    piece_value=5.0,     # Each piece worth $5
    weight=1.0
)
```

**Checking if reward is claimable**:
```python
# Check progress status (computed by Airtable)
if progress.status == RewardStatus.ACHIEVED:
    # User can claim this reward
    pass
```

### Files Modified in Feature 0005

- `src/models/reward.py` - Removed is_cumulative, made pieces_required required
- `src/models/reward_progress.py` - Added claimed field, renamed status
- `src/airtable/repositories.py` - Updated field handling
- `src/services/reward_service.py` - Renamed methods, fixed claiming
- `src/services/habit_service.py` - Always update progress for all rewards
- `src/bot/formatters.py` - Removed cumulative conditionals
- `src/bot/handlers/reward_handlers.py` - Updated method names, deprecated set_status

See `docs/features/0005_PLAN.md` for full implementation details.

### Feature 0006: Removed /set_reward_status Command

**Date**: 2025-10-20

**Reason**: The `/set_reward_status` command became obsolete after Feature 0005 unified the reward system. Reward status is now fully computed by Airtable based on `pieces_earned`, `pieces_required`, and `claimed` fields. Manual status updates are no longer needed or supported.

**Files Modified**:
- `src/bot/main.py` - Removed command handler registration and import
- `src/bot/handlers/reward_handlers.py` - Removed `set_reward_status_command()` function (lines 256-330)
- `src/bot/messages.py` - Removed `HELP_SET_STATUS_USAGE` constant and all references to `/set_reward_status` in help text (English, Russian, Kazakh)

**Migration Path**: Users should use `/claim_reward` to mark achieved rewards as claimed. Status changes automatically based on progress.

## Future Django Migration

**CRITICAL**: When designing new features or refactoring existing code, always consider future migration to Django framework. Follow these principles to ensure smooth transition.

### Architecture Principles

**Keep business logic in the service layer** - Never put business logic directly in handlers/views:
- ✅ **Good**: Handler calls service method, service contains logic
- ❌ **Bad**: Handler contains business logic, calculations, or complex conditionals

**Use repository pattern consistently** - This abstracts data access and makes migration easier:
- Current: `src/airtable/repositories.py` → Future: Django ORM models/managers
- Repositories should have clean interfaces that don't expose Airtable-specific details
- All data access MUST go through repositories (never query Airtable directly)

**Maintain clear separation of concerns**:
```
Handlers (Bot/API) → Services (Business Logic) → Repositories (Data Access) → Data Store
```

This layered architecture maps directly to Django:
- Handlers → Django views/viewsets
- Services → Django services/managers
- Repositories → Django ORM models
- Airtable → PostgreSQL/MySQL

### Model Design Guidelines

**Keep validation logic in model classes** - Pydantic validators will transfer to Django model validators:

```python
# Current (Pydantic)
class User(BaseModel):
    telegram_id: str = Field(...)

    @field_validator('telegram_id')
    def validate_telegram_id(cls, v):
        # Validation logic
        return v

# Future (Django)
class User(models.Model):
    telegram_id = models.CharField(...)

    def clean(self):
        # Same validation logic
        pass
```

**Use type hints consistently** - Helps with Django model field mapping:
- `str` → `CharField` or `TextField`
- `int` → `IntegerField`
- `float` → `FloatField`
- `bool` → `BooleanField`
- `datetime` → `DateTimeField`

**Document field constraints and relationships**:
- Add docstrings explaining field purpose
- Note any business rules or constraints
- Document relationships between models (one-to-many, many-to-many)

**Design with relational database in mind**:
- Avoid Airtable-specific features (formulas, rollups) in business logic
- Think in terms of foreign keys and joins
- Consider normalization and data integrity

### Service Layer Best Practices

**Services should be framework-agnostic**:
```python
# ✅ Good - No framework coupling
class HabitService:
    def process_habit_completion(self, user_id: str, habit_id: str) -> HabitCompletionResult:
        # Business logic using repositories
        pass

# ❌ Bad - Coupled to Telegram
class HabitService:
    async def process_habit_completion(self, update: Update) -> None:
        # Direct handler coupling
        pass
```

**Keep services reusable**:
- Services should work from bot handlers, API endpoints, or admin commands
- Don't assume specific request/response formats
- Return data objects, not formatted messages

**Avoid tight coupling to infrastructure**:
- Don't import `pyairtable` in services
- Don't use Airtable-specific query syntax in business logic
- Keep external dependencies injected or abstracted

### Configuration Management

**Keep all configuration centralized** in `src/config.py`:
- Uses `pydantic-settings` (similar to Django settings)
- Environment variables work the same way in Django
- Easy migration path to `settings.py`

**Document all configuration options**:
- Add type hints and descriptions
- Use sensible defaults
- Group related settings

```python
# Current (pydantic-settings)
class Settings(BaseSettings):
    database_url: str = "sqlite:///db.sqlite3"

# Future (Django settings.py)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
    }
}
```

### Database & Repository Considerations

**Repository pattern abstracts data source**:
```python
# Interface remains the same
user = user_repository.get_by_telegram_id(telegram_id)

# Implementation changes:
# Current: Queries Airtable API
# Future: Django ORM query (User.objects.get(telegram_id=telegram_id))
```

**Design data models with Django ORM in mind**:
- Think about database indexes (frequently queried fields)
- Consider cascade delete behavior
- Plan for database migrations
- Document any complex queries that will need optimization

**Avoid Airtable-specific patterns**:
- ✅ Use repository methods: `habit_repository.get_by_user(user_id)`
- ❌ Don't use formula fields for business logic
- ❌ Don't rely on Airtable views for filtering

### Multi-lingual Support (i18n)

When implementing message constants or multi-lingual features, use Django-compatible patterns:

**Use patterns compatible with Django i18n**:
```python
# Good - Can migrate to Django's gettext
from django.utils.translation import gettext as _

ERROR_USER_NOT_FOUND = _("User not found. Please contact admin to register.")

# Acceptable - Can migrate to django.conf.settings
class Messages:
    ERROR_USER_NOT_FOUND = "User not found. Please contact admin to register."
```

**Structure messages for easy migration**:
- Centralize all user-facing strings in one module
- Use message keys/constants (not inline strings)
- Consider `.po` file format from the start
- Keep message templates separate from logic

**Plan for Django's i18n framework**:
- Django uses GNU gettext (`.po` and `.mo` files)
- Messages can be extracted automatically with `makemessages`
- Supports pluralization, context, and locale-specific formatting

### When Refactoring

Before refactoring any component, ask:

1. **Will this work with Django ORM?** (instead of Airtable)
2. **Is business logic in services?** (not in handlers)
3. **Can this be tested independently?** (no tight coupling)
4. **Is configuration externalized?** (environment variables)
5. **Are messages/strings centralized?** (easy to translate)

### Migration Checklist for New Features

When adding a new feature:
- [ ] Business logic implemented in service layer
- [ ] Data access goes through repository pattern
- [ ] Models use standard Python types (no Airtable-specific types)
- [ ] Configuration uses environment variables
- [ ] User-facing strings are constants/messages (not inline)
- [ ] Code is framework-agnostic where possible
- [ ] Relationships between models are documented
- [ ] Tests mock repositories (not Airtable directly)

### Resources

- Django project structure: [docs.djangoproject.com](https://docs.djangoproject.com)
- Django ORM: Equivalent to our repository pattern
- Django management commands: For running Telegram bot
- Django REST Framework: For future API endpoints
- Django i18n: For multi-lingual support
