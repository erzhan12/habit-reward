<template>
  <nav class="fixed bottom-0 inset-x-0 border-t z-50 safe-area-bottom" :class="navClass">
    <div class="flex justify-around py-2">
      <Link
        v-for="item in items"
        :key="item.href"
        :href="item.href"
        class="flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all min-w-[60px]"
        :class="itemClass(item.href)"
      >
        <span class="text-xl">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </Link>
    </div>
  </nav>
</template>

<script setup>
import { computed } from "vue";
import { Link, usePage } from "@inertiajs/vue3";

const props = defineProps({
  items: { type: Array, required: true },
  navStyle: { type: String, default: "default" },
});

function isActive(href) {
  const url = usePage().url;
  if (href === "/") return url === "/";
  return url.startsWith(href);
}

const navClass = computed(() => {
  if (props.navStyle === "frosted") {
    return "bg-bg-card/70 backdrop-blur-xl border-white/10";
  }
  return "bg-bg-card border-gray-800";
});

function itemClass(href) {
  const active = isActive(href);
  if (props.navStyle === "underline") {
    return active
      ? "text-accent border-t-2 border-accent rounded-none pt-0.5 -mt-0.5"
      : "text-text-secondary";
  }
  if (props.navStyle === "frosted") {
    return active ? "text-accent bg-accent/10 backdrop-blur-sm" : "text-text-secondary";
  }
  if (props.navStyle === "glow") {
    return active
      ? "text-accent bg-accent/15 shadow-sm shadow-accent/20"
      : "text-text-secondary";
  }
  return active ? "text-accent" : "text-text-secondary";
}
</script>

<style scoped>
.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
</style>
