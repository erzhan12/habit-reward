<template>
  <div
    ref="cardEl"
    class="p-6 text-center"
    :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra]"
    :style="animStyle"
  >
    <div class="text-3xl mb-3">🎉</div>
    <h3 class="text-lg font-bold text-text-primary mb-1">Reward!</h3>
    <p class="text-accent font-semibold">{{ rewardName }}</p>
    <p v-if="piecesEarned != null && piecesRequired != null" class="text-sm text-text-secondary mt-2">
      {{ piecesEarned }} / {{ piecesRequired }} pieces
    </p>
    <div
      v-if="piecesEarned != null && piecesRequired != null"
      class="mt-3 h-2 rounded-full bg-bg-card-hover overflow-hidden"
    >
      <div
        class="h-full bg-accent rounded-full transition-all duration-500"
        :style="{ width: progressPercent + '%' }"
      />
    </div>
    <p class="text-xs text-text-secondary mt-3">Tap to dismiss</p>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue";
import { useTheme } from "../../composables/useTheme.js";
import { spawnParticles } from "../../utils/particles.js";

const props = defineProps({
  rewardName: { type: String, default: "" },
  piecesEarned: { type: Number, default: null },
  piecesRequired: { type: Number, default: null },
  cardRect: { type: Object, default: null },
});

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);

const progressPercent = computed(() => {
  if (props.piecesRequired == null || props.piecesRequired === 0) return 0;
  return Math.min((props.piecesEarned / props.piecesRequired) * 100, 100);
});

// Scale-up entrance + particle burst
const animStyle = ref({ transform: "scale(0.8)", opacity: "0", transition: "all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)" });
onMounted(() => {
  requestAnimationFrame(() => {
    animStyle.value = { transform: "scale(1)", opacity: "1", transition: "all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)" };
  });

  // Fire particles from the center of the screen or card
  const x = props.cardRect
    ? props.cardRect.left + props.cardRect.width / 2
    : window.innerWidth / 2;
  const y = props.cardRect
    ? props.cardRect.top + props.cardRect.height / 2
    : window.innerHeight / 2;

  spawnParticles({
    x,
    y,
    count: 20,
    colors: ["#06b6d4", "#ec4899", "#fbbf24", "#10b981", "#6366f1"],
    duration: 800,
  });
});
</script>
