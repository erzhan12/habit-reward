<template>
  <div class="shrink-0" :class="position === 'left' ? 'mr-3' : 'ml-3'">
    <button
      @click="handleToggle"
      :disabled="loading"
      class="relative inline-flex h-7 w-12 items-center rounded-full transition-colors duration-200 focus:outline-none disabled:opacity-50"
      :class="habit.completedToday ? 'bg-accent' : ''"
      :style="!habit.completedToday ? { backgroundColor: 'var(--color-bg-card-hover)' } : {}"
      role="switch"
      :aria-checked="habit.completedToday"
    >
      <span
        class="inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200"
        :class="habit.completedToday ? 'translate-x-6' : 'translate-x-1'"
      />
    </button>
  </div>
</template>

<script setup>
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

function handleToggle() {
  if (props.habit.completedToday) {
    emit("revert", props.habit.id);
  } else {
    emit("complete", props.habit.id);
  }
}
</script>
