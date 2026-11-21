<template>
  <div class="flex-1 min-w-0">
    <div class="flex items-center gap-2">
      <h3
        class="font-medium truncate"
        :class="habit.completedToday ? 'line-through text-text-secondary' : 'text-text-primary'"
      >
        {{ habit.name }}
      </h3>

      <!-- odds badge: hidden by themes that keep the dashboard reward-free.
           Shows the chance only; weight no longer affects it (feature 0048). -->
      <span v-if="hc.showOdds" class="text-xs px-1.5 py-0.5 shrink-0" :class="tc.badge.base">
        {{ habit.rewardChance }}%
      </span>

      <!-- outcome chip: only on completed habits, only when the theme opts in -->
      <span
        v-if="hc.showOutcome && habit.completedToday && habit.todayResult"
        class="text-xs px-1.5 py-0.5 shrink-0 font-medium rounded"
        :class="habit.todayResult.gotReward ? 'text-accent' : 'text-text-muted'"
      >
        <template v-if="habit.todayResult.gotReward">
          🎁 piece won<template v-if="habit.todayResult.rewardName"> — {{ habit.todayResult.rewardName }}</template>
        </template>
        <template v-else>no reward this time</template>
      </span>
    </div>

    <div v-if="habit.streak > 0 || freezeCount > 0" class="flex items-center gap-1 mt-1">
      <template v-if="habit.streak > 0">
        <span
          class="text-sm"
          :class="[streakColorClasses, { 'streak-emoji-muted': habit.completedToday }]"
        >
          🔥
        </span>
        <span class="text-xs font-medium" :class="streakColorClasses">
          {{ habit.streak }}-day streak
        </span>
      </template>
      <!-- freeze inventory: shown whatever the theme's showOdds (feature 0048) -->
      <span
        v-if="freezeCount > 0"
        class="text-xs text-text-secondary"
        :class="{ 'ml-1': habit.streak > 0 }"
        :title="freezeCount === 1 ? '1 streak freeze in reserve' : `${freezeCount} streak freezes in reserve`"
        data-testid="freeze-chip"
      >
        ❄️<template v-if="freezeCount > 1">×{{ freezeCount }}</template>
      </span>
    </div>

    <p v-if="freezeHint" class="text-xs text-text-secondary mt-1" data-testid="freeze-hint">
      {{ freezeHint }}
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../composables/useTheme.js";

const props = defineProps({
  habit: { type: Object, required: true },
  tc: { type: Object, required: true },
  streakClass: { type: String, default: "" },
});

const { themeConfig } = useTheme();

// habitCard theme config with safe defaults (matches DEFAULTS in themes/index.js)
const hc = computed(() => ({
  showOdds: true,
  showOutcome: false,
  buttonLabel: "Done",
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
