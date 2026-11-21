<template>
  <div
    class="p-4 transition-all"
    :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra, hoverClass]"
  >
    <div class="flex items-center justify-between mb-2">
      <h3 class="font-medium text-text-primary truncate">{{ reward.name }}</h3>
      <span
        class="text-xs px-2 py-0.5 font-medium shrink-0"
        :class="statusClass"
      >
        {{ statusLabel }}
      </span>
    </div>

    <!-- Progress bar -->
    <div class="w-full bg-track rounded-full h-2 mb-2">
      <div
        class="h-2 rounded-full transition-all duration-500"
        :class="progressBarClass"
        :style="{ width: progressPercent + '%' }"
      />
    </div>

    <div class="flex items-center justify-between gap-3">
      <span class="text-xs text-text-secondary">
        {{ reward.piecesEarned }} / {{ reward.piecesRequired }} pieces
      </span>

      <div class="flex items-center gap-3 shrink-0">
        <svg
          v-if="reward.isRecurring"
          class="w-3.5 h-3.5 text-text-secondary"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          viewBox="0 0 24 24"
          role="img"
          aria-label="Recurring reward"
        >
          <title>Recurring reward</title>
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h5M20 20v-5h-5M5.1 15A7 7 0 0118.9 9M18.9 9L20 4M18.9 15a7 7 0 01-13.8 0M5.1 15L4 20" />
        </svg>
        <button
          v-if="reward.status === 'ACHIEVED'"
          @click="$emit('claim', reward.id)"
          :disabled="loading"
          class="min-h-11 text-sm font-medium transition-all disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
          :class="[tc.button.rounded, tc.button.padding, tc.button.primary]"
        >
          Claim
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";

const props = defineProps({
  reward: { type: Object, required: true },
  loading: { type: Boolean, default: false },
});

defineEmits(["claim"]);

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);
const { hoverClass } = useThemeAnimation();

const progressPercent = computed(() => {
  if (props.reward.piecesRequired === 0) return 0;
  return Math.min(
    100,
    Math.round((props.reward.piecesEarned / props.reward.piecesRequired) * 100)
  );
});

const statusClass = computed(() => {
  switch (props.reward.status) {
    case "ACHIEVED":
      return "bg-accent/20 text-accent rounded-full";
    default:
      // PENDING / CLAIMED: the theme's badge token carries bg, text and rounding.
      return tc.value.badge.base;
  }
});

const statusLabel = computed(() => {
  switch (props.reward.status) {
    case "ACHIEVED":
      return "Ready";
    case "CLAIMED":
      return "Claimed";
    default:
      return `${progressPercent.value}%`;
  }
});

const progressBarClass = computed(() => {
  if (props.reward.status === "ACHIEVED") return "bg-accent";
  return "bg-accent/60";
});
</script>
