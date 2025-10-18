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

## Repository Pattern

All database operations go through repository classes in `src/airtable/repositories.py`:
- `user_repository` - User CRUD operations
- `habit_repository` - Habit CRUD operations
- `habit_log_repository` - Habit log CRUD operations
- `reward_repository` - Reward CRUD operations
- `reward_progress_repository` - Reward progress CRUD operations

Never query Airtable directly from handlers or services. Always use the repository layer.

## Service Layer

Business logic lives in services (`src/services/`):
- `habit_service.py` - Orchestrates habit completion flow
- `streak_service.py` - Calculates streaks
- `reward_service.py` - Handles reward selection and cumulative progress
- `nlp_service.py` - NLP-based habit classification

Services coordinate between repositories and contain no direct Airtable calls.

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
