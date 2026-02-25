<template>
  <div>
    <!-- Month navigation -->
    <div class="flex items-center justify-between mb-4">
      <button
        @click="$emit('navigate', prevMonth)"
        class="p-2 rounded-lg hover:bg-bg-card-hover text-text-secondary transition-colors"
      >
        &larr;
      </button>
      <h2 class="text-lg font-medium text-text-primary">{{ monthLabel }}</h2>
      <button
        @click="$emit('navigate', nextMonth)"
        :disabled="isCurrentMonth"
        class="p-2 rounded-lg hover:bg-bg-card-hover text-text-secondary transition-colors disabled:opacity-30"
      >
        &rarr;
      </button>
    </div>

    <!-- Day headers -->
    <div class="grid grid-cols-7 gap-1 mb-1">
      <div
        v-for="day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']"
        :key="day"
        class="text-center text-xs text-text-secondary py-1"
      >
        {{ day }}
      </div>
    </div>

    <!-- Calendar days -->
    <div class="grid grid-cols-7 gap-1">
      <!-- Empty cells for offset -->
      <div v-for="n in startOffset" :key="'empty-' + n" />

      <div
        v-for="day in daysInMonth"
        :key="day"
        class="aspect-square flex flex-col items-center justify-center rounded-lg text-sm relative"
        :class="dayClass(day)"
        @click="$emit('selectDay', formatDate(day))"
      >
        <span>{{ day }}</span>
        <!-- Completion dots -->
        <div v-if="getDayCompletions(day).length > 0" class="flex gap-0.5 mt-0.5">
          <span
            v-for="(_, i) in getDayCompletions(day).slice(0, 4)"
            :key="i"
            class="w-1 h-1 rounded-full bg-accent"
          />
          <span
            v-if="getDayCompletions(day).length > 4"
            class="w-1 h-1 rounded-full bg-accent/50"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  currentMonth: { type: String, required: true }, // "2026-02"
  completions: { type: Object, default: () => ({}) }, // { habitId: ["2026-02-01", ...] }
  userToday: { type: String, default: null }, // "2026-02-21" (server timezone)
});

defineEmits(["navigate", "selectDay"]);

const year = computed(() => parseInt(props.currentMonth.split("-")[0]));
const month = computed(() => parseInt(props.currentMonth.split("-")[1]));

const monthLabel = computed(() => {
  const date = new Date(year.value, month.value - 1);
  return date.toLocaleDateString("en", { month: "long", year: "numeric" });
});

const daysInMonth = computed(() => {
  return new Date(year.value, month.value, 0).getDate();
});

const startOffset = computed(() => {
  // Monday = 0, Sunday = 6
  const firstDay = new Date(year.value, month.value - 1, 1).getDay();
  return firstDay === 0 ? 6 : firstDay - 1;
});

const prevMonth = computed(() => {
  if (month.value === 1) return `${year.value - 1}-12`;
  return `${year.value}-${String(month.value - 1).padStart(2, "0")}`;
});

const nextMonth = computed(() => {
  if (month.value === 12) return `${year.value + 1}-01`;
  return `${year.value}-${String(month.value + 1).padStart(2, "0")}`;
});

const isCurrentMonth = computed(() => {
  if (props.userToday) {
    const [y, m] = props.userToday.split("-").map(Number);
    return year.value === y && month.value === m;
  }
  const now = new Date();
  return year.value === now.getFullYear() && month.value === now.getMonth() + 1;
});

const today = computed(() => {
  if (props.userToday) {
    const [y, m, d] = props.userToday.split("-").map(Number);
    if (year.value === y && month.value === m) return d;
    return null;
  }
  const now = new Date();
  if (year.value === now.getFullYear() && month.value === now.getMonth() + 1) {
    return now.getDate();
  }
  return null;
});

function formatDate(day) {
  return `${year.value}-${String(month.value).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

const completionsByDate = computed(() => {
  const map = {};
  for (const habitId in props.completions) {
    for (const dateStr of props.completions[habitId]) {
      if (!map[dateStr]) map[dateStr] = [];
      map[dateStr].push(habitId);
    }
  }
  return map;
});

function getDayCompletions(day) {
  return completionsByDate.value[formatDate(day)] || [];
}

function dayClass(day) {
  const classes = [];
  if (day === today.value) {
    classes.push("bg-accent/20 text-accent font-bold");
  } else if (getDayCompletions(day).length > 0) {
    classes.push("bg-bg-card text-text-primary");
  } else {
    classes.push("text-text-secondary");
  }
  return classes.join(" ");
}
</script>
