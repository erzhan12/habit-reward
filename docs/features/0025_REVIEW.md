# Feature 0025: Recurring vs Non-Recurring Rewards — Code Review

**Review Date:** 2025-12-16  
**Reviewer:** ChatGPT  
**Plan Document:** `docs/features/0025_PLAN.md`

## Findings (ordered by severity)

1. **Telegram “Activate/Deactivate” menu button is effectively dead (handler not registered)**
   - `toggle_reward_conversation` is defined in `src/bot/handlers/reward_handlers.py:2029`, and the Rewards menu includes `menu_reward_toggle` (`src/bot/keyboards.py`), but the conversation handler is never added to the bot application.
   - `src/bot/main.py:24-30` imports reward conversations but omits `toggle_reward_conversation`, and `src/bot/main.py:71-76` only registers claim/add/edit.
   - Same issue in webhook mode: `src/bot/webhook_handler.py:40-46` / `src/bot/webhook_handler.py:65-70`.
   - Result: pressing “🔄 Activate/Deactivate Reward” won’t be handled (likely only logged by the global debug callback).

2. **Telegram edit flow cannot actually change `is_recurring`**
   - The edit flow includes an `AWAITING_REWARD_EDIT_RECURRING` state with handlers for `reward_edit_recurring_yes/no` (`src/bot/handlers/reward_handlers.py:1682-1707`), but the UI shown at that step is `build_reward_skip_cancel_keyboard(...)`, which has no Yes/No buttons (`src/bot/handlers/reward_handlers.py:1649-1659`).
   - Result: users can only Skip/Cancel, never choose a new recurring value.
   - Additionally, the edit confirmation message builder doesn’t include old/new recurring values at all (`src/bot/handlers/reward_handlers.py:1622-1646`), so even after fixing the UI, the confirm step won’t reflect the change.

3. **Non-recurring auto-deactivation is implemented in the service, but bot UX doesn’t surface it**
   - Auto-deactivation happens in `RewardService.mark_reward_claimed()` (`src/services/reward_service.py:355-397`), but the claim flow in Telegram doesn’t reload the reward or show the planned informational message.
   - `INFO_REWARD_NON_RECURRING_DEACTIVATED` is added to `src/bot/messages.py` but is unused anywhere in code.
   - Result: users won’t understand why a one-time reward disappears from active lists after claiming.

4. **Duplicate-name validation is “active-only”, but DB uniqueness is “all rewards”**
   - `RewardRepository.get_by_name()` explicitly filters `active=True` (`src/core/repositories.py:229-236`).
   - `RewardService.create_reward()` uses that check to prevent duplicates (`src/services/reward_service.py:443-450`).
   - But the DB constraint is `unique_together = [('user', 'name')]` (`src/core/models.py`), so an *inactive* reward with the same name will still violate uniqueness, causing an IntegrityError/500 on create.
   - This becomes more user-visible with Feature 0025 since rewards can now be deactivated (manually and automatically).

5. **Migration contains unrelated schema changes**
   - `src/core/migrations/0008_add_is_recurring_to_reward.py` includes `AlterField` operations for `BotAuditLog.event_type` and `Reward.type` in addition to adding `Reward.is_recurring` (`src/core/migrations/0008_add_is_recurring_to_reward.py:18-28`).
   - If intentional, it should be called out in the plan/PR; otherwise it should be split/reverted to keep migrations feature-scoped.

## Plan compliance
- ✅ `Reward.is_recurring` added to Django model + migration (`src/core/models.py`, `src/core/migrations/0008_add_is_recurring_to_reward.py`).
- ✅ Service auto-deactivates non-recurring rewards on claim (`src/services/reward_service.py`).
- ✅ Reward creation accepts `is_recurring` in service and bot add flow (`src/services/reward_service.py`, `src/bot/handlers/reward_handlers.py`).
- ⚠️ Edit flow step exists but is not operable (no Yes/No UI) and confirm output doesn’t reflect `is_recurring` changes.
- ⚠️ Manual activate/deactivate flow exists in code but isn’t wired into the running bot (missing registration).
- ⚠️ Bot/API messaging for “auto-deactivated after claim” isn’t implemented beyond returning `active` in API responses; the planned Telegram info message is unused.
- ⚠️ No tests were added for new bot state, new API endpoint, or the auto-deactivation behavior.

## Testing
- Not run (review only).

