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
      <div class="bg-gray-800 rounded-xl p-4 shadow-lg border border-gray-700 flex items-center justify-between">
        <span class="text-sm text-text-primary">{{ message }}</span>
        <button
          @click="$emit('undo')"
          class="ml-3 px-3 py-1 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors shrink-0"
        >
          Undo
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  message: { type: String, default: "Habit completed" },
});

defineEmits(["undo"]);
</script>
