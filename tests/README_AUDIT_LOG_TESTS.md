# Audit Log Test Suite (Feature 0015)

## Overview

This test suite (`test_audit_logs.py`) automates the manual test plan from `docs/features/0015_MANUAL_TEST.md`. It provides **comprehensive testing** of the Bot Audit Log system while **preventing execution in CI/CD**.

## 🛡️ Safety Features

### Triple-Layer CI Protection

1. **Marker Declaration** (`pyproject.toml:74`)
   - All tests marked with `@pytest.mark.local_only`

2. **Auto-Skip in CI** (`tests/conftest.py`)
   - Detects `CI` or `GITHUB_ACTIONS` environment variables
   - Automatically skips `local_only` tests

3. **Explicit Exclusion** (`.github/workflows/deploy-caddy.yml:46`)
   - GitHub Actions runs: `pytest -m "not local_only"`

### Database Safety

- Tests use `:memory:` SQLite database (see `settings_test.py`)
- Created fresh for each test run
- Destroyed automatically after tests
- **NEVER touches production database**

## 🚀 Running Tests

### Run ALL tests (local development)
```bash
uv run pytest tests/test_audit_logs.py -v
```

### Run specific test case
```bash
# TC-002: Habit completion snapshot
uv run pytest tests/test_audit_logs.py::test_tc002_habit_completion_snapshot -v

# TC-007: Cleanup command
uv run pytest tests/test_audit_logs.py::test_tc007_cleanup_audit_logs_command -v
```

### Run ONLY local-only tests
```bash
uv run pytest tests/ -v -m "local_only"
```

### Simulate CI behavior (skip local_only)
```bash
uv run pytest tests/ -v -m "not local_only"
```

### Run with coverage
```bash
uv run pytest --cov=src.services.audit_log_service tests/test_audit_logs.py -v
```

## 📋 Test Cases Covered

| Test | Description | Automated |
|------|-------------|-----------|
| TC-001 | Command logging (basic commands NOT logged) | ⚠️ Partial |
| TC-002 | Habit completion snapshot | ✅ Yes |
| TC-003 | Reward claim before/after state | ✅ Yes |
| TC-004 | DB-changing button click | ✅ Yes |
| TC-005 | Error logging | ✅ Yes |
| TC-006 | Reward revert logging | ✅ Yes |
| TC-007 | Cleanup management command | ✅ Yes |
| Integration | Complete workflow test | ✅ Yes |

## ⚠️ Known Limitations

### TC-001 (Command Logging)
- **Status**: Partially automated
- **Issue**: Full command handlers (`/start`, `/help`) have complex dependencies (user lookup, language detection, etc.)
- **Workaround**: Test focuses on verifying `log_command()` is NOT called for these commands
- **Manual verification still recommended**: Run `/start` and `/help` in test environment and verify no audit logs created

### Randomness Handling
- All tests mock `reward_service.select_reward()` to eliminate randomness
- This ensures deterministic, repeatable test results
- See `RULES.md` for details on testing strategies for randomness

## 🔧 Troubleshooting

### "Database table is locked" Error
```
sqlite3.OperationalError: database table is locked: users
```

**Cause**: SQLite doesn't handle concurrent writes well in tests

**Solutions**:
1. Run tests sequentially (not in parallel):
   ```bash
   uv run pytest tests/test_audit_logs.py -v --tb=short
   ```

2. If error persists, delete test database:
   ```bash
   rm test.db  # if exists
   uv run pytest tests/test_audit_logs.py -v
   ```

3. Ensure `--reuse-db` is in pytest config (already set in `pyproject.toml`)

### "async_generator has no attribute" Error
**Cause**: Mixing async/sync fixtures incorrectly

**Solution**: Ensure fixtures match their usage:
- Async tests → can use both sync and async fixtures
- Sync fixtures → cannot depend on async fixtures

### Tests Skipped in Local Run
If tests are being skipped locally when they shouldn't be:

```bash
# Check for CI environment variables
env | grep -E '(CI|GITHUB_ACTIONS|CONTINUOUS_INTEGRATION)'

# If any are set, unset them:
unset CI GITHUB_ACTIONS CONTINUOUS_INTEGRATION

# Then re-run tests
uv run pytest tests/test_audit_logs.py -v
```

## 📚 Related Documentation

- **Manual Test Plan**: `docs/features/0015_MANUAL_TEST.md`
- **Testing Patterns**: `RULES.md` (search for "Testing Audit Logs")
- **Pytest Configuration**: `pyproject.toml` → `[tool.pytest.ini_options]`

## 🎯 Best Practices

1. **Run tests before committing changes to audit log system**
   ```bash
   uv run pytest tests/test_audit_logs.py -v
   ```

2. **Use tests as documentation** - Read test code to understand expected audit log behavior

3. **Update tests when changing audit log functionality** - Keep tests in sync with code

4. **Manual verification for critical changes** - Supplement automated tests with manual testing from `0015_MANUAL_TEST.md`

## ✅ Success Criteria

All tests should pass and output:
```
========== 8 passed in 5-10s ==========
```

If tests fail:
1. Read the assertion error carefully
2. Check if recent code changes broke audit logging
3. Verify database migrations are applied: `uv run python manage.py migrate`
4. Check test data setup (fixtures)

## 🤝 Contributing

When adding new audit log features:

1. Add corresponding test case to `test_audit_logs.py`
2. Mark test with `@pytest.mark.local_only`
3. Use sync fixtures for DB setup (see existing patterns)
4. Mock `reward_service.select_reward()` to control randomness
5. Update this README if adding new test patterns
