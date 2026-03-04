<template>
  <div
    class="relative overflow-hidden"
    :class="tc.card.rounded"
    @touchstart="onTouchStart"
    @touchmove="onTouchMove"
    @touchend="onTouchEnd"
  >
    <!-- Revealed panel behind the card content -->
    <div
      class="absolute inset-0 flex items-center bg-accent transition-opacity"
      :class="revealOpacity > 0 ? 'opacity-100' : 'opacity-0'"
      :style="{ opacity: revealOpacity }"
    >
      <div class="flex items-center gap-2 pl-6 text-white font-medium">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        <span class="text-sm">Done!</span>
      </div>
    </div>

    <!-- Slidable card content -->
    <div
      class="relative transition-transform"
      :class="isAnimating ? 'duration-200' : 'duration-0'"
      :style="{ transform: `translateX(${offsetX}px)` }"
    >
      <slot />
    </div>

    <!-- Undo button for completed habits (no swipe needed) -->
    <div v-if="habit.completedToday" class="absolute top-0 right-0 bottom-0 flex items-center pr-4">
      <button
        @click="$emit('revert', habit.id)"
        :disabled="loading"
        class="text-sm font-medium transition-all disabled:opacity-50"
        :class="[tc.button.rounded, tc.button.padding, tc.button.secondary]"
      >
        Undo
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useTheme } from "../../composables/useTheme.js";

const SWIPE_THRESHOLD = 100;

const props = defineProps({
  habit: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  position: {
    type: String,
    default: "right",
    validator: (v) => ["left", "right", "bottom"].includes(v),
  },
});

const emit = defineEmits(["complete", "revert"]);

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);

const startX = ref(0);
const offsetX = ref(0);
const isAnimating = ref(false);
const revealOpacity = computed(() =>
  Math.min(Math.max(offsetX.value / SWIPE_THRESHOLD, 0), 1)
);

function onTouchStart(e) {
  if (props.habit.completedToday || props.loading) return;
  isAnimating.value = false;
  startX.value = e.touches[0].clientX;
}

function onTouchMove(e) {
  if (props.habit.completedToday || props.loading) return;
  const delta = e.touches[0].clientX - startX.value;
  // Only allow right swipe
  offsetX.value = Math.max(0, delta);
}

function onTouchEnd() {
  if (props.habit.completedToday || props.loading) return;
  isAnimating.value = true;

  if (offsetX.value >= SWIPE_THRESHOLD) {
    emit("complete", props.habit.id);
  }

  offsetX.value = 0;
}
</script>
