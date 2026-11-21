<template>
  <div>
    <!-- Month navigation -->
    <div class="flex items-center justify-between mb-4">
      <button
        type="button"
        aria-label="Previous month"
        @click="$emit('navigate', prevMonth)"
        class="min-w-11 min-h-11 grid place-items-center text-text-secondary transition-colors"
        :class="[themeConfig.classes.card.rounded, 'hover:bg-bg-card-hover']"
      >
        &larr;
      </button>
      <h2 class="text-lg font-medium text-text-primary">{{ monthLabel }}</h2>
      <button
        type="button"
        aria-label="Next month"
        @click="$emit('navigate', nextMonth)"
        :disabled="isCurrentMonth"
        class="min-w-11 min-h-11 grid place-items-center text-text-secondary transition-colors disabled:opacity-30"
        :class="[themeConfig.classes.card.rounded, 'hover:bg-bg-card-hover']"
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
      <div v-for="n in startOffset" :key="'empty-' + n" />

      <button
        v-for="day in daysInMonth"
        :key="day"
        type="button"
        class="aspect-square flex flex-col items-center justify-center text-sm relative cursor-pointer"
        :class="[themeConfig.classes.card.rounded, dayClass(day)]"
        :aria-label="dayLabel(day)"
        :aria-expanded="formatDate(day) === selectedDate"
        :aria-controls="detailId || undefined"
        @click="$emit('selectDay', formatDate(day))"
      >
        <span>{{ day }}</span>
        <!-- unfiltered: how many habits were done; filtered: done or not -->
        <span
          v-if="getDayCompletions(day).length > 0 && !filtered"
          class="text-[10px] leading-none font-semibold text-accent mt-0.5"
          aria-hidden="true"
        >{{ getDayCompletions(day).length }}</span>
        <span
          v-else-if="getDayCompletions(day).length > 0"
          class="w-1.5 h-1.5 rounded-full bg-accent mt-1"
          aria-hidden="true"
        />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../composables/useTheme.js";

const props = defineProps({
  currentMonth: { type: String, required: true },
  completions: { type: Object, default: () => ({}) },
  userToday: { type: String, default: null },
  // one habit selected in History: show a dot instead of a count
  filtered: { type: Boolean, default: false },
  selectedDate: { type: String, default: null },
  // id of the day-detail panel the day buttons open and close
  detailId: { type: String, default: null },
});

defineEmits(["navigate", "selectDay"]);

const { themeConfig } = useTheme();

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

const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];

function dayLabel(day) {
  const n = getDayCompletions(day).length;
  const done = props.filtered
    ? (n > 0 ? "completed" : "not completed")
    : `${n} ${n === 1 ? "habit" : "habits"} completed`;
  return `${day} ${MONTH_NAMES[month.value - 1]}, ${done}`;
}

function dayClass(day) {
  const classes = [];
  if (formatDate(day) === props.selectedDate) classes.push("ring-2 ring-accent");
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
