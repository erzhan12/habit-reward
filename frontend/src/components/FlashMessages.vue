<template>
  <div class="fixed top-4 right-4 z-50 space-y-2 max-w-sm" aria-live="polite">
    <TransitionGroup
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-[-8px]"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-[-8px]"
    >
      <div
        v-for="(msg, i) in visible"
        :key="i"
        class="flash px-4 py-3 text-sm shadow-lg border"
        :class="[themeConfig.classes.card.rounded, badgeClass(msg.type)]"
        :role="msg.type === 'error' ? 'alert' : undefined"
      >
        {{ msg.text }}
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";
import { useTheme } from "../composables/useTheme.js";

const props = defineProps({
  messages: { type: Array, default: () => [] },
});

const { themeConfig } = useTheme();
const visible = ref([]);

function show(msgs) {
  if (!msgs || !msgs.length) return;
  visible.value = [...msgs];
  setTimeout(() => {
    visible.value = [];
  }, 4000);
}

// Tones come from theme tokens so toasts read on light and dark themes alike.
function badgeClass(type) {
  if (type === "error") return "flash-error";
  if (type === "success") return "flash-success";
  return "flash-info";
}

onMounted(() => show(props.messages));
watch(() => props.messages, show);
</script>

<style scoped>
/* Mixed over the page colour: it is opaque in every theme, while the card
   colour is translucent in ios_native. */
.flash {
  color: var(--color-text-primary);
}
.flash-error {
  background-color: color-mix(in srgb, var(--color-danger) 15%, var(--color-bg-primary));
  border-color: var(--color-danger);
}
.flash-success {
  background-color: color-mix(in srgb, var(--color-accent) 15%, var(--color-bg-primary));
  border-color: var(--color-accent);
}
.flash-info {
  background-color: color-mix(in srgb, var(--color-border) 40%, var(--color-bg-primary));
  border-color: var(--color-border);
}
</style>
