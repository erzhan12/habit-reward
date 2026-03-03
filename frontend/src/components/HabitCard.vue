<template>
  <div
    ref="cardRef"
    class="transition-all"
    :class="[
      densityPadding,
      tc.card.rounded,
      tc.card.shadow,
      tc.card.border,
      tc.card.bg,
      tc.card.extra,
      habit.completedToday ? 'opacity-60' : tc.card.hoverBg,
      habit.completedToday ? '' : hoverClass,
    ]"
    :style="entranceStyle"
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
            {{ habit.weight }}w · {{ habit.rewardChance }}%
          </span>
        </div>
        <div v-if="habit.streak > 0" class="flex items-center gap-1 mt-1">
          <span class="text-streak-fire text-sm" :class="streakClass">🔥</span>
          <span class="text-xs text-streak-fire font-medium" :class="streakClass">{{ habit.streak }}-day streak</span>
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
import { computed, ref } from "vue";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";

const props = defineProps({
  habit: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  index: { type: Number, default: 0 },
});

defineEmits(["complete", "revert"]);

const cardRef = ref(null);
defineExpose({ cardRef });

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);

const { getCardEntranceStyle, getStreakFireClass, hoverClass } = useThemeAnimation();

const entranceStyle = computed(() => getCardEntranceStyle(props.index));
const streakClass = computed(() => getStreakFireClass(props.habit.streak));

const densityPadding = computed(() => {
  const density = themeConfig.value.pageLayout?.density;
  if (density === 'spacious') return 'p-5';
  if (density === 'compact') return 'p-3';
  return 'p-4';
});
</script>
