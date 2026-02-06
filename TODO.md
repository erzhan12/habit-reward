# TODO: Future Features & Improvements

This document tracks planned features, improvements, and enhancements for the Habit Reward System.

## 🎯 Core Habit System Features

### High Priority



## 🔧 Admin Panel Improvements

### High Priority

- [ ] **Bulk Operations in Admin**
  - Add bulk edit capabilities for habits (e.g., change weight, category, active status)
  - Add bulk operations for users (e.g., activate/deactivate multiple users)
  - **File**: `src/core/admin.py`

- [ ] **Admin Filters & Search Improvements**
  - Add more granular filters for HabitLog (e.g., filter by reward type, date range)
  - Improve search to support partial matches and multiple fields simultaneously
  - Add custom admin views for analytics (e.g., completion rates, reward distribution)

### Medium Priority

- [ ] **Admin Dashboard Widgets**
  - Add dashboard widgets showing key metrics (total users, active habits, completion rates)
  - Display recent activity feed
  - Show system health indicators

- [ ] **Export Functionality**
  - Add ability to export habit logs, user data, reward progress as CSV/JSON
  - Useful for backups and data analysis

## 🤖 Bot Features

### High Priority

- [ ] **Guaranteed Reward on Last Daily Habit**
  - When user completes their last remaining habit for the day, they should receive a 100% guaranteed reward with no "No reward" option
  - **Problem**: Currently even the final habit completion shows a chance to get "No reward", which feels unrewarding for completing all daily habits
  - **Solution**: Detect when a habit is the last one for the day and guarantee a reward
    - Check if this is the final incomplete habit for today before marking it done
    - If yes, calculate reward with 100% success rate (skip the random "No reward" chance)
    - If no, use normal reward calculation logic
  - **Implementation approach**:
    - Modify reward calculation logic to accept a `guaranteed` flag
    - Update habit completion handler to check if this is the last habit for today
    - Pass `guaranteed=True` to reward calculation when it's the final habit
    - Update reward message/presentation accordingly
  - **Files**:
    - `src/bot/handlers/reward_handlers.py` - Add check for last habit and guaranteed flag
    - `src/services/reward_service.py` - Update reward calculation to support guaranteed rewards
    - `src/bot/messages.py` - Update reward presentation messages
  - **Related**: User motivation and reward system enhancement

- [ ] **Add Confirmation Message for "Yesterday" Habit Completion**
  - When a user marks a habit as done for "yesterday", there is no confirmation message — it logs immediately
  - The "for date" option already shows a confirmation message before logging
  - **Problem**: Inconsistent UX — "for date" has confirmation but "yesterday" does not, which can lead to accidental logging
  - **Solution**: Add the same confirmation message used by "for date" to the "yesterday" option
    - Show confirmation only for past dates (not for today)
    - Use the same message format and flow as the existing "for date" confirmation
    - After user confirms, proceed with the same reward calculation and success flow as "for date"
  - **Files**:
    - `src/bot/handlers/habit_done_handler.py` - Add confirmation step for "yesterday" option
    - `src/bot/messages.py` - Reuse existing "for date" confirmation message

### Medium Priority

- [ ] **Auto-delete Habit Name Message on Creation, Reward Name on creation and API Key name on creation**
  - When a user creates a new habit, the message that shows the habit name/title should be auto-deleted or replaced
  - When a user creates a new reward, the message that shows the reward name/title should be auto-deleted or replaced
  - When a user creates a new API key, the message that shows the API key name/title should be auto-deleted or replaced
  - **Reason**: Keep the chat clean and avoid lingering habit name messages
  - **File**: `src/bot/handlers/habit_management_handler.py`

- [ ] **Habit Reminders**
  - Scheduled reminders for pending habits
  - Configurable reminder times per user
  - **File**: New handler `src/bot/handlers/reminder_handler.py`

- [ ] **Habit Statistics & Insights**
  - Weekly/monthly completion statistics
  - Streak visualization
  - Most completed habits, completion rate trends
  - **File**: `src/bot/handlers/stats_handler.py`

- [ ] **Habit Templates**
  - Pre-defined habit templates users can add (e.g., "Morning Routine", "Fitness")
  - Quick setup for new users
  - **File**: `src/bot/handlers/habit_management_handler.py`

- [ ] **Multi-language Support Expansion**
  - Add more languages beyond current set
  - Community-contributed translations
  - **File**: `src/bot/messages.py`, `src/bot/language.py`

### Low Priority

- [ ] **Undo Button for Recent Completions**
  - Add inline "Undo" button that appears after completing a habit (within 5 minutes)
  - Quick way to revert accidental completions without using `/revert_habit` command
  - **File**: `src/bot/handlers/habit_done_handler.py`

- [ ] **Habit Completion Confirmation**
  - Add confirmation step for habit completion to prevent accidental logging
  - Optional setting users can enable/disable
  - **File**: `src/bot/handlers/habit_done_handler.py`, `src/bot/messages.py`

