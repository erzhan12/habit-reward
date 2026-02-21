<template>
  <div class="px-4 pt-6 pb-4 max-w-2xl mx-auto">
    <!-- Summary card -->
    <div class="bg-bg-card rounded-xl p-4 mb-6">
      <h1 class="text-2xl font-bold text-text-primary mb-3">Streaks</h1>
      <div class="grid grid-cols-3 gap-4 text-center">
        <div>
          <p class="text-2xl font-bold text-accent">{{ summary.totalCompletions }}</p>
          <p class="text-xs text-text-secondary">Total done</p>
        </div>
        <div>
          <p class="text-2xl font-bold text-text-primary">{{ summary.activeHabits }}</p>
          <p class="text-xs text-text-secondary">Active habits</p>
        </div>
        <div>
          <p class="text-2xl font-bold text-streak-fire">{{ summary.bestStreak.count }}</p>
          <p class="text-xs text-text-secondary truncate" :title="summary.bestStreak.habitName">
            Best streak
          </p>
        </div>
      </div>
    </div>

    <!-- Habit streaks list -->
    <div class="space-y-2">
      <div
        v-for="habit in habits"
        :key="habit.id"
        class="bg-bg-card rounded-xl p-4"
      >
        <div class="flex items-center justify-between">
          <div class="flex-1 min-w-0">
            <h3 class="font-medium text-text-primary truncate">{{ habit.name }}</h3>
            <div class="flex items-center gap-3 mt-1">
              <span class="text-xs text-text-secondary">
                Best: {{ habit.longestStreak }}
              </span>
              <span class="text-xs text-text-secondary">
                This week: {{ habit.completionsThisWeek }}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 ml-3 shrink-0">
            <span class="text-streak-fire text-lg">&#128293;</span>
            <span class="text-xl font-bold" :class="habit.currentStreak > 0 ? 'text-streak-fire' : 'text-text-secondary'">
              {{ habit.currentStreak }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="habits.length === 0" class="text-center py-12">
        <p class="text-text-secondary">No habits yet.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  habits: { type: Array, default: () => [] },
  summary: { type: Object, default: () => ({ totalCompletions: 0, activeHabits: 0, bestStreak: { habitName: "N/A", count: 0 } }) },
});
</script>
