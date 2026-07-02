<template>
  <div class="mb-6">
    <!-- ═══ ring (Night Arcade): progress ring + points ═══ -->
    <div v-if="headerStyle === 'ring'" class="flex items-center gap-5">
      <div class="w-16 h-16 rounded-full grid place-items-center shrink-0" :style="ringStyle">
        <div class="w-[52px] h-[52px] rounded-full grid place-items-center bg-bg-primary">
          <span class="font-bold text-[15px] text-text-primary"
            >{{ stats.completedToday }}<span class="text-text-muted font-medium">/{{ stats.totalToday }}</span></span
          >
        </div>
      </div>
      <div>
        <h1 class="text-2xl font-bold text-text-primary">Today</h1>
        <p class="text-sm text-text-secondary mt-0.5">
          {{ dateLabel }}
          <span v-if="stats.totalPointsToday > 0" class="text-accent font-semibold">
            · +{{ stats.totalPointsToday }} pts</span
          >
        </p>
      </div>
    </div>

    <!-- ═══ punches (Ticket Stub): weekday + punch tally ═══ -->
    <div v-else-if="headerStyle === 'punches'" class="flex items-end gap-5">
      <div>
        <h1 class="text-[26px] font-bold text-text-primary tracking-tight">{{ weekdayLabel }}</h1>
        <p class="text-sm text-text-secondary mt-0.5">
          {{ dateLabel }}
          <span v-if="stats.totalPointsToday > 0" class="text-accent font-semibold">
            · +{{ stats.totalPointsToday }} pts</span
          >
        </p>
      </div>
      <div class="ml-auto flex items-center gap-2.5 pb-1">
        <span class="text-xs text-text-secondary font-medium">Today's punches</span>
        <div class="flex gap-1.5">
          <span
            v-for="i in stats.totalToday"
            :key="i"
            class="w-4 h-4 rounded-full grid place-items-center"
            :class="i <= stats.completedToday
              ? 'bg-accent text-white text-[10px]'
              : 'border-[1.5px] border-dashed border-text-muted'"
            >{{ i <= stats.completedToday ? '✓' : '' }}</span
          >
        </div>
      </div>
    </div>

    <!-- ═══ xp (Quest Log): stat line + progress bar ═══ -->
    <div v-else-if="headerStyle === 'xp'" class="bg-bg-card border border-bg-card-hover rounded-lg px-4 py-3.5">
      <div class="flex items-baseline gap-4">
        <h1 class="text-[17px] font-semibold text-text-primary uppercase tracking-wide">
          Today — {{ shortDateLabel }}
        </h1>
        <span class="text-xs text-text-secondary"
          >quests: <span class="text-accent font-semibold">{{ stats.completedToday }}/{{ stats.totalToday }}</span></span
        >
        <span v-if="stats.totalPointsToday > 0" class="text-xs text-text-secondary"
          >points: <span class="text-streak-fire font-semibold">+{{ stats.totalPointsToday }}</span></span
        >
      </div>
      <div class="flex items-center gap-2.5 mt-2.5">
        <div class="flex-1 h-2 rounded bg-bg-card-hover overflow-hidden">
          <div class="h-full bg-accent transition-all duration-500" :style="{ width: pct + '%' }"></div>
        </div>
        <span class="text-[11px] text-text-secondary">{{ pct }}%</span>
      </div>
    </div>

    <!-- ═══ plain (default, all existing themes) ═══ -->
    <div v-else>
      <h1 class="text-2xl font-bold text-text-primary mb-1">Today</h1>
      <p class="text-sm text-text-secondary">
        {{ stats.completedToday }} / {{ stats.totalToday }} habits done
        <span v-if="stats.totalPointsToday > 0" class="ml-2 text-accent">
          +{{ stats.totalPointsToday }}pts
        </span>
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../composables/useTheme.js";

const props = defineProps({
  stats: { type: Object, default: () => ({ completedToday: 0, totalToday: 0, totalPointsToday: 0 }) },
});

const { themeConfig } = useTheme();

const headerStyle = computed(() => themeConfig.value.pageLayout?.headerStyle || "plain");

const pct = computed(() => {
  const total = props.stats.totalToday || 0;
  if (!total) return 0;
  return Math.round((props.stats.completedToday / total) * 100);
});

// conic-gradient progress ring driven by the accent CSS var
const ringStyle = computed(() => ({
  background: `conic-gradient(var(--color-accent) 0 ${pct.value * 3.6}deg, var(--color-bg-card-hover) ${pct.value * 3.6}deg 360deg)`,
}));

const now = new Date();
const weekdayLabel = now.toLocaleDateString("en-US", { weekday: "long" });
const dateLabel = now.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
const shortDateLabel = now
  .toLocaleDateString("en-US", { month: "short", day: "2-digit" })
  .toUpperCase();
</script>
