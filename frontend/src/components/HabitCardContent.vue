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
      <span class="text-sm" :class="streakColorClasses">
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

const props = defineProps({
  habit: { type: Object, required: true },
  tc: { type: Object, required: true },
  streakClass: { type: String, default: "" },
});

const streakColorClasses = computed(() => [
  props.habit.completedToday ? "text-text-muted" : "text-streak-fire",
  props.streakClass,
]);
</script>
