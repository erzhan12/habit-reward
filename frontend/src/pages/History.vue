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
        @navigate="navigateMonth"
      />
    </div>

    <!-- Legend -->
    <div v-if="habits.length > 0" class="mt-4 flex items-center gap-2" :style="getCardEntranceStyle(2)">
      <span class="w-2 h-2 rounded-full bg-accent" />
      <span class="text-xs text-text-secondary">= habit completed</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from "vue";
import { router } from "@inertiajs/vue3";
import CalendarGrid from "../components/CalendarGrid.vue";
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
