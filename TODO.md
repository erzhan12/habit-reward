# TODO: Future Features & Improvements

This document tracks planned features, improvements, and enhancements for the Habit Reward System.

## 🎯 Core Habit System Features

### High Priority

- [ ] **Flexible Streak Tracking with Grace Days**
  - Add new field to Habits model: `allowed_skip_days` (or `grace_days`) - integer field
  - Allows habits to have configurable "grace days" where missing a habit doesn't break the streak
  - **Default value**: 0 (strict by default, maintains backward compatibility)
  - **Suggested field name options**: `allowed_skip_days`, `grace_days`, or `skip_tolerance`
  - **Example use case**: A habit with `allowed_skip_days=1` can be skipped 1 day without breaking the streak
  - **Weekend Grace Days Option**:
    - Add field: `weekend_exempt` (boolean) or `exempt_weekdays` (array/CharField)
    - When enabled, weekends (Saturday/Sunday) don't count against streak
    - **Suggested field name options**: `weekend_exempt`, `skip_weekends`, or `exempt_weekdays`
    - **Implementation approach 1** (Simple): Boolean field `weekend_exempt` - if True, Sat/Sun are automatically grace days
    - **Implementation approach 2** (Flexible): Array/JSONField `exempt_weekdays` - allows selecting specific days (0=Monday, 6=Sunday)
    - **Default value**: False (weekends count by default)
    - **Example use cases**:
      - Gym habit: skip weekends (`weekend_exempt=True`)
      - Work habit: skip weekends and Wednesdays (`exempt_weekdays=[2, 5, 6]`)
    - Streak calculation should skip these days when checking for breaks
    - Combine with `allowed_skip_days` for maximum flexibility
  - **Implementation notes**:
    - Modify streak calculation logic in `src/services/habit_service.py` or `src/core/services/habit_service.py`
    - Update `get_current_streak()` and related methods to account for grace days and exempt weekdays
    - Should track consecutive completions with allowed gaps and exempt days
    - Add validation to ensure `allowed_skip_days >= 0`
    - Add validation for `exempt_weekdays` to ensure values are 0-6
    - Update habit creation/edit forms to include both fields
    - Add UI in bot for users to set grace days and weekend exemptions when creating/editing habits
    - Consider UX: how to explain the difference between grace days (can skip any X days) vs exempt days (specific days always skipped)
  - **Files**: `src/core/models.py`, `src/services/habit_service.py`, `src/bot/handlers/habit_management_handler.py`
  - **Related**: Affects streak calculation, habit completion logic, and user experience

- [ ] **Multi-User Support: User Field in Habits and Rewards**
  - Add `user` field (ForeignKey to User model) to both Habits and Rewards tables
  - Currently habits and rewards appear to be shared across all users
  - Each user should have their own isolated habits and rewards
  - **Implementation requirements**:
    - Add `user` ForeignKey field to `Habit` model in `src/core/models.py`
    - Add `user` ForeignKey field to `Reward` model in `src/core/models.py`
    - Set `on_delete=models.CASCADE` to delete user's habits/rewards when user is deleted
    - Add database migration to add the field (handle existing data migration strategy)
    - Update all queries to filter by `user` (habits, rewards, habit logs, reward progress)
    - Update bot handlers to automatically associate habits/rewards with current user
    - Update admin panel to show user filter and allow filtering by user
    - Update services to require user context for all operations
    - Add validation to prevent users from accessing other users' habits/rewards
  - **Data migration considerations**:
    - If existing data exists, need migration strategy:
      - Option 1: Assign all existing habits/rewards to a default/admin user
      - Option 2: Create user records for existing Telegram users and assign accordingly
      - Option 3: Mark existing data as "legacy" and start fresh
  - **Security implications**:
    - Ensure all API endpoints and bot commands filter by authenticated user
    - Add permission checks to prevent cross-user data access
    - Update tests to verify user isolation
  - **Files**: `src/core/models.py`, `src/core/migrations/`, `src/services/habit_service.py`, `src/services/reward_service.py`, `src/bot/handlers/`, `src/core/admin.py`
  - **Related**: Critical architectural change enabling true multi-user support, affects all habit and reward operations

## 🔧 Admin Panel Improvements

### High Priority

- [ ] **Custom Admin Action for Habit Log Reversion**
  - Add a custom admin action `revert_selected_logs` to `HabitLogAdmin` that properly reverts selected habit logs
  - Should call `habit_service.revert_habit_completion()` to ensure reward progress is also rolled back
  - Prevents manual deletion of logs without reverting associated reward progress
  - **File**: `src/core/admin.py`
  - **Related**: Current manual deletion doesn't revert reward progress automatically

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

- [ ] **Backdate Habit Completion**
  - Add ability to complete habits for past dates (yesterday or earlier) through Telegram bot
  - Useful when users forget to log completion or weren't able to access the bot on completion day
  - **Suggested command**: `/complete_for_date` or add "Log for Yesterday" button in habit list
  - **Implementation approach**:
    - Option 1: Quick button "Complete for Yesterday" alongside "Done" button
    - Option 2: "Select Date" option that opens a calendar/date picker
    - Option 3: Command like `/complete_yesterday <habit_name>` or `/complete_date DD-MM-YYYY <habit_name>`
  - **Features to include**:
    - Allow backdating up to a reasonable limit (e.g., 7 days back)
    - Show confirmation with the selected date before logging
    - Recalculate streaks and reward progress based on the backdated entry
    - Prevent duplicate entries for the same habit on the same date
    - Display calendar showing which days already have completions
  - **Validation rules**:
    - Cannot backdate to before habit was created
    - Cannot backdate to a date that already has a completion for that habit
    - Should respect user's timezone when determining "yesterday"
  - **Files**: `src/bot/handlers/habit_done_handler.py`, `src/services/habit_service.py`, `src/bot/messages.py`
  - **Related**: Improves user experience, helps maintain accurate streaks, affects reward calculation

- [ ] **Reward Edit Interface**
  - Add Telegram bot command/interface to edit existing rewards
  - Currently rewards can only be created and deleted, but not edited
  - Should allow editing:
    - Reward name/title
    - Reward description
    - Reward type (small/medium/large)
    - Target points required
    - Active/inactive status
  - **Suggested command**: `/edit_reward` or add "Edit" button in reward list view
  - **Implementation approach**:
    - Add edit buttons to reward list inline keyboard
    - Create conversation flow for editing each field
    - Allow partial edits (only change specific fields)
    - Show confirmation before saving changes
  - **Files**: `src/bot/handlers/reward_handler.py` or new `src/bot/handlers/reward_management_handler.py`, `src/bot/messages.py`
  - **Related**: Completes CRUD operations for rewards in bot interface

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

### Medium Priority

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

- [ ] **REST API Endpoints**
  - Full REST API for all operations
  - API documentation (OpenAPI/Swagger)
  - **File**: New `src/api/` directory

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

