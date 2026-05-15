# Feature 0046 Code Review

## Findings

### P2 - Optional particle failures can bypass the sink-bounce wait

`triggerCompletionCelebration()` starts the sink animation and reward particles together, then awaits them via `Promise.all()` (`frontend/src/composables/useThemeAnimation.js:146-148`). `animateSinkBounce()` swallows its own WAAPI cancellation/failure paths, but `animateBurstParticles()` does not catch failures from `getBoundingClientRect()`, the dynamic import, or `spawnParticles()` (`frontend/src/composables/useThemeAnimation.js:119-129`).

`Dashboard.vue` catches the rejected `triggerCompletionCelebration()` call and immediately proceeds to show the reward popup and undo toast (`frontend/src/pages/Dashboard.vue:151-165`). If the particle path rejects while the sink animation is still running, the popup can open before the card finishes settling, which violates the main sequencing requirement for reward wins. The robust shape is to isolate the optional particle failure while still awaiting the sink promise, for example by catching the particle promise individually or using `Promise.allSettled()` after guaranteeing the sink promise is included.

### P3 - The manual test plan referenced by the implementation plan is missing

`docs/features/0046_PLAN.md` says the manual scenarios are recorded in `docs/features/0046_MANUAL_TEST_PLAN.md`, but that file is not present. The automated coverage is good for the helper and theme migration paths, but the requested manual coverage for real dashboard interactions, swipe mode, reduced motion, grid layout, and per-theme popup variants is not documented in the repo.

## Implementation Check

The main code paths match the plan:

- `completionCelebration` was removed from theme config and replaced by `reward.rewardPopupVariant`.
- `RewardCelebration.vue` and `Theme.vue` read the new reward variant field.
- `HabitCard.vue` moved the swipe-mode exposed ref onto a DOM element.
- `Dashboard.vue` captures the old rect, waits for `nextTick()`, awaits the completion animation, and only then opens the reward popup.
- `useThemeAnimation.js` exports `animateSinkBounce`, `animateBurstParticles`, and `triggerCompletionCelebration`, with reduced-motion gating at the entry point.

## Validation

- `npm test -- tests/themeAnimation.spec.js tests/themes.spec.js` passed: 79 tests.
- `npm run build` passed. Vite emitted a non-blocking warning that `particles.js` is dynamically imported by `useThemeAnimation.js` and also statically imported by `RewardParticles.vue`, so that dynamic import will not create a separate chunk.
