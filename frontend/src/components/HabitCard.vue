<template>
  <div
    class="bg-bg-card rounded-xl p-4 transition-all"
    :class="habit.completedToday ? 'opacity-60' : 'hover:bg-bg-card-hover'"
  >
    <div class="flex items-center justify-between">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <h3
            class="font-medium truncate"
            :class="habit.completedToday ? 'line-through text-text-secondary' : 'text-text-primary'"
          >
            {{ habit.name }}
          </h3>
          <span class="text-xs px-1.5 py-0.5 rounded bg-gray-800 text-text-secondary shrink-0">
            {{ habit.weight }}w
          </span>
        </div>
        <div v-if="habit.streak > 0" class="flex items-center gap-1 mt-1">
          <span class="text-streak-fire text-sm">&#128293;</span>
          <span class="text-xs text-streak-fire font-medium">{{ habit.streak }}-day streak</span>
        </div>
      </div>

      <div class="ml-3 shrink-0">
        <button
          v-if="!habit.completedToday"
          @click="$emit('complete', habit.id)"
          :disabled="loading"
          class="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-50"
        >
          Done
        </button>
        <button
          v-else
          @click="$emit('revert', habit.id)"
          :disabled="loading"
          class="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-text-secondary text-sm font-medium transition-colors disabled:opacity-50"
        >
          Undo
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  habit: { type: Object, required: true },
  loading: { type: Boolean, default: false },
});

defineEmits(["complete", "revert"]);
</script>
