<template>
  <div class="px-4 pt-6 pb-4 max-w-2xl mx-auto">
    <!-- Stats header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-text-primary mb-1">Today</h1>
      <p class="text-sm text-text-secondary">
        {{ stats.completedToday }} / {{ stats.totalToday }} habits done
        <span v-if="stats.totalPointsToday > 0" class="ml-2 text-accent">
          +{{ stats.totalPointsToday }}pts
        </span>
      </p>
    </div>

    <!-- Habit list / grid -->
    <div :class="listLayoutClass">
      <HabitCard
        v-for="(habit, idx) in habits"
        :key="habit.id"
        :ref="(el) => setCardRef(habit.id, el)"
        :habit="habit"
        :loading="loadingId === habit.id"
        :index="idx"
        @complete="completeHabit"
        @revert="revertHabit"
      />

      <div v-if="habits.length === 0" class="text-center py-12">
        <p class="text-text-secondary">No habits yet. Add some via the Telegram bot.</p>
      </div>
    </div>

    <!-- Undo toast -->
    <UndoToast
      :visible="undoVisible"
      :message="undoMessage"
      @undo="handleUndo"
    />
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from "vue";
import { router } from "@inertiajs/vue3";
import HabitCard from "../components/HabitCard.vue";
import UndoToast from "../components/UndoToast.vue";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";

defineProps({
  habits: { type: Array, default: () => [] },
  stats: { type: Object, default: () => ({}) },
  completionFlash: { type: Object, default: null },
});

const { themeConfig } = useTheme();
const { triggerCompletionCelebration } = useThemeAnimation();

// --- Layout ---
const listLayoutClass = computed(() => {
  const pl = themeConfig.value.pageLayout || {};
  const layout = pl.habitList || 'list';
  const density = pl.density || 'normal';

  if (layout === 'grid-2') {
    if (density === 'spacious') return 'grid grid-cols-2 gap-4';
    if (density === 'compact') return 'grid grid-cols-2 gap-2';
    return 'grid grid-cols-2 gap-3';
  }
  if (density === 'spacious') return 'space-y-4';
  if (density === 'compact') return 'space-y-2';
  return 'space-y-3';
});

// --- Card refs for celebration positioning ---
const cardRefs = {};
function setCardRef(habitId, componentInstance) {
  if (componentInstance) {
    cardRefs[habitId] = componentInstance;
  }
}

// --- Loading / undo state ---
const loadingId = ref(null);
const undoVisible = ref(false);
const undoMessage = ref("");
const undoHabitId = ref(null);
const undoTimer = ref(null);

onUnmounted(() => {
  if (undoTimer.value) clearTimeout(undoTimer.value);
});

function completeHabit(habitId) {
  loadingId.value = habitId;
  router.post(`/habits/${habitId}/complete/`, {}, {
    preserveScroll: true,
    onSuccess: (page) => {
      const flash = page.props.completionFlash;

      // Trigger theme-specific celebration animation on the card
      const cardComponent = cardRefs[habitId];
      if (cardComponent?.cardRef) {
        triggerCompletionCelebration(cardComponent.cardRef);
      }

      showUndo(habitId, flash?.text || "Habit completed");
    },
    onFinish: () => {
      loadingId.value = null;
    },
  });
}

function revertHabit(habitId) {
  loadingId.value = habitId;
  hideUndo();
  router.post(`/habits/${habitId}/revert/`, {}, {
    preserveScroll: true,
    onFinish: () => {
      loadingId.value = null;
    },
  });
}

function showUndo(habitId, message) {
  hideUndo();
  undoHabitId.value = habitId;
  undoMessage.value = message;
  undoVisible.value = true;
  undoTimer.value = setTimeout(() => {
    undoVisible.value = false;
  }, 5000);
}

function hideUndo() {
  if (undoTimer.value) clearTimeout(undoTimer.value);
  undoVisible.value = false;
}

function handleUndo() {
  if (undoHabitId.value) {
    revertHabit(undoHabitId.value);
  }
}
</script>
