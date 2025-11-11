# TODO: Future Features & Improvements

This document tracks planned features, improvements, and enhancements for the Habit Reward System.

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

