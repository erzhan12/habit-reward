# Feature 0046 — Manual Test Plan

These scenarios verify the sink-bounce animation, sequenced reward popup, and the schema migration's per-theme popup variants in a real browser. Automated tests cover the helper/migration plumbing; this checklist exists because animation timing, layout reflow, and reduced-motion behavior cannot be observed reliably in jsdom.

**Prereqs**
- Dev server: `uvicorn asgi:app --reload --port 8000` + `cd frontend && npm run dev`
- Logged-in test user with at least 3 habits — one without any reward, one with a near-due reward (1 piece left), and one positioned at the bottom of the list

## Scenarios

### 1. Completion without a reward (happy path)

1. From the Dashboard, mark a habit done that has no reward configured (or whose reward is not yet ready to fire).
2. **Expect**: card animates downward with an overshoot-and-settle bounce into the bottom slot (~600 ms). No reward popup. Undo toast appears immediately after the animation completes.

### 2. Completion that earns a reward

1. Mark a habit done whose reward fires on this completion.
2. **Expect**: card sink-bounces into bottom slot. Particles burst from the card's center mid-animation. After sink settles, the reward popup opens. Undo toast follows.
3. Dismiss the popup → no layout shift; undo toast remains.

### 3. Completing the bottommost habit

1. Mark the last (bottom-positioned) habit done.
2. **Expect**: deltaY is near 0, so the card performs an in-place mini-bounce. No flicker / horizontal jump. Sequencing identical to scenarios 1/2 depending on reward.

### 4. Swipe-mode completion (verifies ref-placement fix)

1. Switch to a theme whose `interactions.habitComplete` is `'swipe-reveal'`. (Currently no theme uses swipe by default; toggle via DB or theme editor if needed.)
2. Mark a habit done by swiping.
3. **Expect**: same sink-bounce as button mode. Previously the ref pointed at the `<HabitDoneSwipe>` component proxy, so `cardEl.getBoundingClientRect()` / `cardEl.animate()` would silently no-op; with the fix the animation must visibly run.

### 5. `prefers-reduced-motion`

1. Enable reduced motion at the OS level (macOS → System Settings → Accessibility → Display → Reduce motion) or via DevTools (Rendering tab → Emulate CSS media feature `prefers-reduced-motion: reduce`).
2. Mark a habit done — both no-reward and reward variants.
3. **Expect**: card does **not** animate. If a reward was earned, the popup appears immediately (no animation wait). Undo toast follows. No console errors.

### 6. Grid-2 layout

1. Switch to a theme with `pageLayout.habitList: 'grid-2'` (currently **Nature Forest** uses grid for `rewardList`, none use grid-2 for the habit list by default — verify via the theme picker or use DevTools to override `listLayoutClass`).
2. Mark a habit done that needs to reorder across columns (i.e. its new bottom position is in a different column than its old position).
3. **Expect**: the FLIP delta composes both X and Y. The card translates diagonally to its new grid slot with the same overshoot easing. No double-paint or jump.

### 7. Per-theme reward popup variants

For each of the 8 themes, complete a reward-earning habit and confirm the popup variant matches the migrated `reward.rewardPopupVariant`:

| Theme              | Expected variant | Popup component  |
|--------------------|------------------|------------------|
| Clean Modern       | `default`        | `RewardDefault`  |
| Gamified Arcade    | `particles`      | `RewardParticles`|
| Cozy Warm          | `default`        | `RewardDefault`  |
| iOS Native         | `default`        | `RewardDefault`  |
| Dark Focus         | `quiet`          | `RewardQuiet`    |
| Retro Terminal     | `quiet`          | `RewardQuiet`    |
| Nature Forest      | `default`        | `RewardDefault`  |
| Minimalist Zen     | `quiet`          | `RewardQuiet`    |

**Expect**: the popup component matches the table; the `Theme.vue` personality-tag chip for `Particles` / `Quiet` themes still renders correctly in the theme picker.

## Regressions to watch for

- Reward popup opening **before** the sink animation finishes — would indicate the awaited `triggerCompletionCelebration` short-circuited (e.g. particle rejection escaping `Promise.all`).
- Card not visibly moving in swipe mode — would indicate the `cardRef` regressed back onto the swipe component.
- Console errors mentioning `cardEl.animate is not a function` — should be silently no-op'd; surfacing in console means the WAAPI fallback guard regressed.