- [ ] **Bulk Habit Completion**
  - Allow users to mark multiple habits as done at once
  - Useful for users with many daily habits
  - **File**: `src/bot/handlers/habit_done_handler.py`

## 📊 Analytics & Reporting

- [ ] **User Analytics Dashboard**
  - Completion rates over time
  - Reward claim patterns
  - Streak analysis
  - **File**: New `src/dashboard/analytics.py`

- [ ] **Habit Performance Metrics**
  - Which habits are most/least completed
  - Average completion time
  - Drop-off rates
  - **File**: New service `src/services/analytics_service.py`

- [ ] **Reward Effectiveness Analysis**
  - Which rewards motivate users most
  - Correlation between reward types and completion rates
  - **File**: New analytics module

## 🔐 Security & Performance

- [ ] **Rate Limiting**
  - Add rate limiting to prevent abuse
  - Protect API endpoints and bot commands
  - **File**: Middleware or decorator

- [ ] **Audit Logging**
  - Track all admin actions (who changed what, when)
  - Track critical user actions (deletions, reversions)
  - **File**: New `src/core/audit.py`

- [ ] **Database Query Optimization**
  - Review and optimize slow queries
  - Add database indexes where needed
  - **File**: `src/core/models.py`, `src/core/repositories.py`

- [ ] **Caching Layer**
  - Cache frequently accessed data (user settings, active habits)
  - Reduce database load
  - **File**: New `src/utils/cache.py`

- [ ] **Self-delete API Key Messages**
  - After generating an API key via the bot, the message containing the key should auto-delete after 10 minutes
  - **Reason**: Security; prevent API keys from lingering in chat history


## 🧪 Testing & Quality

- [ ] **Integration Tests**
  - End-to-end tests for complete user flows
  - Test bot interactions with real Telegram API (test mode)
  - **File**: `tests/test_integration.py`

- [ ] **Load Testing**
  - Test system under high load
  - Identify bottlenecks
  - **File**: New `tests/load/`

- [ ] **Coverage Improvements**
  - Increase test coverage to 90%+
  - Focus on edge cases and error handling
  - **File**: Various test files

## 🌐 Multi-Platform Features

### Web Dashboard Enhancements

- [ ] **Interactive Habit Calendar**
  - Visual calendar showing completion history
  - Click to mark habits as done
  - **File**: `src/dashboard/components/calendar.py`

- [ ] **Reward Progress Visualization**
  - Progress bars, charts for reward progress
  - Visual feedback for users
  - **File**: `src/dashboard/components/rewards.py`

- [ ] **User Profile Management**
  - Edit profile, change settings via web interface
  - Link/unlink Telegram account
  - **File**: New dashboard pages

### API Development

- [ ] **API Authentication**
  - JWT token-based authentication
  - OAuth2 support
  - **File**: New `src/api/auth.py`

## 📱 Mobile App Features (Future)

- [ ] **Native iOS App**
  - Native UI for habit tracking
  - Push notifications
  - Offline support
  - **Related**: See `docs/MULTI_PLATFORM_ROADMAP.md`

- [ ] **Telegram Mini App**
  - Inline web app within Telegram
  - Rich UI for habit management
  - **Related**: See `docs/MULTI_PLATFORM_ROADMAP.md`

## 🛠️ Developer Experience

- [ ] **Development Documentation**
  - API documentation
  - Architecture diagrams
  - Contribution guidelines
  - **File**: `docs/DEVELOPMENT.md`

- [ ] **Database Migration Tools**
  - Scripts for migrating from Airtable to PostgreSQL
  - Data validation tools
  - **File**: `scripts/migrate_data.py`

- [ ] **Local Development Setup**
  - Docker Compose for local development
  - Pre-configured test data
  - **File**: `deployment/docker/docker-compose.dev.yml`

## 🐛 Bug Fixes & Technical Debt

- [ ] **Review and Refactor**
  - Code review for consistency
  - Remove deprecated code paths
  - Improve error handling

- [ ] **Dependency Updates**
  - Keep dependencies up to date
  - Security patches
  - **File**: `pyproject.toml`

## 📝 Documentation

- [ ] **User Guide**
  - Comprehensive user manual
  - FAQ section
  - **File**: `docs/USER_GUIDE.md`

- [ ] **Admin Guide**
  - Guide for using Django admin panel
  - Common admin tasks
  - **File**: `docs/ADMIN_GUIDE.md`

- [ ] **Deployment Guide**
  - Production deployment checklist
  - Monitoring and maintenance
  - **File**: `docs/DEPLOYMENT.md` (enhance existing)

---

## Notes

- Features are organized by priority and category
- Check off items as they're completed
- Add new items as needed
- Reference related feature plans in `docs/features/` when implementing
- Consider impact on existing functionality when adding new features
