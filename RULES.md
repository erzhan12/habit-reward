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
if not user.is_active:
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

All database operations go through repository classes in `src/core/repositories.py`:
- `user_repository` - User CRUD operations
- `habit_repository` - Habit CRUD operations
- `habit_log_repository` - Habit log CRUD operations
- `reward_repository` - Reward CRUD operations
- `reward_progress_repository` - Reward progress CRUD operations

Never query the Django ORM directly from handlers or services. Always use the repository layer.

### Django ORM Repository Pattern

**CRITICAL**: Repositories wrap Django ORM queries to provide async compatibility and maintain a consistent interface for services.

**Async Wrapper Pattern**:

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

**Performance Optimization**:

Always use `select_related()` and `prefetch_related()` for ForeignKey and ManyToMany relationships to avoid N+1 queries:

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

**Global Repository Instances**:

Repositories are instantiated as singletons at module level:

```python
# At bottom of src/core/repositories.py
user_repository = UserRepository()
habit_repository = HabitRepository()
habit_log_repository = HabitLogRepository()
reward_repository = RewardRepository()
reward_progress_repository = RewardProgressRepository()
```

**Files affected**: `src/core/repositories.py`

### Django Model Instantiation Pattern

**CRITICAL**: When working with Django models in services, always pass dictionaries to repository `create()` methods instead of instantiating Django model objects directly.

**Pattern for Creating Records**:

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
- `timestamp` fields with `auto_now_add=True` (e.g., `HabitLog.timestamp`)
- `updated_at` fields with `auto_now=True` (e.g., `User.updated_at`)
- `date_joined` field from `AbstractUser` (auto-set on user creation)
- `last_login` field from `AbstractUser` (managed by Django auth)
- Fields with `default` values (can be omitted)

**Django User Model Field Mappings**:

The `User` model extends Django's `AbstractUser`, which means some field names changed from the old Airtable schema:

```python
# Old Airtable field → New Django field
'active' → 'is_active'           # BooleanField from AbstractUser
'created_at' → 'date_joined'     # DateTimeField from AbstractUser (auto_now_add=True)

# When creating users via repository:
await user_repository.create({
    'telegram_id': telegram_id,
    'name': name,
    'language': language,
    'is_active': True,            # Use 'is_active', not 'active'
    # 'date_joined' is auto-set, don't include it
    # 'updated_at' is auto-set, don't include it
})
```

**Files affected**:
- `src/services/reward_service.py` - Uses dict pattern for model creation
- `src/core/models.py` - Django model definitions
- All service files should follow this pattern

### Computed Values Pattern

**Use regular methods instead of `@property` for computed values.** This provides better async compatibility and more explicit intent.

**RewardProgress Computed Methods**:
- `get_status()` - Returns RewardStatus (CLAIMED, ACHIEVED, or PENDING)
- `get_pieces_required()` - Gets pieces_required from linked reward (needs select_related('reward'))
- `get_progress_percent()` - Calculates percentage completion (0-100)
- `get_status_emoji()` - Extracts emoji from status value

**Usage Pattern**:

```python
# ✅ Good - Use method calls
if progress.get_status() == RewardStatus.ACHIEVED:
    pieces_needed = progress.get_pieces_required()
    percent = progress.get_progress_percent()
    emoji = progress.get_status_emoji()

# ❌ Bad - Properties no longer exist
if progress.status == RewardStatus.ACHIEVED:  # AttributeError!
    pieces_needed = progress.pieces_required  # AttributeError!
```

**Important**: Always use `select_related('reward')` when querying RewardProgress to avoid N+1 queries when calling `get_pieces_required()`.

```python
# ✅ Good - Prefetch related data
progress = await progress_repo.get_by_user_and_reward(user_id, reward_id)  # Repository does select_related
progress.get_pieces_required()  # No extra query

# ⚠️ Risky - May cause extra query if not prefetched
progress = RewardProgress.objects.get(id=progress_id)  # No select_related
progress.get_pieces_required()  # Extra DB query!
```

**Files affected**:
- `src/core/models.py:210-253` - RewardProgress computed methods
- `src/services/reward_service.py` - Calls get_status() method
- `src/bot/formatters.py` - Uses all computed methods
- `src/bot/handlers/reward_handlers.py` - Uses get_status() method

### Async-Safe ForeignKey Access Pattern

**CRITICAL**: Django model methods that access ForeignKey relationships MUST NOT trigger synchronous database queries when called from async contexts.

**The Problem**:
When a Django model method accesses a ForeignKey field (e.g., `self.reward.pieces_required`), it triggers a database query if the related object is not loaded. In async contexts, this causes `SynchronousOnlyOperation` errors.

**Example of Broken Pattern**:
```python
# ❌ Bad - Causes SynchronousOnlyOperation in async contexts
class RewardProgress(models.Model):
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)

    def get_status(self):
        # This triggers a sync DB query in async contexts!
        if self.pieces_earned >= self.reward.pieces_required:
            return self.RewardStatus.ACHIEVED
```

**The Solution - Cache ForeignKey Values**:

1. **In Repository Methods**: After fetching objects with `select_related()`, cache the needed FK values directly on the instance:

```python
# In RewardProgressRepository
@staticmethod
def _attach_cached_pieces_required(progress: RewardProgress) -> RewardProgress:
    """Attach cached pieces_required to avoid ForeignKey access in async contexts."""
    if progress and hasattr(progress, 'reward'):
        # Access reward.pieces_required now (in sync context) and cache it
        progress._cached_pieces_required = progress.reward.pieces_required
    return progress

async def get_by_user_and_reward(self, user_id, reward_id):
    progress = await sync_to_async(
        RewardProgress.objects.select_related('reward').get
    )(user_id=user_id, reward_id=reward_id)
    return self._attach_cached_pieces_required(progress)  # Cache FK values
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
        # Check for cached value first (set by repository)
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

**Why This Works**:
- Repository methods access ForeignKeys inside `sync_to_async()` wrappers (sync context)
- Values are cached as simple attributes on the instance
- Model methods access cached attributes (no DB query)
- Works reliably across async/sync boundaries

**Files affected** (Bug Fix: 2025-11-19):
- `src/core/models.py:210-253` - Added `_get_pieces_required_safe()` helper
- `src/core/repositories.py:215-358` - Added caching helper, updated all methods

**Related Bug**: Completing multiple habits in succession caused `SynchronousOnlyOperation` error on the second habit because `get_status()` tried to access `self.reward.pieces_required` in an async context.

## Service Layer

Business logic lives in services (`src/services/`):
- `habit_service.py` - Orchestrates habit completion flow
- `streak_service.py` - Calculates streaks
- `reward_service.py` - Handles reward selection and cumulative progress
- `nlp_service.py` - NLP-based habit classification

Services coordinate between repositories and contain no direct database calls.

### NLP Service Optional Pattern

**CRITICAL**: The NLP service is optional and should gracefully degrade when LLM_API_KEY is not configured. This allows the application to start and run even without AI features.

**Implementation Pattern** (`src/services/nlp_service.py`):

```python
class NLPService:
    def __init__(self):
        self.enabled = False
        self.client = None

        if not settings.LLM_API_KEY:
            logger.warning("⚠️ LLM_API_KEY is not configured. NLP habit classification will be disabled.")
            return  # Graceful degradation

        try:
            self.client = OpenAI(api_key=settings.LLM_API_KEY)
            self.enabled = True
            logger.info(f"✅ NLP service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize client: {e}. NLP features will be disabled.")
            return

    def classify_habit_from_text(self, user_text: str, available_habits: list[str]) -> list[str]:
        if not self.enabled or not self.client:
            return []  # Return empty list when disabled

        # Normal classification logic...
```

**Key Behaviors**:
1. **No exceptions on missing config**: Service initializes successfully even without LLM_API_KEY
2. **Disabled flag**: `self.enabled` tracks whether the service is functional
3. **Graceful fallback**: Methods return empty results instead of failing
4. **Clear logging**: Warning messages inform about disabled state
5. **Try-catch protection**: Catches initialization errors and disables service

**Why This Matters**:
- Application can run in development without requiring API keys
- Reduces dependencies for local testing
- Prevents startup failures due to missing optional features
- Makes deployment more resilient

**Files Modified** (Feature: Optional NLP Service):
- `src/services/nlp_service.py:14-36` - Made LLM_API_KEY optional with graceful degradation
- `src/services/nlp_service.py:60-63` - Added enabled check in classify_habit_from_text()

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
from src.core.repositories import user_repository, habit_repository, ...
```

