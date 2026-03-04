<template>
  <!-- Swipe mode: the swipe component wraps everything -->
  <HabitDoneSwipe
    v-if="isSwipeMode"
    ref="cardRef"
    :habit="habit"
    :loading="loading"
    @complete="$emit('complete', $event)"
    @revert="$emit('revert', $event)"
  >
    <div
      class="transition-all"
      :class="[
        densityPadding,
        tc.card.bg,
        tc.card.extra,
        habit.completedToday ? 'opacity-60' : '',
      ]"
      :style="entranceStyle"
    >
      <HabitCardContent :habit="habit" :tc="tc" :streakClass="streakClass" />
    </div>
  </HabitDoneSwipe>

  <!-- Standard mode: card with interaction component on left/right -->
  <div
    v-else
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
      <!-- Left interaction (checkbox) -->
      <component
        v-if="interactionProps.position === 'left'"
        :is="interactionComponent"
        :habit="habit"
        :loading="loading"
        v-bind="interactionProps"
        @complete="$emit('complete', $event)"
        @revert="$emit('revert', $event)"
      />

      <HabitCardContent :habit="habit" :tc="tc" :streakClass="streakClass" />

      <!-- Right interaction (button, toggle) -->
      <component
        v-if="interactionProps.position === 'right'"
        :is="interactionComponent"
        :habit="habit"
        :loading="loading"
        v-bind="interactionProps"
        @complete="$emit('complete', $event)"
        @revert="$emit('revert', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";
import { useThemeInteraction } from "../composables/useThemeInteraction.js";
import HabitDoneSwipe from "./interactions/HabitDoneSwipe.vue";
import HabitCardContent from "./HabitCardContent.vue";

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
const { interactionComponent, interactionProps, isSwipeMode } = useThemeInteraction();

const entranceStyle = computed(() => getCardEntranceStyle(props.index));
const streakClass = computed(() => getStreakFireClass(props.habit.streak));

const densityPadding = computed(() => {
  const density = themeConfig.value.pageLayout?.density;
  if (density === 'spacious') return 'p-5';
  if (density === 'compact') return 'p-3';
  return 'p-4';
});
</script>
