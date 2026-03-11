<template>
  <div class="shrink-0" :class="position === 'left' ? 'mr-3' : 'ml-3'">
    <button
      v-if="!habit.completedToday"
      @click="$emit('complete', habit.id)"
      :disabled="loading"
      class="text-sm font-medium transition-all disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
      :class="[tc.button.rounded, tc.button.padding, tc.button.primary]"
    >
      Done
    </button>
    <button
      v-else
      @click="$emit('revert', habit.id)"
      :disabled="loading"
      class="text-sm font-medium transition-all disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
      :class="[tc.button.rounded, tc.button.padding, tc.button.secondary]"
    >
      Undo
    </button>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../../composables/useTheme.js";

defineProps({
  habit: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  position: {
    type: String,
    default: "right",
    validator: (v) => ["left", "right", "bottom"].includes(v),
  },
});

defineEmits(["complete", "revert"]);

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);
</script>
