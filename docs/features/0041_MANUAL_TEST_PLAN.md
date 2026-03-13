# Feature 0041 — Manual Test Plan
# Habit Performance Metrics API

**Plan**: `docs/features/0041_PLAN.md`
**Review**: `docs/features/0041_REVIEW.md`
**Date**: 2026-03-13

---

## Prerequisites

1. Server running: `uvicorn asgi:app --reload --port 8000`
2. At least 2-3 active habits with completion logs spanning several days
3. A valid JWT access token. Obtain one via:

```bash
# Get auth code from Telegram bot: /web_login
# Then exchange it:
curl -X POST http://localhost:8000/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "<your_id>", "auth_code": "<code>"}'
```

Save the `access_token` from the response. All test commands below use `$TOKEN` as placeholder.

```bash
export TOKEN="<your_access_token>"
```

---

## Test Suite

---

### T-01 — Health Check & Endpoint Discovery

| # | Action | Expected Result |
|---|--------|----------------|
| 1.1 | `curl http://localhost:8000/health` | `200 OK` with JSON `{"status": "healthy"}` |
| 1.2 | `curl http://localhost:8000/docs` | Swagger UI loads; `/v1/analytics` section visible with 3 endpoints |

---

### T-02 — Completion Rates (Default Period)

```bash
curl -s http://localhost:8000/v1/analytics/completion-rates \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

| # | Check | Expected Result |
|---|-------|----------------|
| 2.1 | Status code | `200` |
| 2.2 | Response is a JSON array | Each item has: `habit_id`, `habit_name`, `completion_rate`, `completed_days`, `available_days` |
| 2.3 | `completion_rate` values | Between 0.0 and 1.0 |
| 2.4 | Sorted by rate | First item has highest `completion_rate` |
| 2.5 | Only active habits | Deactivated habits should NOT appear in the list |
| 2.6 | Default period | Covers last 30 days (verify `completed_days` makes sense for your data) |

---

### T-03 — Completion Rates (Period Variants)

| # | Action | Expected Result |
|---|--------|----------------|
| 3.1 | `?period=7d` | Returns rates for last 7 days; `available_days` ≤ 7 per habit |
| 3.2 | `?period=30d` | Same as default |
| 3.3 | `?period=90d` | Returns rates for last 90 days; `available_days` ≤ 90 |

```bash
curl -s "http://localhost:8000/v1/analytics/completion-rates?period=7d" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

### T-04 — Completion Rates (Custom Date Range)

| # | Action | Expected Result |
|---|--------|----------------|
| 4.1 | `?start_date=2026-03-01&end_date=2026-03-13` | Returns rates for that exact range |
| 4.2 | `?start_date=2026-03-10&end_date=2026-03-01` | `400` — "start_date must be <= end_date" |
| 4.3 | `?start_date=2025-01-01&end_date=2026-03-13` | `400` — "must not exceed 365 days" |
| 4.4 | `?start_date=2026-03-01` (no end_date) | `400` — "Both start_date and end_date are required" |
| 4.5 | `?end_date=2026-03-13` (no start_date) | `400` — "Both start_date and end_date are required" |

```bash
# Valid custom range
curl -s "http://localhost:8000/v1/analytics/completion-rates?start_date=2026-03-01&end_date=2026-03-13" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Invalid: start > end
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8000/v1/analytics/completion-rates?start_date=2026-03-10&end_date=2026-03-01" \
  -H "Authorization: Bearer $TOKEN"

# Invalid: partial range
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8000/v1/analytics/completion-rates?start_date=2026-03-01" \
  -H "Authorization: Bearer $TOKEN"
```

---

### T-05 — Rankings

```bash
curl -s http://localhost:8000/v1/analytics/rankings \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

| # | Check | Expected Result |
|---|-------|----------------|
| 5.1 | Status code | `200` |
| 5.2 | Response is a JSON array | Each item has: `rank`, `habit_id`, `habit_name`, `completion_rate`, `total_completions`, `current_streak`, `longest_streak_in_range` |
| 5.3 | `rank` values | Sequential: 1, 2, 3... |
| 5.4 | Sorted by rate | `rank=1` has highest `completion_rate` |
| 5.5 | `current_streak` | Matches what you see on the Streaks page or `/v1/streaks` |
| 5.6 | `total_completions` | Reasonable count for the 30-day default period |
| 5.7 | `longest_streak_in_range` | ≥ `current_streak` (or could be higher if streak was broken and restarted) |

---

### T-06 — Rankings with Period

| # | Action | Expected Result |
|---|--------|----------------|
| 6.1 | `?period=7d` | Rankings reflect last 7 days only; `total_completions` likely lower than 30d |
| 6.2 | `?period=90d` | Rankings reflect last 90 days |

```bash
curl -s "http://localhost:8000/v1/analytics/rankings?period=7d" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

### T-07 — Trends (All Habits)

