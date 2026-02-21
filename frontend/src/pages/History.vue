<template>
  <div class="px-4 pt-6 pb-4 max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-text-primary mb-4">History</h1>

    <!-- Habit filter -->
    <div class="mb-4">
      <select
        v-model="selectedHabit"
        @change="navigate"
        class="w-full bg-bg-card border border-gray-800 rounded-lg px-3 py-2 text-sm text-text-primary appearance-none cursor-pointer"
      >
        <option value="">All habits</option>
        <option v-for="h in habits" :key="h.id" :value="h.id">
          {{ h.name }}
        </option>
      </select>
    </div>

    <!-- Calendar -->
    <div class="bg-bg-card rounded-xl p-4">
      <CalendarGrid
        :currentMonth="currentMonth"
        :completions="completions"
        :userToday="userToday"
        @navigate="navigateMonth"
      />
    </div>

    <!-- Legend -->
    <div v-if="habits.length > 0" class="mt-4 flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-accent" />
      <span class="text-xs text-text-secondary">= habit completed</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { router } from "@inertiajs/vue3";
import CalendarGrid from "../components/CalendarGrid.vue";

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
