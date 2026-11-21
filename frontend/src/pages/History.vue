<template>
  <div class="px-4 pt-6 pb-4 max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-text-primary mb-4">History</h1>

    <!-- Habit filter -->
    <div class="mb-4" :style="getCardEntranceStyle(0)">
      <select
        v-model="selectedHabit"
        @change="navigate"
        class="w-full px-3 py-2 text-sm appearance-none cursor-pointer"
        :class="tc.select.base"
      >
        <option value="">All habits</option>
        <option v-for="h in habits" :key="h.id" :value="h.id">
          {{ h.name }}
        </option>
      </select>
    </div>

    <!-- Calendar -->
    <div
      class="p-4"
      :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra, hoverClass]"
      :style="getCardEntranceStyle(1)"
    >
      <CalendarGrid
        :currentMonth="currentMonth"
        :completions="completions"
        :userToday="userToday"
        :filtered="!!selectedHabit"
        :selectedDate="selectedDay"
        detailId="history-day-detail"
        @navigate="navigateMonth"
        @selectDay="selectDay"
      />
    </div>

    <!-- Day detail -->
    <div
      v-if="selectedDay"
      id="history-day-detail"
      class="mt-4 p-4"
      :class="[tc.card.rounded, tc.card.border, tc.card.bg, tc.card.extra]"
      data-testid="day-detail"
    >
      <h2 class="text-sm font-medium text-text-primary mb-2">{{ selectedDayLabel }}</h2>
      <p v-if="dayDetail.count === 0" class="text-sm text-text-secondary">Nothing completed.</p>
      <ul v-else class="space-y-1">
        <li v-for="name in dayDetail.names" :key="name" class="text-sm text-text-primary flex items-center gap-2">
          <span class="text-accent" aria-hidden="true">✓</span>{{ name }}
        </li>
        <li v-if="dayDetail.otherCount > 0" class="text-sm text-text-secondary">
          {{ dayDetail.otherCount }} other {{ dayDetail.otherCount === 1 ? "habit" : "habits" }}
        </li>
      </ul>
    </div>

    <!-- Legend -->
    <div v-if="habits.length > 0" class="mt-4 flex items-center gap-2" :style="getCardEntranceStyle(2)">
      <template v-if="selectedHabit">
        <span class="w-2 h-2 rounded-full bg-accent" aria-hidden="true" />
        <span class="text-xs text-text-secondary">= completed</span>
      </template>
      <span v-else class="text-xs text-text-secondary">
        Number under a day = habits completed. Tap a day to see which.
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from "vue";
import { router } from "@inertiajs/vue3";
import CalendarGrid from "../components/CalendarGrid.vue";
import { dayCompletions } from "../utils/dayCompletions.js";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";

const props = defineProps({
  currentMonth: { type: String, required: true },
  completions: { type: Object, default: () => ({}) },
  habits: { type: Array, default: () => [] },
  selectedHabit: { type: [String, Number, null], default: null },
  userToday: { type: String, default: null },
});

const selectedHabit = ref(props.selectedHabit || "");

watch(() => props.selectedHabit, (v) => {
  selectedHabit.value = v || "";
});

// Selected day for the detail list. Navigation keeps component state
// (preserveState), so clear it whenever the month or filter changes.
const selectedDay = ref(null);
watch(() => [props.currentMonth, props.selectedHabit], () => {
  selectedDay.value = null;
});

function selectDay(iso) {
  selectedDay.value = selectedDay.value === iso ? null : iso;
}

const dayDetail = computed(() =>
  selectedDay.value ? dayCompletions(props.completions, props.habits, selectedDay.value) : null,
);

const MONTHS = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];

const selectedDayLabel = computed(() => {
  if (!selectedDay.value) return "";
  const [, m, d] = selectedDay.value.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}`;
});

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);
const { getCardEntranceStyle, hoverClass } = useThemeAnimation();

function navigate() {
  const params = new URLSearchParams();
  params.set("month", props.currentMonth);
  if (selectedHabit.value) params.set("habit", selectedHabit.value);
  router.get(`/history/?${params.toString()}`, {}, { preserveState: true });
}

function navigateMonth(month) {
  const params = new URLSearchParams();
  params.set("month", month);
  if (selectedHabit.value) params.set("habit", selectedHabit.value);
  router.get(`/history/?${params.toString()}`, {}, { preserveState: true });
}
</script>
