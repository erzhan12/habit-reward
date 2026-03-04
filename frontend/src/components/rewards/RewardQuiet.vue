<template>
  <div
    class="p-5 text-center"
    :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra]"
    :style="animStyle"
  >
    <p class="text-sm text-text-secondary">Reward earned</p>
    <p class="text-accent font-medium mt-1">{{ rewardName }}</p>
    <p v-if="piecesEarned != null && piecesRequired != null" class="text-xs text-text-secondary mt-1">
      {{ piecesEarned }} / {{ piecesRequired }}
    </p>
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

// Quiet fade-in
const animStyle = ref({ opacity: "0", transition: "opacity 0.4s ease-out" });
onMounted(() => {
  requestAnimationFrame(() => {
    animStyle.value = { opacity: "1", transition: "opacity 0.4s ease-out" };
  });
});
</script>