These are singleton instances defined at the bottom of the repository file.

## Pydantic Settings Configuration

**CRITICAL**: When using Pydantic Settings with list-type fields that need to accept comma-separated environment variables, use a `@model_validator` to handle parsing.

### The Problem

Pydantic Settings tries to JSON-parse environment variables for complex types like `list[str]`. When environment variables are set as comma-separated strings (e.g., `SUPPORTED_LANGUAGES=en,ru,kk`), this causes a `JSONDecodeError`.

**Error Example**:
```python
# In settings class
supported_languages: list[str] = ["en", "ru", "kk"]

# In docker-compose.yml or .env
SUPPORTED_LANGUAGES=en,ru,kk  # Comma-separated string

# Result: JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

### The Solution: Model Validator Pattern

Use a union type (`str | list[str]`) with a `@model_validator` to handle both formats:

```python
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Accept both string and list formats
    supported_languages: str | list[str] = ["en", "ru", "kk"]

    @model_validator(mode="after")
    def parse_supported_languages(self):
        """Parse comma-separated string to list for supported_languages."""
        if isinstance(self.supported_languages, str):
            # Split comma-separated string and strip whitespace
            self.supported_languages = [
                lang.strip() for lang in self.supported_languages.split(",") if lang.strip()
            ]
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
```

### Supported Formats

This pattern supports multiple input formats:
- **Default value**: `["en", "ru", "kk"]` (list)
- **Comma-separated**: `SUPPORTED_LANGUAGES=en,ru,kk` (string)
- **With spaces**: `SUPPORTED_LANGUAGES=en, ru, kk` (string with spaces)
- **Single value**: `SUPPORTED_LANGUAGES=en` (single item)
- **JSON array**: `SUPPORTED_LANGUAGES=["en","ru","kk"]` (JSON - if needed)

### Why @model_validator Instead of @field_validator?

Pydantic Settings' `EnvSettingsSource` processes environment variables BEFORE field validators run. For complex types, it attempts JSON parsing first, which fails with comma-separated strings. A `@model_validator(mode="after")` runs AFTER all fields are loaded, allowing custom parsing logic.

### Files Affected

**Bug Fix** (2025-11-16):
- **Error**: Application failed to start with `SettingsError: error parsing value for field "supported_languages"`
- **Root Cause**: Docker environment set `SUPPORTED_LANGUAGES=en,ru,kk` but Pydantic expected JSON format
- **Fix**: Added `@model_validator` to `src/config.py:38-46` to parse comma-separated strings

**Files modified**:
- `src/config.py:3` - Added `model_validator` import
- `src/config.py:35` - Changed type to `str | list[str]`
- `src/config.py:38-46` - Added `parse_supported_languages()` model validator

## Django Configuration

**CRITICAL**: All Django configuration is centralized in `src/habit_reward_project/settings.py`. Environment-specific settings use environment variables.

### Settings Location

```
src/
├── habit_reward_project/
│   ├── settings.py          # Main Django settings
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # WSGI application
│   └── asgi.py              # ASGI application (for async)
└── core/                    # Main Django app
    ├── models.py
    ├── admin.py
    ├── repositories.py
    └── migrations/
```

### Environment Variables

Configuration uses `django-environ` for environment variable management:

**Required Variables**:
- `SECRET_KEY` - Django secret key (auto-generated in development)
- `DATABASE_URL` - Database connection string (default: SQLite)
- `TELEGRAM_BOT_TOKEN` - Telegram bot authentication token

**Optional Variables**:
- `DEBUG` - Debug mode (default: True in development)
- `TELEGRAM_WEBHOOK_URL` - Webhook endpoint for production
- `LLM_PROVIDER` - AI provider (e.g., 'openai', 'anthropic')
- `LLM_MODEL` - AI model name
- `LLM_API_KEY` - AI service API key

**Example `.env` file**:
```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3                    # Development
# DATABASE_URL=postgres://user:pass@localhost/dbname  # Production
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
DEBUG=True
```

### Database Configuration

**Development**: SQLite (default)
```python
# settings.py
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}
```

**Production**: PostgreSQL (recommended)
```bash
# .env
DATABASE_URL=postgres://username:password@hostname:5432/database_name
```

The `env.db()` helper from `django-environ` automatically parses database URLs into Django's `DATABASES` format.

### Custom User Model

**CRITICAL**: This project uses a custom user model that extends Django's `AbstractUser`:

```python
# settings.py
AUTH_USER_MODEL = 'core.User'
```

This allows Telegram-specific fields while maintaining Django's built-in authentication features.

### Custom Settings (Habit Bot Specific)

```python
# Habit tracking configuration
STREAK_MULTIPLIER_RATE = 0.1      # Streak bonus multiplier (10% per streak)
PROGRESS_BAR_LENGTH = 10          # Progress bar length in characters
RECENT_LOGS_LIMIT = 10            # Number of recent logs to fetch

# Multi-lingual support
SUPPORTED_LANGUAGES = ['en', 'ru', 'kk']
```

**Files affected**:
- `src/habit_reward_project/settings.py` - All Django configuration
- `src/config.py` - Bot-specific settings (legacy, being phased out)

## GitHub Actions Deployment & DATABASE_URL Encoding

**CRITICAL**: When deploying via GitHub Actions, database passwords with special characters MUST be URL-encoded in the `DATABASE_URL` to prevent parsing errors.

### The Problem

Django uses `django-environ` to parse `DATABASE_URL` connection strings. Passwords containing special characters like `#`, `/`, `=`, `@`, `:` will break URL parsing if not encoded:

**Error Example**:
```python
DATABASE_URL=postgresql://postgres:pass#word@db:5432/mydb
# Parsing fails: '#' is interpreted as URL fragment marker
# Error: "Port could not be cast to integer value as 'word@db'"
```

### The Solution: URL Encoding

All special characters in passwords must be URL-encoded:
- `#` → `%23`
- `/` → `%2F`
- `=` → `%3D`
- `@` → `%40`
- `:` → `%3A`
- Space → `%20`

**Correct Example**:
```bash
# Original password: "3QZ#C_Jp5ls7W01k"
# Encoded password:  "3QZ%23C_Jp5ls7W01k"
DATABASE_URL=postgresql://postgres:3QZ%23C_Jp5ls7W01k@db:5432/habit_reward
```

### GitHub Actions Implementation

The `.github/workflows/deploy.yml` workflow automatically handles URL encoding:

1. **Reads password from environment variable** (safer than command-line args)
2. **Uses Python inline command** with `urllib.parse.quote()` to avoid nested heredoc issues
3. **Encodes with `safe=''`** to encode ALL special characters
4. **Regenerates .env file** from scratch on every deployment to prevent corruption
5. **Verifies DATABASE_URL format** before proceeding with deployment

**Key Code Pattern** (`.github/workflows/deploy.yml:154-157`):
```bash
# Export password as environment variable (safer than command-line args)
export DB_PASSWORD='${{ secrets.POSTGRES_PASSWORD }}'

# URL-encode using Python inline command
ENCODED_PASSWORD=$(python3 -c "import urllib.parse, os; print(urllib.parse.quote(os.environ.get('DB_PASSWORD', ''), safe=''), end='')")

# Use in DATABASE_URL
printf 'DATABASE_URL=postgresql://%s:%s@db:5432/%s\n' \
  "$POSTGRES_USER" "$ENCODED_PASSWORD" "$POSTGRES_DB"
```

### Why Environment Variables Instead of Command-Line Args?

Passing passwords via command-line arguments (`sys.argv`) exposes them in process listings and shell history. Using environment variables is more secure.

### GitHub Secrets Configuration

Ensure these secrets are set in your GitHub repository:
- `POSTGRES_DB` - Database name (e.g., `habit_reward`)
- `POSTGRES_USER` - Database user (e.g., `postgres`)
- `POSTGRES_PASSWORD` - **RAW password** (NOT encoded - encoding happens in workflow)
- Other Django/Telegram secrets as needed

