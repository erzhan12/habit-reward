<template>
  <div class="min-h-screen bg-bg-primary flex flex-col lg:flex-row">
    <!-- Desktop sidebar -->
    <aside class="hidden lg:flex lg:flex-col lg:w-56 lg:fixed lg:inset-y-0 bg-bg-card border-r border-gray-800">
      <div class="p-6">
        <h1 class="text-xl font-bold text-accent">Habit Reward</h1>
      </div>
      <nav class="flex-1 px-3 space-y-1">
        <Link
          v-for="item in navItems"
          :key="item.href"
          :href="item.href"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
          :class="isActive(item.href)
            ? 'bg-accent/10 text-accent'
            : 'text-text-secondary hover:text-text-primary hover:bg-bg-card-hover'"
        >
          <span class="text-lg">{{ item.icon }}</span>
          {{ item.label }}
        </Link>
      </nav>
      <div class="p-3 border-t border-gray-800">
        <button
          @click="handleLogout"
          :disabled="isLoggingOut"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium w-full text-text-secondary hover:text-text-primary hover:bg-bg-card-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Log out of your account"
        >
          <span class="text-lg" aria-hidden="true">&#x1F6AA;</span>
          {{ isLoggingOut ? 'Logging out...' : 'Logout' }}
        </button>
        <p v-if="logoutError" class="px-3 mt-1 text-xs text-red-400">{{ logoutError }}</p>
      </div>
    </aside>

    <!-- Flash messages -->
    <FlashMessages :messages="flash" />

    <!-- Main content -->
    <main class="flex-1 lg:ml-56 pb-20 lg:pb-6">
      <slot />
    </main>

    <!-- Mobile bottom nav -->
    <BottomNav :items="navItems" class="lg:hidden" />
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Link, router, usePage } from "@inertiajs/vue3";
import BottomNav from "./BottomNav.vue";
import FlashMessages from "./FlashMessages.vue";

const page = usePage();
const flash = computed(() => page.props.flash || []);

const navItems = [
  { href: "/", icon: "\u2714", label: "Today" },
  { href: "/streaks/", icon: "\uD83D\uDD25", label: "Streaks" },
  { href: "/history/", icon: "\uD83D\uDCC5", label: "History" },
  { href: "/rewards/", icon: "\uD83C\uDF81", label: "Rewards" },
];

const isLoggingOut = ref(false);
const logoutError = ref(null);

async function handleLogout() {
  if (isLoggingOut.value) return;
  isLoggingOut.value = true;
  logoutError.value = null;
  try {
    await router.post("/auth/logout/");
  } catch (error) {
    console.error("Logout failed:", error);
    logoutError.value = "Logout failed. Please try again.";
  } finally {
    isLoggingOut.value = false;
  }
}

function isActive(href) {
  const url = usePage().url;
  if (href === "/") return url === "/";
  return url.startsWith(href);
}
</script>
