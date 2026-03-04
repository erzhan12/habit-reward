<template>
  <div class="flex-1 min-w-0">
    <div class="flex items-center gap-2">
      <h3
        class="font-medium truncate"
        :class="habit.completedToday ? 'line-through text-text-secondary' : 'text-text-primary'"
      >
        {{ habit.name }}
      </h3>
      <span class="text-xs px-1.5 py-0.5 shrink-0" :class="tc.badge.base">
        {{ habit.weight }}w · {{ habit.rewardChance }}%
      </span>
    </div>
    <div v-if="habit.streak > 0" class="flex items-center gap-1 mt-1">
      <span class="text-streak-fire text-sm" :class="streakClass">🔥</span>
      <span class="text-xs text-streak-fire font-medium" :class="streakClass">{{ habit.streak }}-day streak</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  habit: { type: Object, required: true },
  tc: { type: Object, required: true },
  streakClass: { type: String, default: "" },
});
</script>