**IMPORTANT**: Store the RAW password in GitHub Secrets. The workflow will automatically encode it when building `DATABASE_URL`.

### Debugging DATABASE_URL Issues

If you see errors like:
- `"Port could not be cast to integer value as 'XYZ'"`
- `"Invalid database URL"`
- Django fails to connect to PostgreSQL

**Check**:
1. Does the password contain special characters? (`#`, `/`, `=`, `@`, `:`)
2. Is the `DATABASE_URL` properly URL-encoded?
3. Verify encoding: `python3 -c "import urllib.parse; print(urllib.parse.quote('your-password', safe=''))"`
4. Check deployment logs for "Verifying DATABASE_URL format" output

### Files Modified (Fix: DATABASE_URL Encoding)

**Date**: 2025-11-14

**Bug**: Deployment failed with `ValueError: Port could not be cast to integer value as 'bOlbTIuDlrUcT423puSykGaB60LrWEq9HjHuL'` because special characters in `POSTGRES_PASSWORD` were not URL-encoded.

**Fix**: Enhanced `.github/workflows/deploy.yml` to:
1. Use environment variables for password (not command-line args)
2. Always regenerate `.env` from scratch to prevent corruption
3. Add comprehensive verification of `DATABASE_URL` format
4. Create timestamped backups of existing `.env` files

**Files affected**:
- `.github/workflows/deploy.yml:147-302` - Improved .env generation and DATABASE_URL encoding

## Django Models

**CRITICAL**: All data models are Django ORM models in `src/core/models.py`. These replaced the old Pydantic models from Airtable.

### Model Overview

The project has 5 core models:

1. **User** - Custom user model extending `AbstractUser`
2. **Habit** - Habit definitions
3. **Reward** - Reward definitions
4. **RewardProgress** - User progress tracking for rewards
5. **HabitLog** - Habit completion history

### User Model (extends AbstractUser)

```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Inherited from AbstractUser:
    # - username, email, password (auth fields)
    # - first_name, last_name
    # - is_staff, is_superuser, is_active (permissions)
    # - date_joined, last_login (timestamps)

    # Custom Telegram fields:
    telegram_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=2, default='en')
    updated_at = models.DateTimeField(auto_now=True)
```

**Key Features**:
- Username auto-generated as `f"tg_{telegram_id}"`
- `is_active` replaces old `active` field (from AbstractUser)
- `date_joined` replaces old `created_at` field (from AbstractUser)
- Supports Django's built-in authentication and admin interface

### Habit Model

```python
class Habit(models.Model):
    name = models.CharField(max_length=255, unique=True)
    weight = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    category = models.CharField(max_length=100, null=True, blank=True)
    active = models.BooleanField(default=True)
```

**Validation**:
- Weight must be between 1 and 100 (enforced by Django validators)
- Name must be unique across all habits

### Reward Model

```python
class Reward(models.Model):
    class RewardType(models.TextChoices):
        VIRTUAL = 'virtual', 'Virtual'
        REAL = 'real', 'Real'
        NONE = 'none', 'None'

    name = models.CharField(max_length=255, unique=True)
    weight = models.FloatField(default=1.0)
    type = models.CharField(max_length=10, choices=RewardType.choices)
    pieces_required = models.IntegerField(default=1)
    piece_value = models.FloatField(null=True, blank=True)
```

**Unified Reward System**:
- All rewards use `pieces_required` (instant rewards: `pieces_required=1`)
- `type` uses Django's `TextChoices` enum for type safety
- `piece_value` is optional (for monetary rewards)

### RewardProgress Model

```python
class RewardProgress(models.Model):
    class RewardStatus(models.TextChoices):
        PENDING = '🕒 Pending', 'Pending'
        ACHIEVED = '⏳ Achieved', 'Achieved'
        CLAIMED = '✅ Claimed', 'Claimed'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    pieces_earned = models.IntegerField(default=0)
    claimed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    # Computed methods (not database fields)
    def get_status(self):
        """Returns current status based on progress and claimed flag"""
        if self.claimed:
            return self.RewardStatus.CLAIMED
        elif self.pieces_earned >= self.reward.pieces_required:
            return self.RewardStatus.ACHIEVED
        else:
            return self.RewardStatus.PENDING

    def get_pieces_required(self):
        """Returns pieces_required from linked reward (needs select_related)"""
        return self.reward.pieces_required

    def get_progress_percent(self):
        """Calculates progress percentage (0-100)"""
        if self.reward.pieces_required == 0:
            return 0
        return min(100, (self.pieces_earned / self.reward.pieces_required) * 100)

    def get_status_emoji(self):
        """Extracts emoji from status value"""
        return self.get_status().split()[0]
```

**Critical Pattern**: Status is computed in Python, not stored in database (replaces Airtable formula fields).

### HabitLog Model

```python
class HabitLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE)
    reward = models.ForeignKey(Reward, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    streak_count = models.IntegerField(default=1)
    got_reward = models.BooleanField(default=False)
    habit_weight = models.IntegerField()
    total_weight_applied = models.FloatField()
    last_completed_date = models.DateField()
```

**Cascade Behavior**:
- Deleting user → deletes all their habit logs (CASCADE)
- Deleting habit → deletes all logs for that habit (CASCADE)
- Deleting reward → keeps logs but nullifies reward reference (SET_NULL)

**Files affected**:
- `src/core/models.py` - All Django model definitions

## Django Admin

**CRITICAL**: Django admin is fully configured and provides a web interface for managing all models.

### Accessing Django Admin

1. **Create superuser** (first time only):
```bash
python manage.py createsuperuser
```

2. **Run Django development server**:
```bash
python manage.py runserver
```

3. **Access admin interface**:
```
http://localhost:8000/admin/
```

### Admin Features

All models are registered with custom admin classes in `src/core/admin.py`:

**UserAdmin**:
- Extends Django's built-in `UserAdmin`
- Displays: telegram_id, name, email, is_active, date_joined
- Search by: telegram_id, username, email, name
- Filters: is_active, is_staff, date_joined
- Fieldsets organized: Telegram Info, Personal Info, Permissions, Dates

**HabitAdmin**:
- List display: name, category, weight, active
- Search: name, category
- Filters: active, category
- Inline editing of habits

**RewardAdmin**:
- List display: name, type, pieces_required, piece_value, weight
- Search: name
- Filters: type
- Shows reward configuration

**RewardProgressAdmin**:
- List display: user, reward, pieces_earned, computed status, progress percentage
- Search: user__telegram_id, reward__name
- Filters: claimed, updated_at
- Shows computed fields via methods
- Uses `select_related` to optimize queries

**HabitLogAdmin**:
- List display: user, habit, timestamp, streak_count, got_reward, reward
- Search: user__telegram_id, habit__name
- Filters: got_reward, timestamp
- Date hierarchy: timestamp
- Autocomplete for related fields

### Custom Admin Methods

Computed values are displayed via custom admin methods:

```python
@admin.register(RewardProgress)
class RewardProgressAdmin(admin.ModelAdmin):
    def status(self, obj):
        """Display computed status"""
        return obj.get_status()

    def progress_percentage(self, obj):
        """Display progress as percentage"""
        return f"{obj.get_progress_percent():.0f}%"

    list_display = ['user', 'reward', 'pieces_earned', 'status', 'progress_percentage']
```

**Files affected**:
- `src/core/admin.py` - All admin configurations

## Database Migrations

**CRITICAL**: Django migrations track all changes to database schema. Always create and run migrations after modifying models.

### Migration Commands

**Create migrations** (after changing models):
```bash
python manage.py makemigrations
```

**Apply migrations** (update database):
```bash
python manage.py migrate
```

**Show migration status**:
```bash
python manage.py showmigrations
```

**Rollback migration** (if needed):
```bash
python manage.py migrate core 0001  # Rollback to migration 0001
```

### When to Create Migrations

Create migrations whenever you:
- Add, remove, or modify model fields
- Change field types or constraints
- Add or remove models
- Change model Meta options (indexes, ordering, etc.)

### Migration Files

