<template>
  <div class="flex-1 min-w-0">
    <!-- title row: the title alone, so it only truncates on genuinely long names -->
    <h3
      class="font-medium truncate"
      :class="habit.completedToday ? 'line-through text-text-secondary' : 'text-text-primary'"
    >
      {{ habit.name }}
    </h3>

    <!-- meta line: streak, freeze, odds. Spacing only — no "·" separators. -->
    <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1">
      <div v-if="habit.streak > 0" class="inline-flex items-center gap-1">
        <span
          class="text-sm"
          :class="[streakColorClasses, { 'streak-emoji-muted': habit.completedToday }]"
        >
          🔥
        </span>
        <span class="text-xs font-medium" :class="streakColorClasses">
          {{ habit.streak }}-day streak
        </span>
      </div>

      <!-- freeze inventory: shown whatever the theme's odds setting (feature 0048) -->
      <span
        v-if="freezeCount > 0"
        class="text-xs text-text-secondary"
        :title="freezeCount === 1 ? '1 streak freeze in reserve' : `${freezeCount} streak freezes in reserve`"
        data-testid="freeze-chip"
      >
        ❄️<template v-if="freezeCount > 1">×{{ freezeCount }}</template>
      </span>
      <!-- reward chance (feature 0048: depends on the streak only), styled per
           theme; it comes last so its hint wraps under the whole row. Shown in every theme (0049). -->
      <OddsChip
        :reward-chance="Number(habit.rewardChance) || 0"
        :completed="!!habit.completedToday"
        :next-streak="Number(habit.nextStreak) || 1"
        :chance="chance"
        :odds-style="hc.oddsStyle"
        :badge-class="tc.badge?.base || ''"
      />

    </div>

    <!-- outcome: own line under the meta line, may wrap (long reward names) -->
    <p
      v-if="hc.showOutcome && habit.completedToday && habit.todayResult"
      class="text-xs font-medium mt-1"
      :class="habit.todayResult.gotReward ? 'text-accent' : 'text-text-secondary'"
      data-testid="outcome"
    >
      <template v-if="habit.todayResult.gotReward">
        🎁 piece won<template v-if="habit.todayResult.rewardName"> — {{ habit.todayResult.rewardName }}</template>
      </template>
      <template v-else>no reward this time</template>
    </p>

    <p v-if="freezeHint" class="text-xs text-text-secondary mt-1" data-testid="freeze-hint">
      {{ freezeHint }}
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../composables/useTheme.js";
import OddsChip from "./OddsChip.vue";

const props = defineProps({
  habit: { type: Object, required: true },
  tc: { type: Object, required: true },
  streakClass: { type: String, default: "" },
  // { curve, cap } from the dashboard view (feature 0049); null hides the curve
  chance: { type: Object, default: null },
});

const { themeConfig } = useTheme();

// habitCard theme config with safe defaults (matches DEFAULTS in themes/index.js)
const hc = computed(() => ({
  showOutcome: false,
  buttonLabel: "Done",
  oddsStyle: "badge",
  ...(themeConfig.value.habitCard || {}),
}));

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// "2026-11-17" -> "17 Nov". Split the ISO string: new Date() would shift the day in
// negative-offset timezones.
function shortDate(iso) {
  const [, month, day] = String(iso).split("-").map(Number);
  return month && day ? `${day} ${MONTHS[month - 1]}` : String(iso);
}

const freezeCount = computed(() => Number(props.habit.freezeCount) || 0);

const freezeHint = computed(() => {
  if (props.habit.completedToday) return "";
  if (props.habit.freezeUsedFor) {
    return `❄️ Freeze used for ${shortDate(props.habit.freezeUsedFor)} — complete today to keep the streak.`;
  }
  if (props.habit.freezeAtRisk) return "❄️ Skip today and your freeze will be used tonight.";
  return "";
});

const streakColorClasses = computed(() => [
  props.habit.completedToday ? "text-text-muted" : "text-streak-fire",
  props.habit.completedToday ? "" : props.streakClass,
]);
</script>
