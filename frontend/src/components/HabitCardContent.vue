<template>
  <div class="flex-1 min-w-0">
    <div class="flex items-center gap-2">
      <h3
        class="font-medium truncate"
        :class="habit.completedToday ? 'line-through text-text-secondary' : 'text-text-primary'"
      >
        {{ habit.name }}
      </h3>

      <!-- odds badge: hidden by themes that keep the dashboard reward-free -->
      <span v-if="hc.showOdds" class="text-xs px-1.5 py-0.5 shrink-0" :class="tc.badge.base">
        {{ habit.weight }}w · {{ habit.rewardChance }}%
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

    <div v-if="habit.streak > 0" class="flex items-center gap-1 mt-1">
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

const streakColorClasses = computed(() => [
  props.habit.completedToday ? "text-text-muted" : "text-streak-fire",
  props.habit.completedToday ? "" : props.streakClass,
]);
</script>
