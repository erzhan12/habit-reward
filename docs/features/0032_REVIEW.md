# Feature 0032 Code Review: Add Confirmation Message for "Yesterday" Habit Completion

## Summary

**Status: APPROVED with 1 pre-existing bug noted**

The "yesterday" flow correctly shows the same confirmation prompt used by the "for date" flow and routes into the existing `CONFIRMING_BACKDATE` handler. The change is minimal and reuses all existing infrastructure. One pre-existing bug in `cancel_handler` is now more exposed.

## Implementation Checklist

| Requirement | Status | Location |
|-------------|--------|----------|
| Get `habit_id` from context | ✅ Done | `habit_done_handler.py:354` |
| Store `backdate_date` in context | ✅ Done | `habit_done_handler.py:367` |
| Show `HELP_BACKDATE_CONFIRM` message | ✅ Done | `habit_done_handler.py:374-377` |
| Use `build_backdate_confirmation_keyboard` | ✅ Done | `habit_done_handler.py:373` |
| Return `CONFIRMING_BACKDATE` state | ✅ Done | `habit_done_handler.py:381` |
| No changes to `handle_backdate_confirmation()` | ✅ Correct | `habit_done_handler.py:539-624` |
| No changes to ConversationHandler states | ✅ Correct | `habit_done_handler.py:647-669` |
| No changes to `messages.py` or `keyboards.py` | ✅ Correct | — |

## Findings

### 1. Pre-existing bug: `cancel_handler` crashes on callback queries (not introduced by this change)

**File**: `src/bot/handlers/habit_done_handler.py:627-644`

The `cancel_handler` uses `update.message.reply_text()` (line 633). However, in the `CONFIRMING_BACKDATE` state, it's registered as a `CallbackQueryHandler` (line 665):

```python
CONFIRMING_BACKDATE: [
    CallbackQueryHandler(handle_backdate_confirmation, pattern="^backdate_confirm_"),
    CallbackQueryHandler(cancel_handler, pattern="^backdate_cancel$"),  # <-- callback query
]
```

When the user clicks the "No" button (callback_data: `"backdate_cancel"`), `update.message` is `None` for callback queries. This causes `AttributeError: 'NoneType' object has no attribute 'reply_text'`.

**Impact**: This bug already existed for the "for date" cancellation path. Our change now also exposes it to "yesterday" cancellations, making it more likely to be hit.

**Fix suggestion**: `cancel_handler` should check if `update.callback_query` exists and use `query.edit_message_text()` instead of `update.message.reply_text()` when triggered via callback.

### 2. Test masks the cancel bug

**File**: `tests/bot/test_habit_done_yesterday_confirmation.py:159-187`

The cancel test at line 161 manually sets `update.message = Mock()` to make it work:
```python
update.message = Mock()
update.message.reply_text = AsyncMock()
```

In a real Telegram callback query, `update.message` would be `None`. The test passes but doesn't reflect actual runtime behavior.

## Data Alignment Issues

None. The context data flows correctly:
- `habit_id` (str) set at `habit_selected_callback:179` → read at `handle_yesterday_selection:354` → passed to `build_backdate_confirmation_keyboard` which accepts `int | str`
- `habit_name` (str) set at `habit_selected_callback:180` → read at `handle_backdate_confirmation:554`
- `backdate_date` (date) set at `handle_yesterday_selection:367` → read at `handle_backdate_confirmation:555`

## Over-Engineering Assessment

No over-engineering. The change is 6 net lines of logic — the minimum needed.

## Code Style Consistency

No issues. The new code in `handle_yesterday_selection()` mirrors the pattern in `handle_backdate_date_selection()` (lines 520-536): store date in context, format for display, show confirmation keyboard, return `CONFIRMING_BACKDATE`.

## Test Coverage

Test file: `tests/bot/test_habit_done_yesterday_confirmation.py`

| Test | What it covers |
|------|---------------|
| `test_yesterday_selection_shows_confirmation` | Confirmation prompt shown, correct state returned, keyboard has correct callbacks |
| `test_yesterday_confirmation_processes_completion` | Confirmation calls `process_habit_completion` with `target_date=yesterday`, context cleaned up |
| `test_yesterday_confirmation_duplicate_shows_error` | `ERROR_BACKDATE_DUPLICATE` shown on ValueError, context cleaned up |
| `test_yesterday_cancel_cleans_context` | Cancel path cleans context, doesn't process habit (but see Finding #2 above) |

## Conclusion

The feature correctly implements the plan. The only issue found is a **pre-existing bug** in `cancel_handler` that crashes when invoked via callback query — this bug existed before our change but is now more exposed. Recommend fixing it as a follow-up.