Migrations are stored in `src/core/migrations/`:
```
src/core/migrations/
├── __init__.py
├── 0001_initial.py        # Initial migration (created Oct 23, 2025)
└── 0002_*.py              # Future migrations
```

**Initial migration** (`0001_initial.py`):
- Created all 5 tables: User, Habit, Reward, RewardProgress, HabitLog
- Set up ForeignKey relationships
- Configured indexes and constraints

### Migration Best Practices

1. **Always review migrations** before applying:
```bash
python manage.py sqlmigrate core 0001  # View SQL for migration
```

2. **Never edit applied migrations** - create new migrations instead

3. **Commit migrations to git** - they're part of your codebase

4. **Test migrations on copy of production data** before deploying

5. **Backup database** before running migrations in production

### First-Time Setup

For new developers or deployment:

```bash
# 1. Apply all migrations
python manage.py migrate

# 2. Create superuser for admin access
python manage.py createsuperuser

# 3. Verify setup
python manage.py check
```

**Files affected**:
- `src/core/migrations/` - All migration files
- `src/core/models.py` - Models that trigger migrations

## Django Transactions

**CRITICAL**: Use Django transactions for operations that require multiple database changes to succeed or fail atomically.

### Transaction Pattern

Django transactions ensure data consistency by wrapping multiple database operations:

```python
from django.db import transaction
from asgiref.sync import sync_to_async

# Wrap transaction in sync_to_async for use in async handlers
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

Use `transaction.atomic()` when:
1. **Deleting records with side effects** (e.g., reverting habit completion)
2. **Creating multiple related records** (e.g., user + initial settings)
3. **Updating multiple tables** that must stay consistent
4. **Financial operations** (e.g., claiming rewards with monetary value)

### Example: Habit Revert with Transaction

From `src/bot/handlers/habit_revert_handler.py`:

```python
async def _revert_habit_log_transaction(log_id: str, progress_id: str):
    """Atomically revert habit log and update reward progress"""
    def _transaction():
        with transaction.atomic():
            # 1. Delete the habit log
            HabitLog.objects.filter(pk=log_id).delete()

            # 2. Decrement reward progress
            if progress_id:
                progress = RewardProgress.objects.get(id=progress_id)
                progress.pieces_earned = max(0, progress.pieces_earned - 1)
                progress.claimed = False
                progress.save()

            # If anything fails, entire operation is rolled back

    await sync_to_async(_transaction)()
```

### Transaction Best Practices

1. **Keep transactions short** - only include necessary operations
2. **Don't call external APIs** inside transactions (they can't be rolled back)
3. **Use select_for_update()** for race condition protection:
```python
with transaction.atomic():
    progress = RewardProgress.objects.select_for_update().get(id=progress_id)
    progress.pieces_earned += 1
    progress.save()
```

4. **Handle exceptions** inside transaction block:
```python
try:
    with transaction.atomic():
        # ... operations ...
except IntegrityError:
    # Transaction automatically rolled back
    logger.error("Database constraint violation")
```

5. **Use savepoints** for nested transactions (advanced):
```python
with transaction.atomic():
    # Outer transaction

    with transaction.atomic():
        # Inner savepoint
        # Can be rolled back independently
```

### Habit Completion Transaction Pattern

**CRITICAL**: Habit completion operations MUST wrap both reward progress updates and habit log creation in an atomic transaction to prevent data inconsistencies.

**Implementation** (`src/services/habit_service.py:184-205`):

```python
# Wrap both operations in atomic transaction
async with self._atomic():
    reward_progress = None
    if got_reward:
        # Update reward progress (creates entry if doesn't exist)
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

**Why This Matters**:

Without atomic transaction wrapping, the following data corruption can occur:

1. **Orphaned progress entries**: `update_reward_progress()` creates entry with `pieces_earned=0`, but `habit_log.create()` fails
   - Result: RewardProgress entry exists with 0 pieces, but no corresponding HabitLog
   - This is how entries like "MacBook Pro: 0/10 pieces, no logs" can appear

2. **Missing progress updates**: HabitLog created successfully, but progress update fails
   - Result: Habit log shows reward was awarded, but progress counter wasn't incremented

**Transaction guarantees**:
- ✅ Both operations succeed together, or both are rolled back
- ✅ No orphaned progress entries with 0 pieces
- ✅ Reward progress always matches habit logs (for current cycle)

### Reward Progress Validation Notes

**IMPORTANT**: Do NOT attempt to validate `pieces_earned` by counting total HabitLogs for recurring multi-piece rewards.

**Why HabitLog count ≠ pieces_earned**:

For recurring rewards (rewards that reset after claiming), HabitLogs accumulate across ALL cycles, while RewardProgress tracks only the CURRENT cycle:

**Example**: "MacBook Pro" (10 pieces required)

```
Cycle 1:
- User earns 10 pieces → 10 HabitLogs created
- User claims reward → pieces_earned=0, claimed=True
- HabitLogs: 10 (still exist)

Cycle 2:
- User earns 3 pieces → 3 new HabitLogs created (total: 13)
- RewardProgress: pieces_earned=3, claimed=False
- HabitLogs: 13 (across all cycles)
```

At this point:
- ✅ `pieces_earned=3` is CORRECT (current cycle)
- ❌ Counting total HabitLogs (13) would be WRONG

**Valid states**:
- `pieces_earned=0, claimed=False, no HabitLogs` → Valid (user will earn reward in future)
- `pieces_earned=0, claimed=True, HAS HabitLogs` → Valid (just claimed, starting new cycle)
- `pieces_earned=N, claimed=False` → Valid (earning progress, current cycle)
- `pieces_earned=0, claimed=False, HAS HabitLogs` → Possibly orphaned, but could be valid if logs are from past claimed cycles

**Do NOT**:
- ❌ Recalculate `pieces_earned` from total HabitLog count (breaks recurring rewards)
- ❌ Delete progress entries with 0 pieces (could be claimed rewards or future rewards)
- ❌ Validate consistency between total logs and current progress (logs span multiple cycles)

**DO**:
- ✅ Use atomic transactions to prevent future corruption
- ✅ Trust existing progress entries as valid
- ✅ Let the system naturally track progress within each cycle

**Files affected**:
- `src/services/habit_service.py:184-205` - Atomic transaction for habit completion
- `src/bot/handlers/habit_revert_handler.py` - Uses transactions for atomic reverts
- Any service that needs multi-step consistency

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

1. **Mock External Dependencies**: Always mock Django repositories and Telegram objects
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

**Status is fully computed in Python** via the `get_status()` method - Never set status manually in code.

### Data Models

All reward models are now in **src/core/models.py** (Django models):

**Reward model**:
- `pieces_required: int` - Required for ALL rewards (IntegerField, default=1)
- `piece_value: float | None` - Monetary value per piece (FloatField, nullable)
- Removed: `is_cumulative` field (no longer needed)
- Removed: `RewardType.CUMULATIVE` enum value

**RewardProgress model**:
- `claimed: bool` - Whether user has claimed this reward (BooleanField, default=False)
- `get_status()` method - Computes status based on pieces_earned and claimed
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
  - Status changes from "Achieved" (N/N) → "Claimed" (0/N) via the `get_status()` method
  - User will see "0/N Claimed" until they earn the next piece
  - When they earn the next piece, `update_reward_progress()` automatically resets `claimed=False`

**Removed methods** (as of Feature 0006):
- `update_cumulative_progress()` - renamed to `update_reward_progress()`
- `mark_reward_completed()` - renamed to `mark_reward_claimed()`
- `set_reward_status()` - status is now fully computed by `get_status()` method

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

**src/core/repositories.py**:

RewardRepository:
- Removed `is_cumulative` field from create/update operations
- `pieces_required` defaults to 1 if not specified

RewardProgressRepository:
- Uses Django ORM `select_related('user', 'reward')` for performance
- Status computed via `get_status()` method (not stored in database)
- Status enum: PENDING, ACHIEVED, CLAIMED

### Bot Handlers

**src/bot/handlers/reward_handlers.py**:
- Use `mark_reward_claimed()` instead of `mark_reward_completed()`
- Status is read-only, computed by `get_status()` method

