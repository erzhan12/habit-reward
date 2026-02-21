<template>
  <div class="px-4 pt-6 pb-4 max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-text-primary mb-6">Rewards</h1>

    <!-- Active rewards -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
      <RewardCard
        v-for="reward in rewards"
        :key="reward.id"
        :reward="reward"
        :loading="loadingId === reward.id"
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
          v-for="reward in claimedRewards"
          :key="reward.id"
          class="bg-bg-card rounded-lg px-4 py-3 flex items-center gap-3"
        >
          <span class="text-accent">&#10003;</span>
          <span class="text-sm text-text-secondary">{{ reward.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { router } from "@inertiajs/vue3";
import RewardCard from "../components/RewardCard.vue";

defineProps({
  rewards: { type: Array, default: () => [] },
  claimedRewards: { type: Array, default: () => [] },
});

const loadingId = ref(null);
const showClaimed = ref(false);

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
