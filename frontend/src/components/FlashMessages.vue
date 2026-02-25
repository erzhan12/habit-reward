<template>
  <div class="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
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
        class="px-4 py-3 rounded-lg text-sm shadow-lg"
        :class="badgeClass(msg.type)"
      >
        {{ msg.text }}
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";

const props = defineProps({
  messages: { type: Array, default: () => [] },
});

const visible = ref([]);

function show(msgs) {
  if (!msgs || !msgs.length) return;
  visible.value = [...msgs];
  setTimeout(() => {
    visible.value = [];
  }, 4000);
}

function badgeClass(type) {
  if (type === "error") return "bg-red-900/80 text-red-200 border border-red-700";
  if (type === "success") return "bg-emerald-900/80 text-emerald-200 border border-emerald-700";
  return "bg-gray-800/80 text-gray-200 border border-gray-600";
}

onMounted(() => show(props.messages));
watch(() => props.messages, show);
</script>
