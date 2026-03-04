<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <!-- Toast mode: small notification in corner, no backdrop -->
      <div
        v-if="visible && isToast"
        class="fixed top-4 right-4 z-50 max-w-xs w-full"
        @click="dismiss"
      >
        <RewardToast
          :reward-name="rewardName"
          :pieces-earned="piecesEarned"
          :pieces-required="piecesRequired"
        />
      </div>

      <!-- Expand-from-card mode: centered overlay with backdrop -->
      <div
        v-else-if="visible"
        class="fixed inset-0 z-50 flex items-center justify-center"
        @click="dismiss"
      >
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" />
        <div
          class="relative z-10 max-w-sm w-full mx-4"
          :style="cardPositionStyle"
          @click.stop
        >
          <component
            :is="celebrationComponent"
            :reward-name="rewardName"
            :pieces-earned="piecesEarned"
            :pieces-required="piecesRequired"
            :card-rect="cardRect"
          />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, watch, onUnmounted, ref } from "vue";
import { useTheme } from "../../composables/useTheme.js";
import RewardDefault from "./RewardDefault.vue";
import RewardParticles from "./RewardParticles.vue";
import RewardQuiet from "./RewardQuiet.vue";
import RewardToast from "./RewardToast.vue";

const props = defineProps({
  visible: { type: Boolean, default: false },
  rewardName: { type: String, default: "" },
  piecesEarned: { type: Number, default: null },
  piecesRequired: { type: Number, default: null },
  cardRect: { type: Object, default: null },
});

const emit = defineEmits(["dismiss"]);
const { themeConfig } = useTheme();

const isToast = computed(() =>
  themeConfig.value.reward?.displayMode === "toast"
);

const celebrationComponent = computed(() => {
  const type = themeConfig.value.animations?.completionCelebration;
  switch (type) {
    case "burst-particles":
      return RewardParticles;
    case "fade-quiet":
      return RewardQuiet;
    default:
      return RewardDefault;
  }
});

const cardPositionStyle = computed(() => {
  if (!props.cardRect) return {};
  // Offset from viewport center toward the source card's vertical position
  const cardCenter = props.cardRect.top + props.cardRect.height / 2;
  const viewportCenter = window.innerHeight / 2;
  const offset = Math.max(-viewportCenter + 80, Math.min(cardCenter - viewportCenter, viewportCenter - 200));
  return { marginTop: `${offset}px` };
});

// Auto-dismiss after 3s
const timer = ref(null);

watch(() => props.visible, (val) => {
  if (timer.value) clearTimeout(timer.value);
  if (val) {
    timer.value = setTimeout(dismiss, 3000);
  }
});

onUnmounted(() => {
  if (timer.value) clearTimeout(timer.value);
});

function dismiss() {
  if (timer.value) clearTimeout(timer.value);
  emit("dismiss");
}
</script>
