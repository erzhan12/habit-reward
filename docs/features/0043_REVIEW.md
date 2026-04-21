# Feature 0043 — Code Review

## Summary

The plan was implemented faithfully. Active rewards are now returned in the new order (`zero_piece` first, then `non_zero` ascending by `pieces_earned`), claimed one-time rewards remain excluded from the active list, and claimed items continue to be rendered as a separate collapsible section in the Vue page. The unit tests were updated to match the new semantics and a new regression test was added for synthetic active-reward rows. All 17 tests in `tests/test_reward_filtering.py` pass.

Verdict: ship-ready, with a couple of small observations to consider.

---

## 1. Plan fidelity

All plan requirements are met:

- Partitioning matches the plan's `zero_piece` vs `non_zero` split (`src/services/reward_service.py` lines 569–586).

```569:586:src/services/reward_service.py
            zero_piece: list[RewardProgress] = []
            non_zero: list[RewardProgress] = []
            for p in coerced:
                progress_reward_ids.add(
                    int(p.reward_id) if isinstance(p.reward_id, str) else p.reward_id
                )
                status = p.get_status()
                if status == RewardStatus.CLAIMED:
                    reward_obj = getattr(p, "reward", None)
                    if reward_obj and getattr(reward_obj, "is_recurring", False):
                        zero_piece.append(p)
                    continue

                pieces_req = getattr(p, "pieces_required", -1)
                if p.pieces_earned == 0 or pieces_req is None:
                    zero_piece.append(p)
                else:
                    non_zero.append(p)
```

- Sort key is `pieces_earned` ascending with Python's stable sort, so equal keys preserve repository order (verified by `test_equal_pieces_earned_preserves_repo_order`):

```605:607:src/services/reward_service.py
            non_zero.sort(key=lambda rp: rp.pieces_earned)

            return zero_piece + non_zero
```

- One-time `CLAIMED` is excluded, recurring `CLAIMED` is bucketed as fresh cycle (zero-piece).
- Synthetic rows for active rewards without a `RewardProgress` entry are appended to `zero_piece` (matches the plan).
- `src/web/views/rewards.py` and `frontend/src/pages/Rewards.vue` are unchanged and do not resort client-side — claimed rewards still render below active ones in the collapsible section.
- Docstring updated to describe the new behavior.
- Tests in `tests/test_reward_filtering.py` are updated, and the new `test_synthetic_active_reward_appears_in_zero_piece_group` regression test was added as the plan called for.
- `TODO.md` entry added describing the change.

---

## 2. Bugs / correctness

No correctness bugs found. A few subtle points worth documenting:

### 2.1 `getattr(p, "pieces_required", -1)` sentinel is effectively dead

The `-1` default is never actually hit because `RewardProgressModel.pieces_required` is declared as `int | None`, so the attribute always exists. The later check is only `pieces_req is None`, so `-1` would be bucketed as `non_zero`. This was true before this change as well (pre-existing defensive pattern), so it's not a regression — but if the intent is "unknown required → zero_piece", a plain attribute access (`p.pieces_required`) would be clearer:

```python
pieces_req = p.pieces_required
if p.pieces_earned == 0 or pieces_req is None:
    zero_piece.append(p)
```

Low priority — cosmetic cleanup, not a real bug.

### 2.2 Edge case: `ACHIEVED` + `pieces_earned == 0`

Under the old code an `ACHIEVED` entry always went to the `achieved` bucket. Under the new code, an `ACHIEVED` entry with `pieces_earned == 0` (only possible when `pieces_required == 0`, an invalid/nonsensical config) would be placed in `zero_piece`. This isn't a real-world concern — `pieces_required == 0` shouldn't exist — but it's worth noting that the new code no longer treats `ACHIEVED` as its own bucket.

### 2.3 Ordering of synthetic zero-piece entries

Synthetic active-reward entries are appended to `zero_piece` *after* the main loop, so they always appear at the end of the zero-piece block regardless of the natural repo order. That's acceptable, but if product intent is "zero-piece sorted by reward creation order" you'd want to merge-sort them. Probably fine as-is — just undocumented.

---

## 3. Data alignment

No issues. Server still emits `piecesEarned` / `piecesRequired` (camelCase) in `src/web/views/rewards.py`, and the Vue page consumes those keys unchanged. Claimed list props (`claimedRewards`, `claimedAt`, `timesClaimed`) are likewise untouched.

---

## 4. Scope / unexpected side effects

### 4.1 Bot behavior also changes (not explicitly mentioned in the plan)

`get_user_reward_progress()` is also used by the Telegram bot:

- `src/bot/handlers/reward_handlers.py` lines 191 and 486 (the `/progress` screen and the claim-success summary).
- Output is rendered in order by `format_claim_success_with_progress` in `src/bot/formatters.py`.

The plan scope is "web app Rewards page", but this change silently updates the bot's progress listing order too (zero-piece first, then ascending by pieces_earned, instead of percentage-descending). That's arguably consistent UX across clients, but it's a user-visible behavior change the plan didn't call out. Options:

1. Keep it (unify ordering across web + bot) and update the bot's user docs / screenshots if any.
2. Introduce a separate sort-order parameter and let the bot keep its old ordering.

If the intent is #1, everything is already done — just acknowledge the cross-client impact.

### 4.2 Unrelated TODO flips

The diff flips two Analytics TODO items from `[ ]` to `[x]`:

```diff
-- [ ] **User Analytics Dashboard**
+- [x] **User Analytics Dashboard**
...
-- [ ] **Habit Performance Metrics**
+- [x] **Habit Performance Metrics**
```

These are unrelated to feature 0043 and look like they were landed together by accident. If they were completed by a separate change they should be in a separate commit; otherwise revert.

---

## 5. Over-engineering / refactor concerns

None. The function is slightly shorter than before (dropped the 3-bucket partition and the unreachable `else` log). Readability is marginally better.

---

## 6. Style / consistency

- Docstring clearly describes the new semantics and is accurate.
- The file is large (700+ lines) but that predates this change; no action needed here.
- Trailing `else: logger.warning("Unexpected reward status …")` branch was removed. It was unreachable given the three-valued `RewardStatus` enum, so removal is correct and reduces noise.

---

## 7. Test coverage

Good. Coverage of the ordering contract:

- `test_non_zero_sorted_by_pieces_earned_ascending`
- `test_achieved_and_pending_share_non_zero_bucket`
- `test_zero_piece_rewards_appear_first`
- `test_mixed_ordering_all_groups`
- `test_one_piece_away_is_ordered_by_pieces_earned`
- `test_equal_pieces_earned_preserves_repo_order`
- `test_pieces_required_none_goes_to_zero_piece_group`
- `test_synthetic_active_reward_appears_in_zero_piece_group` (new)
- `test_claimed_recurring_reward_visible_as_never_won`
- `test_active_reward_without_progress_visible`

Filter coverage (claimed hidden, recurring visible, etc.) is unchanged. All 17 tests pass locally.

Nice-to-have tests not strictly required:

- A test that asserts one-time `CLAIMED` entries with `pieces_earned > 0` aren't leaked into `zero_piece` (current logic `continue`s, so it's safe, but explicit coverage would help).
- A test mixing a synthetic active reward *and* a progress-row zero-piece reward to pin down their relative order.

---

## 8. Recommendation

Approve with two small follow-ups:

1. **Split the TODO.md Analytics flips into their own commit** (scope hygiene).
2. **Decide/document whether the bot listing also adopts the new order intentionally** — if yes, a one-line note in the PR description is enough; if no, scope the ordering change to the web view (e.g. sort in `rewards_page()` rather than in the service).

Everything else is ready to merge.
