# Feature 0044 Code Review: Dim Completed Today Streak Indicator

## Verdict

**Implementation matches the plan.** All required behaviors present, tests pass (64/64 in the two affected spec files), no security or performance issues. One small DRY improvement worth taking; everything else is optional polish.

## Plan Conformance

| Plan requirement | Status |
|---|---|
| `text-streak-fire` moved from static `class` into `:class` binding | ✅ [HabitCardContent.vue:17,23](frontend/src/components/HabitCardContent.vue#L17-L23) |
| Mutually exclusive color binding (`text-text-muted` vs `text-streak-fire`) | ✅ Removed from DOM on completed, not just overridden |
| `streakClass` retained for both states | ✅ Both spans keep `streakClass` in the bound array |
| `v-if="habit.streak > 0"` unchanged | ✅ [HabitCardContent.vue:14](frontend/src/components/HabitCardContent.vue#L14) |
| Habit name behavior unchanged | ✅ [HabitCardContent.vue:6](frontend/src/components/HabitCardContent.vue#L6) |
| `--color-text-muted` added to all 8 themes in `themes/index.js` | ✅ |
| `--color-text-muted` mirrored in `app.css` `@theme` + every `[data-theme]` block | ✅ Values match index.js exactly for all 8 themes |
| `REQUIRED_CSS_VARS` updated in theme schema test | ✅ [themes.spec.js:26](frontend/tests/themes.spec.js#L26) |
| Three component test scenarios (incomplete bright, completed muted, no streak hidden) | ✅ [HabitCardContent.spec.js](frontend/tests/HabitCardContent.spec.js) |

### CSS variable value parity (index.js ↔ app.css)

| Theme | Value | Match |
|---|---|---|
| clean_modern | `#7c8798` | ✅ |
| gamified_arcade | `#6f7c91` | ✅ |
| cozy_warm | `#7f7772` | ✅ |
| ios_native | `#7d7d87` | ✅ |
| dark_focus | `#7d8794` | ✅ |
| retro_terminal | `#66806b` | ✅ |
| nature_forest | `#718971` | ✅ |
| minimalist_zen | `#737373` | ✅ |

## Findings

### Critical
None.

### Warning
None.

### Suggestion

1. **Duplicated `:class` array on the two streak spans** — *Resolved in `eb28e42`: extracted to the `streakColorClasses` computed in [HabitCardContent.vue](frontend/src/components/HabitCardContent.vue).*

2. **`retro_terminal` muted token is desaturated green, not gray** — [themes/index.js:466](frontend/src/themes/index.js#L466) / [app.css:93](frontend/src/app.css#L93) use `#66806b`. This is intentional to match the terminal aesthetic, but a future contributor "normalizing" the muted palette could break it. One-line comment next to the value would lock the intent.

3. **Two minor test gaps in [HabitCardContent.spec.js](frontend/tests/HabitCardContent.spec.js)**:
   - No case exercising the default empty `streakClass` (current tests always pass `"streak-fire-bounce"`). Adding a no-`streakClass` mount would lock in that no stray empty token slips into the DOM.
   - Symmetry check missing: incomplete habits aren't asserted to *not* have `text-text-muted`. Cheap to add.
   - Both are nice-to-haves; the plan's three required scenarios are correctly covered and meaningful.

4. **Documentation** — no updates required. RULES.md and the JSDoc in `themes/index.js` intentionally avoid enumerating individual CSS-var tokens; the contract is enforced by `REQUIRED_CSS_VARS` in [themes.spec.js](frontend/tests/themes.spec.js), which was updated. Test-as-contract is consistent with project convention.

## Subagent Verification

- **Security**: Clean — `habit.name` / `habit.streak` rendered via Vue mustache interpolation (auto-escaped); no `v-html`; class bindings use string literals only.
- **Performance**: Inline 2-element class arrays on lines 17 and 23 re-allocate per render, but cost is well below profiler noise; computed wrapper would add reactive overhead exceeding the saved allocation. Skip optimization.
- **Tests**: `cd frontend && npx vitest run tests/HabitCardContent.spec.js tests/themes.spec.js` → 64/64 passing.

## Recommendation

Ship as-is, or take suggestion #1 (extract the duplicated class array to a `computed`) before commit. Other suggestions are optional follow-ups.
