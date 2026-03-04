<template>
  <div
    class="px-4 py-3 flex items-center gap-3"
    :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra]"
    :style="animStyle"
  >
    <span class="text-xl">🎁</span>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-text-primary truncate">{{ rewardName }}</p>
      <p v-if="piecesEarned != null && piecesRequired != null" class="text-xs text-text-secondary">
        {{ piecesEarned }}/{{ piecesRequired }} pieces
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue";
import { useTheme } from "../../composables/useTheme.js";

defineProps({
  rewardName: { type: String, default: "" },
  piecesEarned: { type: Number, default: null },
  piecesRequired: { type: Number, default: null },
});

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);

// Slide in from right
const animStyle = ref({ transform: "translateX(100%)", opacity: "0", transition: "all 0.3s ease-out" });
onMounted(() => {
  requestAnimationFrame(() => {
    animStyle.value = { transform: "translateX(0)", opacity: "1", transition: "all 0.3s ease-out" };
  });
});
</script>
