<template>
  <div class="px-4 pt-6 pb-4 max-w-2xl mx-auto">
    <DashboardHeader :stats="stats" />

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

    <!-- Reward celebration overlay -->
    <RewardCelebration
      :visible="celebrationVisible"
      :reward-name="celebrationData.rewardName"
      :pieces-earned="celebrationData.piecesEarned"
      :pieces-required="celebrationData.piecesRequired"
      :card-rect="celebrationData.cardRect"
      @dismiss="celebrationVisible = false"
    />

    <!-- Undo toast -->
    <UndoToast
      :visible="undoVisible"
      :message="undoMessage"
      @undo="handleUndo"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onUnmounted, nextTick } from "vue";
import { router } from "@inertiajs/vue3";
import HabitCard from "../components/HabitCard.vue";
import DashboardHeader from "../components/DashboardHeader.vue";
import UndoToast from "../components/UndoToast.vue";
import RewardCelebration from "../components/rewards/RewardCelebration.vue";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";
import { useRealtimeSync } from "../composables/useRealtimeSync.js";

defineProps({
  habits: { type: Array, default: () => [] },
  stats: { type: Object, default: () => ({}) },
  completionFlash: { type: Object, default: null },
});

const { themeConfig } = useTheme();
const { triggerCompletionCelebration } = useThemeAnimation();

// Covers the ~600ms sink-bounce + popup-display window.
const REALTIME_PAUSE_DURATION_MS = 4000;

// Pause realtime sync during celebration to prevent router.reload() from
// resetting celebrationVisible before the user sees the reward popup.
const realtimePaused = ref(false);
let realtimePauseTimer = null;
useRealtimeSync({ paused: realtimePaused });

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

/** Resolve the card DOM node from a HabitCard component instance (exposed ref). */
function resolveCardElement(componentInstance) {
  if (!componentInstance) return null;
  const exposed = componentInstance.cardRef;
  if (!exposed) return null;
  if (exposed instanceof HTMLElement) return exposed;
  if (typeof exposed === "object" && "value" in exposed) {
    return exposed.value ?? null;
  }
  return null;
}

function setCardRef(habitId, componentInstance) {
  if (componentInstance) {
    cardRefs[habitId] = componentInstance;
  }
}

// --- Celebration state ---
const celebrationVisible = ref(false);
const celebrationData = reactive({
  rewardName: "",
  piecesEarned: null,
  piecesRequired: null,
  cardRect: null,
});

// --- Loading / undo state ---
const loadingId = ref(null);
const undoVisible = ref(false);
const undoMessage = ref("");
const undoHabitId = ref(null);
const undoTimer = ref(null);

onUnmounted(() => {
  if (undoTimer.value) clearTimeout(undoTimer.value);
  if (realtimePauseTimer) clearTimeout(realtimePauseTimer);
});

function completeHabit(habitId) {
  loadingId.value = habitId;

  // Pause WebSocket reloads so the celebration popup isn't wiped out
  realtimePaused.value = true;
  if (realtimePauseTimer) clearTimeout(realtimePauseTimer);
  realtimePauseTimer = setTimeout(() => {
    realtimePaused.value = false;
    realtimePauseTimer = null;
  }, REALTIME_PAUSE_DURATION_MS);

  // Capture old position BEFORE the server response repositions the card.
  const preCardComponent = cardRefs[habitId];
  const preCardEl = resolveCardElement(preCardComponent);
  const oldRect = preCardEl?.getBoundingClientRect?.() ?? null;

  router.post(`/habits/${habitId}/complete/`, {}, {
    preserveScroll: true,
    onSuccess: async (page) => {
      const flash = page.props.completionFlash;

      // Wait for Inertia's new habits prop to be applied so the card sits in
      // its new (bottom) DOM slot. Same :key keeps the same node — preCardEl
      // is still valid for the FLIP delta.
      await nextTick();

      // Re-resolve the card component in case its mount/unmount churned during
      // the Inertia re-render; fall back to the pre-post element we captured
      // for the FLIP delta. Same :key normally keeps the DOM node stable.
      const cardComponent = cardRefs[habitId];
      const cardEl = resolveCardElement(cardComponent) ?? preCardEl;
      const gotReward = !!(flash?.got_reward && flash?.reward_name);

      try {
        await triggerCompletionCelebration(cardEl, { oldRect, gotReward });
      } catch (err) {
        // Universal fallback — inner animations swallow their own failures;
        // this guards against any new rejection path. Surface in dev.
        if (import.meta.env.DEV) console.warn('Completion animation failed:', err);
      }

      if (gotReward) {
        celebrationData.rewardName = flash.reward_name;
        celebrationData.piecesEarned = flash.pieces_earned ?? null;
        celebrationData.piecesRequired = flash.pieces_required ?? null;
        celebrationData.cardRect = cardEl?.getBoundingClientRect?.() ?? null;
        celebrationVisible.value = true;
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