**src/bot/formatters.py**:
- Always show progress for any reward (not just cumulative)
- Check `pieces_required > 1` instead of `is_cumulative`
- Removed `RewardType.CUMULATIVE` from emoji mapping
- Uses `progress.get_status()` to display current status

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

### Daily Frequency Control (Feature 0014)

**IMPORTANT**: As of Feature 0014, rewards support configurable daily frequency limits to prevent over-awarding. This replaces the old blanket "no reward twice in one day" rule with flexible per-reward configuration.

**New Field**: `Reward.max_daily_claims`
- Type: `IntegerField` (nullable)
- `NULL` or `0` = unlimited (reward can be awarded multiple times per day)
- `1` = once per day maximum (default behavior)
- `2+` = that many pieces per day maximum

**Key Behaviors**:
1. **Piece-based counting**: Daily limit counts individual PIECES awarded, not completions
   - A 5-piece reward with `max_daily_claims=1` can only earn 1 piece per day
   - Takes 5 days minimum to complete
2. **ALL pieces count toward daily limit**: Counts ALL pieces awarded today (both claimed and unclaimed)
   - **CRITICAL BUG FIX (2025-11-05)**: Claimed pieces now count toward the daily limit
   - This prevents users from bypassing `max_daily_claims` by claiming between completions
   - Once daily limit is reached, reward is excluded for the rest of the day regardless of claim status
3. **Lottery exclusion**: Rewards at their daily limit are automatically excluded from selection
4. **Completion blocking**: Rewards that are already completed (pieces_earned >= pieces_required) are also excluded

**Implementation Details**:

**Service Layer** (`src/services/reward_service.py`):
- `get_todays_pieces_by_reward(user_id, reward_id)`: Counts ALL pieces awarded today (claimed or unclaimed)
  - **Fixed in Feature 0014**: Now counts ALL pieces from today's habit_logs, not just unclaimed ones
  - Counts habit_logs where `got_reward=True` and `reward_id` matches
  - This prevents the claim-reset bypass vulnerability
- `select_reward()`: Enhanced with two filtering passes:
  1. **Completion filter**: Exclude rewards where `pieces_earned >= pieces_required`
  2. **Daily limit filter**: For each reward with `max_daily_claims > 0`:
     - Count today's pieces (all) using `get_todays_pieces_by_reward()`
     - Exclude if count >= max_daily_claims
- `mark_reward_claimed()`: Now resets `pieces_earned=0` when claiming
  - Sets both `claimed=True` and `pieces_earned=0`
  - This allows the reward to start fresh after claiming

**Simplified Exclusion Logic** (`src/services/habit_service.py`):
```python
# Old way (pre-Feature 0014):
todays_awarded_rewards = await self.reward_service.get_todays_awarded_rewards(user.id)
selected_reward = await self.reward_service.select_reward(
    total_weight=total_weight,
    user_id=user.id,
    exclude_reward_ids=todays_awarded_rewards  # Manual exclusion
)

# New way (post-Feature 0014):
selected_reward = await self.reward_service.select_reward(
    total_weight=total_weight,
    user_id=user.id,
    exclude_reward_ids=[]  # No manual exclusion - handled internally
)
```

**Admin Interface** (`src/core/admin.py`):
- `max_daily_claims` field added to Reward admin list_display
- New fieldset "Daily Frequency Control" with help text
- Description: "Leave empty or set to 0 for unlimited daily claims"

**Migration**: `src/core/migrations/0002_add_reward_daily_limits.py`
- Adds `max_daily_claims` field (nullable)
- Existing rewards default to NULL (unlimited) to maintain backward compatibility

**Example Scenarios**:
1. **Unlimited reward** (`max_daily_claims=NULL`): Can be earned multiple times per day with no restrictions
2. **Once-per-day reward** (`max_daily_claims=1`, `pieces_required=1`): Classic "once daily" reward
3. **Multi-piece limited** (`max_daily_claims=1`, `pieces_required=5`): Earn 1 piece/day, takes 5 days to complete
4. **Unlimited multi-piece** (`max_daily_claims=NULL`, `pieces_required=10`): Can earn all 10 pieces in one day if lucky

**Important Notes**:
- **CRITICAL**: The daily counter counts ALL pieces (claimed and unclaimed) to prevent bypass
- Once a reward reaches its daily limit, it CANNOT be earned again that day (even after claiming)
- This prevents users from exploiting `max_daily_claims=1` by claiming between completions
- Completed but unclaimed rewards are excluded from lottery (ACHIEVED status)
- Status computation via `get_status()` is unaffected by daily limits

**Bug Fix History**:
- **2025-11-05**: Fixed blocking bug where `get_todays_pieces_by_reward()` returned 0 for CLAIMED rewards
  - Previous behavior: Claiming freed up the daily slot, allowing bypass of `max_daily_claims`
  - New behavior: ALL pieces awarded today count, regardless of claim status
  - Impact: Properly enforces daily limits as specified in Feature 0014 plan

**Files Modified**:
- `src/core/models.py` - Added `max_daily_claims` field to Reward model
- `src/models/reward.py` - Added `max_daily_claims` to Pydantic Reward model
- `src/services/reward_service.py` - Added `get_todays_pieces_by_reward()`, modified `select_reward()` and `mark_reward_claimed()`
- `src/services/habit_service.py` - Simplified to remove manual exclusion list
- `src/core/admin.py` - Added `max_daily_claims` to RewardAdmin interface
- `src/core/migrations/0002_add_reward_daily_limits.py` - Database migration

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
# Check progress status (computed by get_status() method)
if progress.get_status() == RewardStatus.ACHIEVED:
    # User can claim this reward
    pass
```

### Files Modified in Feature 0005 (Historical - Unified Reward System)

**Note**: These changes were later migrated from Airtable Pydantic models to Django ORM models (Feature 0009).

- `src/core/models.py` - Reward and RewardProgress Django models with claimed field and get_status() method
- `src/core/repositories.py` - Updated field handling for Django ORM
- `src/services/reward_service.py` - Renamed methods (`mark_reward_claimed()`), fixed claiming logic
- `src/services/habit_service.py` - Always update progress for all rewards
- `src/bot/formatters.py` - Removed cumulative conditionals, uses get_status()
- `src/bot/handlers/reward_handlers.py` - Updated method names, deprecated set_status

See `docs/features/0005_PLAN.md` for full implementation details.

### Feature 0006: Removed /set_reward_status Command

**Date**: 2025-10-20

**Reason**: The `/set_reward_status` command became obsolete after Feature 0005 unified the reward system. Reward status is now fully computed by the `get_status()` method based on `pieces_earned`, `pieces_required`, and `claimed` fields. Manual status updates are no longer needed or supported.

**Files Modified**:
- `src/bot/main.py` - Removed command handler registration and import
- `src/bot/handlers/reward_handlers.py` - Removed `set_reward_status_command()` function (lines 256-330)
- `src/bot/messages.py` - Removed `HELP_SET_STATUS_USAGE` constant and all references to `/set_reward_status` in help text (English, Russian, Kazakh)

**Migration Path**: Users should use `/claim_reward` to mark achieved rewards as claimed. Status changes automatically based on progress.

### Post-Habit-Creation UX Pattern

**CRITICAL**: After successfully creating a habit via `/add_habit`, immediately show a menu displaying all habits (including the newly created one) with action buttons to improve user experience.

**Implementation Pattern**:

```python
# In habit_confirmed() after creating habit
created_habit = await habit_repository.create(new_habit)
logger.info(f"✅ Created habit '{created_habit.name}' (ID: {created_habit.id})")

# Show success message
success_message = msg('SUCCESS_HABIT_CREATED', lang, name=created_habit.name)
await query.edit_message_text(success_message, parse_mode="HTML")

# Fetch all active habits including the newly created one
all_habits = await habit_repository.get_all_active()

# Show the post-creation menu with habits list
keyboard = build_post_create_habit_keyboard(all_habits, lang)
next_message = msg('HELP_HABIT_CREATED_NEXT', lang)

