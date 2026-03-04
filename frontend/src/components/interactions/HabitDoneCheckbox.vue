<template>
  <div class="shrink-0" :class="position === 'left' ? 'mr-3' : 'ml-3'">
    <label class="flex items-center cursor-pointer" :class="loading ? 'opacity-50 pointer-events-none' : ''">
      <input
        type="checkbox"
        :checked="habit.completedToday"
        @change="handleChange"
        :disabled="loading"
        class="sr-only peer"
      />
      <div
        class="w-6 h-6 border-2 flex items-center justify-center transition-all"
        :class="[
          tc.button.rounded === 'rounded-full' ? 'rounded-full' : tc.button.rounded === 'rounded-none' ? 'rounded-none' : 'rounded-md',
          habit.completedToday
            ? 'bg-accent border-accent'
            : 'border-text-secondary hover:border-accent',
        ]"
      >
        <svg
          v-if="habit.completedToday"
          class="w-4 h-4 text-white"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="3"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    </label>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../../composables/useTheme.js";

const props = defineProps({
  habit: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  position: {
    type: String,
    default: "left",
    validator: (v) => ["left", "right", "bottom"].includes(v),
  },
});

const emit = defineEmits(["complete", "revert"]);

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);

function handleChange() {
  if (props.habit.completedToday) {
    emit("revert", props.habit.id);
  } else {
    emit("complete", props.habit.id);
  }
}
</script>
