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
import { computed } from "vue";
import { Link, usePage } from "@inertiajs/vue3";
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

function isActive(href) {
  const url = usePage().url;
  if (href === "/") return url === "/";
  return url.startsWith(href);
}
</script>