```bash
curl -s http://localhost:8000/v1/analytics/trends \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

| # | Check | Expected Result |
|---|-------|----------------|
| 7.1 | Status code | `200` |
| 7.2 | Response has `daily` and `weekly` arrays | Both present |
| 7.3 | `daily` entries | Each has `date` (ISO format) and `completions` (int ≥ 1) |
| 7.4 | `daily` sorted by date | Ascending order |
| 7.5 | `weekly` entries | Each has `week_start` (Monday), `completions`, `available_days`, `rate` |
| 7.6 | `week_start` is always a Monday | Verify with a calendar |
| 7.7 | `rate` values | Between 0.0 and 1.0 |
| 7.8 | Days with no completions | NOT present in `daily` (only days with at least 1 completion appear) |

---

### T-08 — Trends (Single Habit)

```bash
# Replace 1 with an actual habit_id from your data
curl -s "http://localhost:8000/v1/analytics/trends?habit_id=1" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

| # | Check | Expected Result |
|---|-------|----------------|
| 8.1 | Status code | `200` |
| 8.2 | `daily` completions | All entries relate to that single habit |
| 8.3 | `weekly` available_days | Reflects that one habit's exempt weekdays and skip days |
| 8.4 | Compare with all-habits trends | Single habit should have fewer or equal completions per day |

---

### T-09 — Trends (Invalid Habit ID)

| # | Action | Expected Result |
|---|--------|----------------|
| 9.1 | `?habit_id=999999` (non-existent) | `404` — "Habit 999999 not found" |
| 9.2 | `?habit_id=<other_user_habit>` (if you know one) | `403` — "Access denied" |

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8000/v1/analytics/trends?habit_id=999999" \
  -H "Authorization: Bearer $TOKEN"
```

---

### T-10 — Authentication Required

| # | Action | Expected Result |
|---|--------|----------------|
| 10.1 | `/v1/analytics/completion-rates` without token | `401` |
| 10.2 | `/v1/analytics/rankings` without token | `401` |
| 10.3 | `/v1/analytics/trends` without token | `401` |
| 10.4 | With expired/invalid token | `401` |

```bash
# No token
curl -s -w "\nHTTP %{http_code}\n" http://localhost:8000/v1/analytics/completion-rates

# Invalid token
curl -s -w "\nHTTP %{http_code}\n" http://localhost:8000/v1/analytics/completion-rates \
  -H "Authorization: Bearer invalid_token_here"
```

---

### T-11 — Exempt Weekdays & Skip Days Verification

If you have a habit with `exempt_weekdays` or `allowed_skip_days` configured:

| # | Check | Expected Result |
|---|-------|----------------|
| 11.1 | Completion rate `available_days` | Lower than calendar days in range (exempt days subtracted) |
| 11.2 | Compare two habits | Habit with exemptions should have fewer `available_days` than one without |
| 11.3 | `completion_rate` | Can be higher than naive calculation because denominator is smaller |

---

### T-12 — New Habit Edge Case

If you recently created a habit (within the last 30 days):

| # | Check | Expected Result |
|---|-------|----------------|
| 12.1 | `available_days` in completion-rates | Should reflect only days since creation, not full 30 days |
| 12.2 | Habit created today with no completions | `completion_rate = 0.0`, `available_days = 1`, `completed_days = 0` |

---

### T-13 — Empty State

| # | Action | Expected Result |
|---|--------|----------------|
| 13.1 | User with no active habits | All 3 endpoints return empty arrays / empty trend data |
| 13.2 | User with habits but no completions in range | `completion-rates`: all rates = 0.0; `trends`: empty daily/weekly |

---

### T-14 — Cross-Endpoint Consistency

| # | Check | Expected Result |
|---|-------|----------------|
| 14.1 | Same `habit_id` across completion-rates and rankings | `completion_rate` matches |
| 14.2 | Rankings `current_streak` vs `/v1/streaks` | Values match |
| 14.3 | Trends daily sum vs completion-rates `completed_days` | For a single habit, sum of `daily.completions` ≈ `completed_days` |

---

## Quick Test Script

Run all happy-path checks in one go:

```bash
export TOKEN="<your_token>"
echo "=== Completion Rates ==="
curl -s "http://localhost:8000/v1/analytics/completion-rates?period=7d" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

echo "=== Rankings ==="
curl -s "http://localhost:8000/v1/analytics/rankings?period=7d" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

echo "=== Trends (all) ==="
curl -s "http://localhost:8000/v1/analytics/trends?period=7d" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

echo "=== Error: no auth ==="
curl -s -w "HTTP %{http_code}\n" http://localhost:8000/v1/analytics/completion-rates

echo "=== Error: invalid range ==="
curl -s -w "HTTP %{http_code}\n" \
  "http://localhost:8000/v1/analytics/completion-rates?start_date=2026-03-10&end_date=2026-03-01" \
  -H "Authorization: Bearer $TOKEN"

echo "=== Error: partial range ==="
curl -s -w "HTTP %{http_code}\n" \
  "http://localhost:8000/v1/analytics/completion-rates?start_date=2026-03-01" \
  -H "Authorization: Bearer $TOKEN"

echo "=== Error: habit not found ==="
curl -s -w "HTTP %{http_code}\n" \
  "http://localhost:8000/v1/analytics/trends?habit_id=999999" \
  -H "Authorization: Bearer $TOKEN"
```
