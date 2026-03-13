<template>
  <div class="px-4 pt-6 pb-4 max-w-2xl mx-auto">
    <!-- Period selector -->
    <div class="flex gap-2 mb-6" :style="getCardEntranceStyle(0)">
      <button
        v-for="p in periods"
        :key="p"
        @click="switchPeriod(p)"
        class="px-4 py-1.5 text-sm font-medium rounded-full transition-colors"
        :class="p === currentPeriod ? tc.button.primary : tc.button.secondary"
      >
        {{ p }}
      </button>
    </div>

    <!-- Empty state -->
    <div v-if="rates.length === 0" class="text-center py-12">
      <p class="text-text-secondary">No analytics data available. Complete some habits to see your stats!</p>
    </div>

    <template v-else>
      <!-- Section 1: Summary cards -->
      <div
        class="p-4 mb-6"
        :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra]"
        :style="getCardEntranceStyle(1)"
      >
        <h1 class="text-2xl font-bold text-text-primary mb-3">Analytics</h1>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div>
            <p class="text-2xl font-bold text-accent">{{ formatPercent(summary.avgCompletionRate) }}</p>
            <p class="text-xs text-text-secondary">Avg completion</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-text-primary">{{ summary.totalCompletions }}</p>
            <p class="text-xs text-text-secondary">Total completions</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-accent truncate" :title="summary.bestHabit?.name">
              {{ summary.bestHabit?.name || 'N/A' }}
            </p>
            <p class="text-xs text-text-secondary">
              Best habit {{ summary.bestHabit ? `(${formatPercent(summary.bestHabit.rate)})` : '' }}
            </p>
          </div>
          <div>
            <p class="text-2xl font-bold text-text-primary">{{ summary.totalAvailableDays }}</p>
            <p class="text-xs text-text-secondary">Available days</p>
          </div>
        </div>
      </div>

      <!-- Section 2: Completion rate bars -->
      <div
        class="p-4 mb-6"
        :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra]"
        :style="getCardEntranceStyle(2)"
      >
        <h2 class="text-lg font-semibold text-text-primary mb-3">Completion Rates</h2>
        <div class="space-y-3">
          <div v-for="rate in rates" :key="rate.habit_id">
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm font-medium text-text-primary truncate">{{ rate.habit_name }}</span>
              <span class="text-sm font-semibold text-accent ml-2 shrink-0">{{ formatPercent(rate.completion_rate) }}</span>
            </div>
            <div class="w-full h-2 rounded-full bg-bg-card-hover">
              <div
                class="h-2 rounded-full bg-accent transition-all duration-500"
                :style="{ width: `${(rate.completion_rate * 100).toFixed(0)}%` }"
              />
            </div>
            <p class="text-xs text-text-secondary mt-0.5">{{ rate.completed_days }} of {{ rate.available_days }} days</p>
          </div>
        </div>
      </div>

      <!-- Section 3: Rankings -->
      <div class="space-y-2 mb-6">
        <h2
          class="text-lg font-semibold text-text-primary"
          :style="getCardEntranceStyle(3)"
        >Rankings</h2>
        <div
          v-for="(r, idx) in rankings"
          :key="r.habit_id"
          class="p-3 flex items-center gap-3"
          :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra, hoverClass]"
          :style="getCardEntranceStyle(4 + idx)"
        >
          <span class="text-lg font-bold text-accent w-8 text-center shrink-0">#{{ r.rank }}</span>
          <div class="flex-1 min-w-0">
            <p class="font-medium text-text-primary truncate">{{ r.habit_name }}</p>
            <div class="flex items-center gap-3 mt-0.5 text-xs text-text-secondary">
              <span>{{ formatPercent(r.completion_rate) }}</span>
              <span>🔥 {{ r.current_streak }}</span>
              <span>Best: {{ r.longest_streak_in_range }}</span>
              <span>{{ r.total_completions }} done</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Section 4: Trend chart -->
      <div
        class="p-4"
        :class="[tc.card.rounded, tc.card.shadow, tc.card.border, tc.card.bg, tc.card.extra]"
        :style="getCardEntranceStyle(4 + rankings.length)"
      >
        <h2 class="text-lg font-semibold text-text-primary mb-3">Weekly Trends</h2>
        <div v-if="trends.weekly.length > 0" class="h-64">
          <Bar :data="chartData" :options="chartOptions" />
        </div>
        <p v-else class="text-sm text-text-secondary text-center py-8">Not enough data for trends yet.</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, watch, ref } from "vue";
import { router } from "@inertiajs/vue3";
import { Bar } from "vue-chartjs";
import { Chart, BarElement, CategoryScale, LinearScale, Tooltip } from "chart.js";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";

Chart.register(BarElement, CategoryScale, LinearScale, Tooltip);

const props = defineProps({
  rates: { type: Array, default: () => [] },
  rankings: { type: Array, default: () => [] },
  trends: { type: Object, default: () => ({ daily: [], weekly: [] }) },
  summary: {
    type: Object,
    default: () => ({
      avgCompletionRate: 0,
      totalCompletions: 0,
      bestHabit: null,
      totalAvailableDays: 0,
    }),
  },
  currentPeriod: { type: String, default: "30d" },
});

const periods = ["7d", "30d", "90d"];

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);
const { getCardEntranceStyle, hoverClass } = useThemeAnimation();

function switchPeriod(p) {
  router.get("/analytics/", { period: p }, { preserveScroll: true });
}

function formatPercent(rate) {
  return `${(rate * 100).toFixed(0)}%`;
}

// Chart.js reads CSS colors reactively for theme compatibility
function readCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const accentColor = ref(readCssVar("--color-accent"));
const textSecondaryColor = ref(readCssVar("--color-text-secondary"));

watch(
  () => themeConfig.value,
  () => {
    // Double-rAF ensures CSS vars are applied before reading — useTheme applies
    // vars in its own rAF, so we need to wait one more frame.
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        accentColor.value = readCssVar("--color-accent");
        textSecondaryColor.value = readCssVar("--color-text-secondary");
      });
    });
  },
);

function formatWeekLabel(dateStr) {
  // Parse YYYY-MM-DD without Date constructor to avoid timezone shifts
  const [, m, d] = dateStr.split("-").map(Number);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${months[m - 1]} ${d}`;
}

const chartData = computed(() => ({
  labels: props.trends.weekly.map((w) => formatWeekLabel(w.week_start)),
  datasets: [
    {
      label: "Completion Rate",
      data: props.trends.weekly.map((w) => +(w.rate * 100).toFixed(1)),
      backgroundColor: accentColor.value || "#6366f1",
      borderRadius: 4,
    },
  ],
}));

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.parsed.y}%`,
      },
    },
  },
  scales: {
    y: {
      min: 0,
      max: 100,
      ticks: {
        callback: (v) => `${v}%`,
        color: textSecondaryColor.value,
      },
      grid: { color: "rgba(128,128,128,0.1)" },
    },
    x: {
      ticks: {
        color: textSecondaryColor.value,
      },
      grid: { display: false },
    },
  },
}));
</script>
