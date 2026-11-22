<template>
  <!-- Mobile top bar: app name + logout (the bottom nav has no room for it) -->
  <header
    class="lg:hidden flex items-center justify-between px-4 py-2 border-b"
    :class="headerClass"
  >
    <span class="text-base font-bold text-accent">Habit Reward</span>
    <button
      type="button"
      aria-label="Log out of your account"
      :aria-busy="busy"
      :disabled="busy"
      class="flex items-center gap-2 px-3 min-h-11 rounded-lg text-sm font-medium transition-colors duration-150 text-text-secondary hover:text-text-primary hover:bg-bg-card-hover disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
      @click="$emit('logout')"
    >
      <span aria-hidden="true">↩</span>
      {{ label }}
    </button>
  </header>
</template>

<script setup>
// Layout owns the logout request and its state; this bar only renders it.
defineProps({
  headerClass: { type: String, default: "" },
  label: { type: String, default: "Logout" },
  busy: { type: Boolean, default: false },
});

defineEmits(["logout"]);
</script>
