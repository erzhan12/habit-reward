# Feature 0046 Code Review

## Findings

### P0 - Feature 0046 is not implemented

The source tree still contains the pre-0046 completion animation flow. `frontend/src/composables/useThemeAnimation.js:120` still reads `animations.value.completionCelebration` and dispatches to `animateScaleUp`, `animateBurstParticles`, or `animateFadeQuiet`; there is no exported `animateSinkBounce`, no `{ oldRect, gotReward }` argument, no reduced-motion gate, and no WAAPI fallback behavior. This means the global sink-bounce animation described by the plan never runs.

The dashboard sequencing is also unchanged. `frontend/src/pages/Dashboard.vue:132` posts the completion request, then `onSuccess` immediately calls `triggerCompletionCelebration(cardEl)` at `frontend/src/pages/Dashboard.vue:141` and immediately opens the reward popup at `frontend/src/pages/Dashboard.vue:150`. It does not capture the pre-submit rect, does not `await nextTick()`, does not await animation completion before showing the popup, and does not wrap the animation in a resilience guard. This preserves the exact bug the feature is intended to fix: reward popup and card animation can happen simultaneously, and the card cannot animate from its old slot to its new bottom slot.

### P0 - Theme schema migration was not applied

`completionCelebration` remains in the theme schema and theme data. The deprecated validation constant is still exported at `frontend/src/themes/index.js:33`, the default still sets `DEFAULTS.animations.completionCelebration` at `frontend/src/themes/index.js:70`, and individual themes still define `animations.completionCelebration` such as `clean_modern` at `frontend/src/themes/index.js:166`, `gamified_arcade` at `frontend/src/themes/index.js:235`, `dark_focus` at `frontend/src/themes/index.js:441`, and `minimalist_zen` at `frontend/src/themes/index.js:649`.

The planned `reward.rewardPopupVariant` field and `VALID_REWARD_POPUP_VARIANTS` export are absent. As a result, reward popup selection still depends on the old animation key, and the forward-compat guard requested by the plan cannot exist.

### P1 - Reward popup and theme picker still read the old field

`RewardCelebration` still chooses its component from `themeConfig.value.animations?.completionCelebration` at `frontend/src/components/rewards/RewardCelebration.vue:73`, mapping `"burst-particles"` and `"fade-quiet"` directly. `Theme.vue` still derives personality tags from `anims.completionCelebration` at `frontend/src/pages/Theme.vue:291`. Both should read `config.reward?.rewardPopupVariant` after the migration.

If only the theme data were migrated later, these two call sites would silently fall back to `RewardDefault` and stop showing the intended `Particles` / `Quiet` labels.

### P1 - Swipe-mode DOM ref bug remains

The plan calls out a swipe-mode ref placement bug, but `frontend/src/components/HabitCard.vue:5` still places `ref="cardRef"` on the `<HabitDoneSwipe>` component instead of the inner DOM `<div>` at `frontend/src/components/HabitCard.vue:11`. In swipe mode, `defineExpose({ cardRef })` can expose a component proxy rather than an element, so `getBoundingClientRect()` and WAAPI `.animate()` are not reliable.

### P1 - Required animation tests are missing

`frontend/tests/themeAnimation.spec.js` does not exist, and `frontend/tests/themes.spec.js:7` still imports `VALID_COMPLETION_CELEBRATIONS`. The existing schema tests still assert `config.animations.completionCelebration` at `frontend/tests/themes.spec.js:62` and validate it at `frontend/tests/themes.spec.js:81`. These tests currently reinforce the old contract instead of guarding the new one.

## Notes

I did not run the frontend test suite because the inspected implementation does not include the planned code paths yet; the review is blocked at source inspection.