# Send as a new message to show the habits list
await query.message.reply_text(
    next_message,
    reply_markup=keyboard,
    parse_mode="HTML"
)
```

**Post-Creation Menu Options**:
1. **Display habits** - Shows all active habits as non-interactive list items (using `view_habit_*` callbacks)
2. **➕ Add Another** - Starts `/add_habit` flow again (`post_create_add_another` callback)
3. **✏️ Edit Habit** - Opens edit habit menu (`menu_habits_edit` callback)
4. **« Back** - Returns to habits menu (`menu_back_habits` callback)

**Keyboard Builder**:
- `build_post_create_habit_keyboard(habits, language)` in `src/bot/keyboards.py`
- Displays habits with name and category (if available)
- Provides quick access to common next actions

**Callback Handlers**:
- `post_create_add_another` → Handled by `post_create_add_another_callback()` in habit_management_handler
- `view_habit_*` → Handled by `view_habit_display_callback()` in menu_handler (display only, no action)
- `menu_habits_edit` → Handled by existing edit_habit_conversation
- `menu_back_habits` → Handled by `open_habits_menu_callback()` in menu_handler

**Files Modified** (Feature: Post-Creation Habit Menu):
- `src/bot/messages.py` - Added `HELP_HABIT_CREATED_NEXT` message constant (English, Russian, Kazakh)
- `src/bot/keyboards.py` - Added `build_post_create_habit_keyboard()` function
- `src/bot/handlers/habit_management_handler.py` - Modified `habit_confirmed()` to show post-creation menu, added `post_create_add_another_callback()` handler
- `src/bot/handlers/menu_handler.py` - Added `view_habit_display_callback()` and `menu_back_habits` callback handler

**Why This Pattern**:
1. **Immediate feedback** - User sees their new habit in the context of all their habits
2. **Reduced friction** - Quick access to add more habits or edit existing ones
3. **Better UX** - Natural flow from creation to management
4. **Visibility** - User can see all their habits at once after adding a new one

### Post-Habit-Removal UX Pattern

**CRITICAL**: After successfully removing a habit via `/remove_habit`, immediately show the Habits menu to provide quick access to other habit management actions.

**Implementation Pattern**:

```python
# In habit_remove_confirmed() after removing habit
removed_habit = await habit_repository.soft_delete(habit_id)
logger.info(f"✅ Soft deleted habit '{removed_habit.name}' (ID: {removed_habit.id})")

# Show success message
success_message = msg('SUCCESS_HABIT_REMOVED', lang, name=habit_name)
await query.edit_message_text(success_message, parse_mode="HTML")

