<template>
  <Transition
    enter-active-class="transition-all duration-300 ease-out"
    enter-from-class="translate-y-full opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transition-all duration-200 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="translate-y-full opacity-0"
  >
    <div
      v-if="visible"
      class="fixed bottom-24 lg:bottom-6 left-4 right-4 lg:left-auto lg:right-6 lg:w-80 z-50"
    >
      <div
        class="p-4 shadow-lg border flex items-center justify-between"
        :class="[tc.card.rounded, tc.card.bg, tc.card.border || 'border-gray-700', tc.card.extra]"
      >
        <span class="text-sm text-text-primary">{{ message }}</span>
        <button
          @click="$emit('undo')"
          class="ml-3 text-sm font-medium transition-all shrink-0"
          :class="[tc.button.rounded, 'px-3 py-1', tc.button.primary]"
        >
          Undo
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../composables/useTheme.js";

defineProps({
  visible: { type: Boolean, default: false },
  message: { type: String, default: "Habit completed" },
});

defineEmits(["undo"]);

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);
</script>
