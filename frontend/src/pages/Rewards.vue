<template>
  <div class="px-4 pt-6 pb-4 max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-text-primary mb-6">Rewards</h1>

    <!-- Active rewards -->
    <div :class="rewardLayoutClass" class="mb-8">
      <RewardCard
        v-for="(reward, idx) in rewards"
        :key="reward.id"
        :reward="reward"
        :loading="loadingId === reward.id"
        :style="getCardEntranceStyle(idx)"
        @claim="claimReward"
      />

      <div v-if="rewards.length === 0" class="col-span-full text-center py-12">
        <p class="text-text-secondary">No active rewards. Add some via the Telegram bot.</p>
      </div>
    </div>

    <!-- Claimed one-time rewards -->
    <div v-if="claimedRewards.length > 0">
      <button
        @click="showClaimed = !showClaimed"
        class="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors mb-3"
      >
        <span :class="showClaimed ? 'rotate-90' : ''" class="transition-transform">&#9654;</span>
        Claimed rewards ({{ claimedRewards.length }})
      </button>

      <div v-if="showClaimed" class="space-y-2">
        <div
          v-for="(reward, idx) in claimedRewards"
          :key="reward.id"
          class="px-4 py-3 flex items-center gap-3"
          :class="[tc.card.rounded, tc.card.bg, tc.card.border, tc.card.extra]"
          :style="getCardEntranceStyle(idx)"
        >
          <span class="text-accent">&#10003;</span>
          <span class="text-sm text-text-secondary">{{ reward.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { router } from "@inertiajs/vue3";
import RewardCard from "../components/RewardCard.vue";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";

defineProps({
  rewards: { type: Array, default: () => [] },
  claimedRewards: { type: Array, default: () => [] },
});

const loadingId = ref(null);
const showClaimed = ref(false);

const { themeConfig } = useTheme();
const tc = computed(() => themeConfig.value.classes);
const { getCardEntranceStyle } = useThemeAnimation();

// --- Layout ---
const rewardLayoutClass = computed(() => {
  const pl = themeConfig.value.pageLayout || {};
  const layout = pl.rewardList || 'list';
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

function claimReward(rewardId) {
  loadingId.value = rewardId;
  router.post(`/rewards/${rewardId}/claim/`, {}, {
    preserveScroll: true,
    onFinish: () => {
      loadingId.value = null;
    },
  });
}
</script>