# Show Habits menu after successful removal
from src.bot.keyboards import build_habits_menu_keyboard
await query.message.reply_text(
    msg('HABITS_MENU_TITLE', lang),
    reply_markup=build_habits_menu_keyboard(lang),
    parse_mode="HTML"
)
logger.info(f"📤 Sent Habits menu to {telegram_id}")
```

**Habits Menu Options**:
1. **➕ Add Habit** - Create a new habit (`menu_habits_add` callback)
2. **✏️ Edit Habit** - Edit an existing habit (`menu_habits_edit` callback)
3. **🗑 Remove Habit** - Remove another habit (`menu_habits_remove` callback)
4. **« Back** - Return to main menu (`menu_back_start` callback)

**Files Modified** (Feature: Post-Removal Habits Menu):
- `src/bot/handlers/habit_management_handler.py` - Modified `habit_remove_confirmed()` to show Habits menu after successful removal

**Why This Pattern**:
1. **Seamless flow** - User can immediately perform another habit management action
2. **No dead ends** - Always provides next steps after completing an action
3. **Consistency** - Matches post-creation pattern for unified UX
4. **Efficiency** - Reduces navigation steps for users managing multiple habits

### Cancel Button Pattern for Habit Flows

**CRITICAL**: All habit creation and editing flows must include a **Cancel** button on inline keyboards, allowing users to abort the operation and return to the Habits menu without typing `/cancel`.

**Implementation Pattern**:

All inline keyboards in habit flows should include a Cancel button:
- Weight selection keyboard
- Category selection keyboard
- Confirmation keyboard

```python
# Add Cancel button to any inline keyboard in habit flows
keyboard.append([
    InlineKeyboardButton(
        text=msg('MENU_CANCEL', language),
        callback_data="cancel_habit_flow"
    )
])
```

**Cancel Handler**:
```python
async def cancel_habit_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel button click during habit creation/editing."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    # Show cancellation message
    await query.edit_message_text(
        msg('INFO_HABIT_CANCEL', lang),
        parse_mode="HTML"
    )

    # Show Habits menu
    from src.bot.keyboards import build_habits_menu_keyboard
    await query.message.reply_text(
        msg('HABITS_MENU_TITLE', lang),
        reply_markup=build_habits_menu_keyboard(lang),
        parse_mode="HTML"
    )

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END
```

**Register in Conversation States**:

Add the cancel handler to all relevant states in both `/add_habit` and `/edit_habit` conversations:

```python
states={
    AWAITING_HABIT_WEIGHT: [
        CallbackQueryHandler(habit_weight_selected, pattern="^weight_"),
        CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
    ],
    AWAITING_HABIT_CATEGORY: [
        CallbackQueryHandler(habit_category_selected, pattern="^category_"),
        CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
    ],
    AWAITING_HABIT_CONFIRMATION: [
        CallbackQueryHandler(habit_confirmed, pattern="^confirm_(yes|no)$"),
        CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
    ]
}
```

**Note on Text Input Steps**:
For steps where users type text (habit name input), keep the `/cancel` command as the cancellation method. Adding an inline keyboard with just a Cancel button to text input prompts can be intrusive to the user experience.

**Message Constant**:
- `MENU_CANCEL = "✖ Cancel"` (English)
- `MENU_CANCEL = "✖ Отмена"` (Russian)
- `MENU_CANCEL = "✖ Болдырмау"` (Kazakh)

**Files Modified** (Feature: Cancel Button in Habit Flows):
- `src/bot/messages.py` - Added `MENU_CANCEL` message constant (3 languages)
- `src/bot/keyboards.py` - Added Cancel button to `build_weight_selection_keyboard()`, `build_category_selection_keyboard()`, `build_habit_confirmation_keyboard()`
- `src/bot/handlers/habit_management_handler.py` - Added `cancel_habit_flow_callback()` handler and registered it in both conversation states

**Why This Pattern**:
1. **Better UX** - Users don't need to remember or type `/cancel` command
2. **Consistency** - Inline buttons match the rest of the conversation flow
3. **Clear exit path** - Obvious way to abort operation at any step
4. **Direct navigation** - Returns user directly to Habits menu (not just ending conversation)

### Menu Callback Entry Points for ConversationHandler

**CRITICAL**: All conversation handlers that can be triggered from inline menu buttons MUST register BOTH the command handler AND the callback handler as entry points.

**The Problem**:
When a conversation handler only has a command as entry point, clicking a menu button that's supposed to start the conversation will be received by the webhook but will have no handler. The callback is logged, returns 200 OK, but nothing happens for the user.

**Example of Broken Pattern**:
```python
# ❌ BAD - Only command entry point
claim_reward_conversation = ConversationHandler(
    entry_points=[CommandHandler("claim_reward", claim_reward_command)],
    ...
)
# User clicks "menu_rewards_claim" button → callback received → no handler → nothing happens
```

**Correct Pattern**:
```python
# ✅ GOOD - Both command and menu callback entry points
claim_reward_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("claim_reward", claim_reward_command),
        CallbackQueryHandler(menu_claim_reward_callback, pattern="^menu_rewards_claim$")
    ],
    states={
        AWAITING_REWARD_SELECTION: [
            CallbackQueryHandler(claim_reward_callback, pattern="^claim_reward_"),
            CallbackQueryHandler(claim_back_callback, pattern="^menu_back$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_claim_handler)]
)
```

**Implementation Pattern**:

Create a menu callback version of the command handler:
```python
async def menu_claim_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point when reward claim starts from menu callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received menu_rewards_claim callback from user {telegram_id} (@{username})")

    # Same validation and logic as command handler...
    # BUT use query.edit_message_text() instead of update.message.reply_text()

    return AWAITING_FIRST_STATE
```

**Key Differences from Command Handler**:
1. **Gets query from callback**: `query = update.callback_query`
2. **Answers callback**: `await query.answer()` (required to remove loading state)
3. **Edits existing message**: `await query.edit_message_text(...)` instead of `update.message.reply_text(...)`
4. **Otherwise identical**: Same validation, same business logic, same return state

**Files Modified** (Bug Fix: Menu Callback Entry Point for Claim Reward):
- `src/bot/handlers/reward_handlers.py:252-312` - Added `menu_claim_reward_callback()` function
- `src/bot/handlers/reward_handlers.py:1059-1061` - Added callback handler as second entry point to `claim_reward_conversation`

**Why This Matters**:
1. **Consistency** - Users can start conversations both from commands and menu buttons
2. **UX** - Menu-driven navigation works as expected
3. **No silent failures** - Callbacks don't just disappear into the void
4. **Debugging** - Clear log messages distinguish command vs callback entry

**Other Conversations Following This Pattern**:
- `add_reward_conversation` - Has both `/add_reward` command and `menu_rewards_add` callback entry points

## Docker Deployment Configuration

**CRITICAL**: Certbot is NOT run as a continuous service to avoid port conflicts with nginx.

### Port Conflict Issue (Fixed 2025-11-16)

**Problem**: The `certbot/certbot` Docker image exposes ports 80/443 internally, which caused conflicts when nginx tried to bind to the same ports. This prevented nginx from starting even though certbot wasn't publishing ports to the host.

**Solution**: Removed certbot service from docker-compose files. SSL certificates should be managed manually when needed.

**SSL Certificate Management**:

**Initial certificate issuance** (one-time):
```bash
# Stop nginx temporarily
cd /home/deploy/habit_reward_bot/docker
docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml stop nginx

# Obtain certificate using standalone mode
docker run --rm -p 80:80 \
  -v certbot_data:/etc/letsencrypt \
  certbot/certbot certonly \
  --standalone \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com

# Start nginx again
docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml start nginx
```

**Certificate renewal** (every ~60 days):
```bash
# Nginx should be running (uses webroot method)
docker run --rm \
  -v certbot_data:/etc/letsencrypt \
  -v certbot_www:/var/www/certbot \
  certbot/certbot renew
```

**Files Modified** (Fix: Certbot Port Conflict):
- `deployment/docker/docker-compose.yml` - Removed certbot service definition
- `deployment/docker/docker-compose.prod.yml` - Removed certbot service overrides
- `deployment/scripts/deploy.sh` - Removed certbot from startup and cleanup commands

**Why Manual Certbot**:
1. **No port conflicts** - Certbot doesn't compete with nginx for ports 80/443
2. **Simpler deployment** - One less service to manage
3. **Sufficient frequency** - Certificates last 90 days, manual renewal every 60 days is acceptable
4. **Deployment portability** - Works on servers with limited resources

## Simplified Deployment with Caddy (Recommended)

**Date**: 2025-11-16
**Status**: Preferred deployment method

As an alternative to the nginx-based deployment, a simplified 2-container setup using Caddy is available. This approach eliminates manual SSL certificate management and simplifies the deployment process.

### Architecture

**Containers**:
1. **Web**: Django + Telegram Bot + SQLite (single application container)
2. **Caddy**: Automatic HTTPS reverse proxy

### Key Benefits

1. **Automatic SSL**: Caddy obtains and renews Let's Encrypt certificates automatically
2. **No Manual Certificate Management**: No certbot commands or renewal scripts needed
3. **Simpler Configuration**: 15-line Caddyfile vs 100+ line nginx config
4. **Bind Mounts for Data**: Database at explicit path `/home/deploy/habit_reward_bot/data/db.sqlite3`
5. **SQLite Database**: Single-file database, easy backups with simple `cp` command
6. **No Port Conflicts**: Caddy handles both HTTP/HTTPS cleanly in one container

### Files

**Deployment Files**:
- `deployment/caddy/Caddyfile` - Caddy configuration (automatic HTTPS)
- `deployment/docker/docker-compose.caddy.yml` - 2-service compose file
- `deployment/docker/Dockerfile.simple` - Optimized multi-stage Dockerfile
- `deployment/scripts/deploy-caddy.sh` - Manual deployment script
- `.env.caddy.example` - Environment variables template

**CI/CD**:
- `.github/workflows/deploy-caddy.yml` - Automated deployment workflow

### Deployment Commands

**First-time deployment**:
```bash
# On VPS
cd /home/deploy/habit_reward_bot
mkdir -p data staticfiles
cd docker
docker-compose --env-file ../.env -f docker-compose.caddy.yml up -d
```

**Updates** (automatic via GitHub Actions):
```bash
git push origin main  # Triggers automatic build and deployment
```

**Manual deployment**:
```bash
cd /home/deploy/habit_reward_bot
./deployment/scripts/deploy-caddy.sh
```

### Data Persistence

**Bind Mounts** (explicit host paths):
```yaml
volumes:
  - ./data:/app/data              # SQLite database
  - ./staticfiles:/app/staticfiles  # Static files
```

**Database Location**: `/home/deploy/habit_reward_bot/data/db.sqlite3`

**Backup Strategy**:
```bash
# Simple file copy (no Docker commands needed)
cp data/db.sqlite3 backups/db_$(date +%Y%m%d).sqlite3
```

**Important**: Data persists across container rebuilds because bind mounts are independent of container images.

### SSL Certificate Management

**Fully Automatic**:
- Caddy obtains SSL certificate on first HTTPS request
- Auto-renewal happens 30 days before expiry
- No manual intervention required
- Certificates stored in `caddy_data` Docker volume

**Verification**:
```bash
# Check SSL certificate
echo | openssl s_client -servername habitreward.duckdns.org \
  -connect habitreward.duckdns.org:443 2>/dev/null | \
  openssl x509 -noout -dates
```

### Security: Domain Blocking

**Date**: 2025-11-20

**Problem**: Public servers receive constant automated attacks and scanners. Without domain restrictions, any domain pointing to your IP address can use your server (domain fronting attack).

**Solution**: Caddy catch-all block to reject all requests except legitimate domains.

**Configuration** (`deployment/caddy/Caddyfile`):
```caddy
# Your legitimate domains first
habitreward.duckdns.org { ... }
www.habitreward.duckdns.org { ... }

# Catch-all MUST come last - blocks everything else
:80, :443 {
    respond "Domain not configured" 444
    log {
        output file /var/log/caddy/blocked.log
        format console
    }
}
```

**What this blocks**:
- Direct IP access (http://206.189.40.240)
- Unknown domains pointing to your IP (e.g., furnicraft.lk)
- Attack attempts to /goform/, /cgi-bin/, /HNAP1/ (router exploits)
- Domain fronting attempts

**Important**: The catch-all (`:80, :443`) must come AFTER your legitimate domain blocks, otherwise it will intercept everything.

### Health Check Logs

**Expected Behavior**: You will see frequent requests to `/admin/login/` in logs:
```
INFO: 172.18.0.3:53114 - "GET /admin/login/ HTTP/1.1" 200 OK  # Caddy healthcheck
INFO: 127.0.0.1:53190 - "GET /admin/login/ HTTP/1.1" 200 OK   # Docker healthcheck
```

**Why**: Two health checks run every 30 seconds:
1. **Docker healthcheck** (127.0.0.1) - Verifies container is healthy
2. **Caddy healthcheck** (172.18.0.3) - Verifies reverse proxy target is responding

**Action**: No action needed - these logs confirm your application is healthy. This is normal and expected behavior.

### Comparison: nginx vs Caddy

| Aspect | nginx (Old) | Caddy (New) |
|--------|------------|-------------|
| Containers | 3 (db, web, nginx) | 2 (web, caddy) |
| SSL Setup | Manual certbot | Automatic |
| SSL Renewal | Manual commands | Automatic |
| Config Lines | 100+ | 15 |
| Database | PostgreSQL | SQLite |
| Backup | pg_dump | File copy |
| Port Conflicts | Had issues | None |

### Migration from nginx to Caddy

See detailed plan: `docs/simple-deployment/PLAN.md`

**Quick migration**:
1. Backup PostgreSQL data: `docker-compose exec db pg_dump...`
2. Stop old containers: `docker-compose down`
3. Start Caddy setup: `docker-compose -f docker-compose.caddy.yml up -d`
4. Caddy automatically provisions SSL certificate

### When to Use nginx vs Caddy

**Use Caddy (Recommended)**:
- New deployments
- Simplicity is priority
- Don't want to manage SSL manually
- Low to medium traffic (< 1000 requests/min)

**Use nginx**:
- Already deployed and working
- Need advanced nginx features (rate limiting, complex routing)
- Very high traffic requirements
- Prefer PostgreSQL over SQLite

**Files Modified** (Feature: Simplified Caddy Deployment):
- Added `deployment/caddy/Caddyfile` - Caddy configuration
- Added `deployment/docker/docker-compose.caddy.yml` - 2-container setup
- Added `deployment/docker/Dockerfile.simple` - Optimized Dockerfile
- Added `.github/workflows/deploy-caddy.yml` - Automated CI/CD
- Added `.env.caddy.example` - Environment template
- Added `deployment/scripts/deploy-caddy.sh` - Manual deployment
- Added `docs/simple-deployment/PLAN.md` - Detailed implementation plan

## Bot Audit Logging

**CRITICAL**: All high-level Telegram bot interactions are logged to the `BotAuditLog` model for debugging data corruption issues and user support. The audit trail captures event snapshots, retains logs for 90 days, and provides helper methods to trace event timelines.

### When to Use Audit Logging

Use `audit_log_service` to log the following high-level events:

1. **Commands** - User executes bot commands (`/start`, `/help`, `/habit_done`, etc.)
2. **Habit Completions** - User completes a habit and earns reward piece
3. **Reward Claims** - User claims an achieved reward
4. **Reward Reverts** - Habit completion is reverted, rolling back reward progress
5. **Button Clicks** - User clicks inline keyboard buttons (for significant state changes only)
6. **Errors** - Exceptions and errors during user interactions

**Do NOT log**:
- Low-level operations (database queries, service calls)
- Intermediate conversation states
- Every button click (only significant ones)
- Internal system operations

### Implementation Pattern

**Service Layer** (`src/services/audit_log_service.py`):

All audit logging goes through the centralized `audit_log_service`:

```python
from src.services.audit_log_service import audit_log_service
from src.utils.async_compat import maybe_await

# Log command execution
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
            "total_weight": total_weight,
            "selected_reward_name": selected_reward.name if got_reward else None,
            "reward_progress": {
                "pieces_earned": progress.pieces_earned,
                "pieces_required": progress.get_pieces_required(),
                "claimed": progress.claimed,
            } if progress else None
        }
    )
)

