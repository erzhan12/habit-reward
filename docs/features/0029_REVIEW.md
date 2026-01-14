# Feature 0029 Code Review: Fix "Reward progress not found" Error on Back Button

## Summary

**Status: CHANGES REQUIRED**

The handler order fix is correct and tests were added, but the tests do not verify the ConversationHandler routing order. A regression in handler ordering would still pass the suite. One assertion also inspects positional args even though the handler uses keyword arguments, so it does not validate the message content.

## Implementation Checklist

| Requirement | Status | Location |
|-------------|--------|----------|
| Swap handler order so `claim_reward_back` matches first | ✅ Done | `src/bot/handlers/reward_handlers.py:2194-2196` |
| Add test for `claim_reward_back` routing | ⚠️ Partial | `tests/test_bot_handlers.py:1486` |
| Add test for `claim_reward_<id>` routing | ⚠️ Partial | `tests/test_bot_handlers.py:1540` |
| Add test for UUID-like reward IDs | ⚠️ Partial | `tests/test_bot_handlers.py:1605` |

## Bugs or Issues

1. **Routing order not actually tested**
   - The new tests call `claim_back_callback()` and `claim_reward_callback()` directly instead of verifying that the ConversationHandler routes `claim_reward_back` to the back handler before the prefix matcher.
   - If the handler order is accidentally reversed again, these tests would still pass.
   - Location: `tests/test_bot_handlers.py:1486`, `src/bot/handlers/reward_handlers.py:2194-2196`.

2. **Message assertion reads positional args but message is passed by keyword**
   - In `test_claim_reward_callback_still_works`, the "not found" assertion reads `call_args.args[0]`, but `edit_message_text()` is called with `text=` as a keyword argument in `claim_reward_callback`.
   - This makes the check ineffective and could miss an error response.
   - Location: `tests/test_bot_handlers.py:1595`, `src/bot/handlers/reward_handlers.py:475`.

## Data Alignment Issues

**None found.**

## Over-engineering Assessment

**No over-engineering detected.** The change remains minimal.

## Code Style Consistency

**Consistent.** The new tests follow existing patterns in `tests/test_bot_handlers.py`.

## Test Quality

Tests exist but do not validate the specific routing behavior that caused the bug. The assertions should be updated to exercise the ConversationHandler pattern order (or inspect the state handler list order directly).

## Conclusion

Fix the test coverage issues above to ensure the routing order regression is caught. After that, the implementation should be ready to approve.
