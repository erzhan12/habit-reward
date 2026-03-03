<template>
  <div
    class="p-4 transition-all"
    :class="[
      tc.card.rounded,
      tc.card.shadow,
      tc.card.border,
      tc.card.bg,
      tc.card.extra,
      habit.completedToday ? 'opacity-60' : tc.card.hoverBg,
    ]"
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
          <span class="text-xs px-1.5 py-0.5 shrink-0" :class="tc.badge.base">
            {{ habit.weight }}w
          </span>
        </div>
        <div v-if="habit.streak > 0" class="flex items-center gap-1 mt-1">
          <span class="text-streak-fire text-sm">🔥</span>
          <span class="text-xs text-streak-fire font-medium">{{ habit.streak }}-day streak</span>
        </div>
      </div>

      <div class="ml-3 shrink-0">
        <button
          v-if="!habit.completedToday"
          @click="$emit('complete', habit.id)"
          :disabled="loading"
          class="text-sm font-medium transition-all disabled:opacity-50"
          :class="[tc.button.rounded, tc.button.padding, tc.button.primary]"
        >
          Done
        </button>
        <button
          v-else
          @click="$emit('revert', habit.id)"
          :disabled="loading"
          class="text-sm font-medium transition-all disabled:opacity-50"
          :class="[tc.button.rounded, tc.button.padding, tc.button.secondary]"
        >
          Undo
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../composables/useTheme.js";

defineProps({
  habit: { type: Object, required: true },
  loading: { type: Boolean, default: false },
});

defineEmits(["complete", "revert"]);

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);
</script>