# Log reward claim
await maybe_await(
    audit_log_service.log_reward_claim(
        user_id=user.id,
        reward=reward,
        progress_snapshot={
            "reward_name": reward.name,
            "pieces_earned_before": pieces_required,
            "pieces_earned_after": 0,
            "claimed": True,
        }
    )
)

# Log errors
await maybe_await(
    audit_log_service.log_error(
        user_id=user.id,
        error_message=f"Error claiming reward: {str(e)}",
        context={
            "command": "claim_reward",
            "reward_id": reward_id,
            "reward_name": reward_name,
        }
    )
)

# Log button clicks (only for significant state changes)
await maybe_await(
    audit_log_service.log_button_click(
        user_id=user.id,
        callback_data=callback_data,
        snapshot={"context": "habit_selection"}
    )
)
```

### Snapshot Structure

Snapshots are JSON objects capturing state at the time of the event. Use consistent keys:

**Habit Completion Snapshot**:
```json
{
  "habit_name": "Morning Exercise",
  "streak_count": 5,
  "total_weight": 55.0,
  "selected_reward_name": "Coffee break",
  "reward_progress": {
    "pieces_earned": 3,
    "pieces_required": 5,
    "claimed": false
  }
}
```

**Reward Claim Snapshot**:
```json
{
  "reward_name": "Coffee break",
  "pieces_earned_before": 5,
  "pieces_earned_after": 0,
  "claimed": true
}
```

**Error Context Snapshot**:
```json
{
  "command": "claim_reward",
  "reward_id": "123",
  "reward_name": "Coffee break",
  "error_type": "ValueError"
}
```

### Integration Points

**Files Modified** (Feature 0015: Bot Audit Log System):

1. **Data Layer**:
   - `src/core/models.py:301-392` - Added `BotAuditLog` model with EventType choices
   - `src/core/migrations/0003_add_bot_audit_log.py` - Database migration

2. **Service Layer**:
   - `src/services/audit_log_service.py` - Created `AuditLogService` with all logging methods

3. **Integration**:
   - `src/services/habit_service.py:19,43,209-232,334-354` - Log habit completions and reward reverts
   - `src/bot/handlers/reward_handlers.py:16,306-319,347-358` - Log reward claims and errors
   - `src/bot/handlers/command_handlers.py:14,85-92,140-147` - Log command executions

4. **Admin & Maintenance**:
   - `src/core/admin.py:5,168-204` - Registered `BotAuditLogAdmin` (read-only)
   - `src/core/management/commands/cleanup_audit_logs.py` - Daily cleanup command

### Querying Audit Logs

Use service helper methods to query logs for debugging:

```python
# Get user's event timeline (last 24 hours)
timeline = await maybe_await(
    audit_log_service.get_user_timeline(
        user_id=user.id,
        hours=24
    )
)

# Trace reward corruption (all events for specific reward)
events = await maybe_await(
    audit_log_service.trace_reward_corruption(
        user_id=user.id,
        reward_id=reward.id
    )
)

# Each log entry has:
# - timestamp: When event occurred
# - event_type: Type of event (COMMAND, HABIT_COMPLETED, etc.)
# - snapshot: State at time of event
# - Related objects: user, habit, reward, habit_log (via ForeignKeys)
```

### Django Admin Interface

Audit logs are accessible via Django admin at `/admin/core/botauditlog/`:

- **List View**: timestamp, user, event_type, command, habit, reward
- **Filters**: event_type, timestamp (date hierarchy)
- **Search**: user telegram_id, command, error_message
- **Read-Only**: Cannot add or edit logs (created automatically)
- **Deletion**: Only superusers can delete (for cleanup)

### Retention Policy & Cleanup

**Retention Period**: 90 days (configurable)

**Automatic Cleanup**: Run daily via cron:

```bash
# Add to crontab
0 2 * * * cd /path/to/project && python manage.py cleanup_audit_logs

# Manual cleanup with custom retention
python manage.py cleanup_audit_logs --days 60
```

The cleanup command:
- Calculates cutoff date (90 days ago from now)
- Deletes `BotAuditLog` entries with `timestamp < cutoff_date`
- Outputs count of deleted records
- Logs completion to application logs

### Debugging Data Corruption Example

**Problem**: User reports "MacBook Pro: 0/10 pieces, no logs" - orphaned progress entry

**Investigation**:

```python
# 1. Get user's reward timeline
events = await audit_log_service.trace_reward_corruption(
    user_id=user.id,
    reward_id=macbook_reward.id
)

# 2. Review snapshots chronologically
for event in events:
    print(f"{event.timestamp}: {event.event_type}")
    print(f"  Snapshot: {event.snapshot}")

# Example output might show:
# 2025-11-18 10:00: HABIT_COMPLETED
#   Snapshot: {"reward_progress": {"pieces_earned": 0, ...}}
# --> This shows progress was created with 0 pieces
# --> Check if corresponding habit_log was created (event.habit_log)
# --> If habit_log is None, this indicates transaction rollback issue
```

**Root Cause**: Audit log reveals `pieces_earned=0` at creation time with no linked `habit_log`, indicating the atomic transaction failed between progress creation and log creation.

**Fix**: Implemented in Feature 0015 - wrapped both operations in `transaction.atomic()` (see `src/services/habit_service.py:184-205`).

### Why Audit Logging Matters

1. **Data Corruption Detection**: Trace exact sequence of events leading to inconsistent state
2. **User Support**: Reconstruct user's interaction history for troubleshooting
3. **Debugging**: See actual state snapshots at time of each event
4. **Performance**: Identify slow operations or bottlenecks
5. **Security**: Track unauthorized access or suspicious activity patterns

See `docs/features/0015_PLAN.md` for full implementation details.
