<template>
  <!-- Top-bar layout (e.g. Ocean Gradient theme) -->
  <div v-if="themeConfig.layout === 'topbar'" class="min-h-screen bg-bg-primary flex flex-col">
    <!-- Desktop top navbar -->
    <header
      class="hidden lg:flex items-center gap-6 px-6 py-3 border-b"
      :class="topbarHeaderClass"
    >
      <h1 class="text-lg font-bold text-accent mr-4 shrink-0">Habit Reward</h1>
      <nav class="flex items-center gap-1 flex-1">
        <Link
          v-for="item in navItems"
          :key="item.href"
          :href="item.href"
          class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors duration-150"
          :class="topbarNavItemClass(item.href)"
        >
          <span>{{ item.icon }}</span>
          {{ item.label }}
        </Link>
      </nav>
      <!-- Desktop logout -->
      <button
        type="button"
        aria-label="Log out of your account"
        :aria-busy="isLoggingOut"
        :disabled="isLoggingOut"
        class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors duration-150 text-text-secondary hover:text-text-primary hover:bg-bg-card-hover shrink-0 disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
        @click="logout"
      >
        <span aria-hidden="true">↩</span>
        {{ logoutLabel }}
      </button>
    </header>

    <MobileTopBar :header-class="sidebarClass" :label="logoutLabel" :busy="isLoggingOut" @logout="logout" />

    <!-- Flash messages -->
    <FlashMessages :messages="flash" />

    <!-- Main content -->
    <main class="flex-1 pb-20 lg:pb-6">
      <slot />
    </main>

    <!-- Mobile bottom nav -->
    <BottomNav :items="navItems" :navStyle="themeConfig.navStyle" class="lg:hidden" />
  </div>

  <!-- Sidebar layout (default) -->
  <div v-else class="min-h-screen bg-bg-primary flex flex-col lg:flex-row">
    <!-- Desktop sidebar -->
    <aside
      class="hidden lg:flex lg:flex-col lg:w-56 lg:fixed lg:inset-y-0 border-r"
      :class="sidebarClass"
    >
      <div class="p-6">
        <h1 class="text-xl font-bold text-accent">Habit Reward</h1>
      </div>
      <nav class="flex-1 px-3 space-y-1">
        <Link
          v-for="item in navItems"
          :key="item.href"
          :href="item.href"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150"
          :class="sidebarNavItemClass(item.href)"
        >
          <span class="text-lg" :class="sidebarIconClass(item.href)">{{ item.icon }}</span>
          {{ item.label }}
        </Link>
      </nav>
      <!-- Sidebar logout at bottom -->
      <div class="px-3 pb-4">
        <button
          type="button"
          aria-label="Log out of your account"
          :aria-busy="isLoggingOut"
          :disabled="isLoggingOut"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 w-full text-text-secondary hover:text-text-primary hover:bg-bg-card-hover disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
          @click="logout"
        >
          <span class="text-lg" aria-hidden="true">↩</span>
          {{ logoutLabel }}
        </button>
      </div>
    </aside>

    <MobileTopBar :header-class="sidebarClass" :label="logoutLabel" :busy="isLoggingOut" @logout="logout" />

    <!-- Flash messages -->
    <FlashMessages :messages="flash" />

    <!-- Main content -->
    <main class="flex-1 lg:ml-56 pb-20 lg:pb-6">
      <slot />
    </main>

    <!-- Mobile bottom nav -->
    <BottomNav :items="navItems" :navStyle="themeConfig.navStyle" class="lg:hidden" />
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Link, router, usePage } from "@inertiajs/vue3";
import BottomNav from "./BottomNav.vue";
import FlashMessages from "./FlashMessages.vue";
import MobileTopBar from "./MobileTopBar.vue";
import { useTheme } from "../composables/useTheme.js";
import { useDayChange } from "../composables/useDayChange.js";

const page = usePage();

useDayChange();
const flash = computed(() => page.props.flash || []);

const { themeConfig } = useTheme();

// One logout handler for the sidebar, topbar and mobile buttons.
// router.post returns void: onStart/onFinish are the only reliable signals
// (onError fires for validation errors only, which logout never returns).
const isLoggingOut = ref(false);
const logoutLabel = computed(() => (isLoggingOut.value ? "Logging out…" : "Logout"));

function logout() {
  if (isLoggingOut.value) return;
  router.post("/auth/logout/", {}, {
    onStart: () => {
      isLoggingOut.value = true;
    },
    onFinish: () => {
      isLoggingOut.value = false;
    },
  });
}

const navItems = [
  { href: "/", icon: "✔", label: "Today" },
  { href: "/streaks/", icon: "🔥", label: "Streaks" },
  { href: "/history/", icon: "📅", label: "History" },
  { href: "/rewards/", icon: "🎁", label: "Rewards" },
  { href: "/analytics/", icon: "📊", label: "Analytics" },
  { href: "/theme/", icon: "🎨", label: "Theme" },
];

function isActive(href) {
  const url = usePage().url;
  if (href === "/") return url === "/";
  return url.startsWith(href);
}

// Sidebar styling
const sidebarClass = computed(() => {
  if (themeConfig.value.navStyle === "frosted") {
    return "bg-bg-card/70 backdrop-blur-xl border-white/10";
  }
  return "bg-bg-card border-border";
});

function sidebarIconClass(href) {
  // Today's ✔ icon uses the theme accent when inactive — signals "mark
  // complete" before the user navigates in, instead of inheriting muted gray.
  if (href === "/" && !isActive(href)) return "text-accent";
  return "";
}

function sidebarNavItemClass(href) {
  const active = isActive(href);
  const style = themeConfig.value.navStyle;

  if (style === "underline") {
    return active
      ? "text-accent border-b-2 border-accent rounded-none pb-2"
      : "text-text-secondary hover:text-text-primary hover:bg-bg-card-hover";
  }
  if (style === "frosted") {
    return active
      ? "bg-accent/15 text-accent backdrop-blur-sm"
      : "text-text-secondary hover:text-text-primary hover:bg-white/5";
  }
  if (style === "glow") {
    return active
      ? "bg-accent/15 text-accent shadow-sm shadow-accent/20"
      : "text-text-secondary hover:text-text-primary hover:bg-bg-card-hover";
  }
  // default
  return active
    ? "bg-accent/10 text-accent"
    : "text-text-secondary hover:text-text-primary hover:bg-bg-card-hover";
}

// Top-bar styling
const topbarHeaderClass = computed(() => {
  if (themeConfig.value.navStyle === "frosted") {
    return "bg-bg-card/60 backdrop-blur-xl border-white/10 sticky top-0 z-40";
  }
  return "bg-bg-card border-border";
});

function topbarNavItemClass(href) {
  const active = isActive(href);
  const style = themeConfig.value.navStyle;

  if (style === "underline") {
    return active
      ? "text-accent border-b-2 border-accent rounded-none"
      : "text-text-secondary hover:text-text-primary";
  }
  if (style === "frosted") {
    return active
      ? "bg-accent/15 text-accent"
      : "text-text-secondary hover:text-text-primary hover:bg-white/5";
  }
  return active
    ? "bg-accent/10 text-accent"
    : "text-text-secondary hover:text-text-primary hover:bg-bg-card-hover";
}
</script>
