# Feature 0023: Hide Piece Price Field in Telegram Reward Commands — Code Review

**Review Date:** 2025-12-12  
**Reviewer:** ChatGPT  
**Plan Document:** `docs/features/0023_PLAN.md`

## Findings (ordered by severity)
1. **Missing regression tests for the new bot flows**  
   - No updates under `tests/` to cover the shorter `/add_reward` and `/edit_reward` paths (per plan tests should land in `tests/test_bot_handlers.py`). This leaves the new “skip piece value” behavior unverified and increases the risk of silent breakage in multi-locale prompts and confirmations.
2. **Unused conversation states kept for piece value**  
   - `src/bot/handlers/reward_handlers.py:58-76` still declares `AWAITING_REWARD_VALUE` and `AWAITING_REWARD_EDIT_VALUE` even though both states are removed from the conversations. Keeping these constants invites accidental reuse and makes it harder to see that the piece-value step is fully disabled.
3. **Edit context still stores piece_value even though it is no longer exposed**  
   - `src/bot/handlers/reward_handlers.py:1197-1204` copies `reward.piece_value` into `old_piece_value` on selection. That data is never shown or written back, so we’re storing an unused field in user state. Dropping it would better reflect the intended UX and avoid stale data hanging around the context.

## Plan compliance
- Telegram add/edit reward flows now bypass piece-value prompts and go straight from pieces → confirm; confirmation templates were trimmed accordingly; creation and update paths no longer send `piece_value` from the bot ✅ (`src/bot/handlers/reward_handlers.py`, `src/bot/messages.py`)
- RULES updated to state the bot must not manage `piece_value` ✅ (`RULES.md`)
- Tests called for in the plan are absent ⚠️ (nothing added under `tests/`)

## Testing
- Not run (review only)
