<template>
  <nav class="fixed bottom-0 inset-x-0 bg-bg-card border-t border-gray-800 safe-area-bottom z-50">
    <div class="flex justify-around py-2">
      <Link
        v-for="item in items"
        :key="item.href"
        :href="item.href"
        class="flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors min-w-[60px]"
        :class="isActive(item.href)
          ? 'text-accent'
          : 'text-text-secondary'"
      >
        <span class="text-xl">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </Link>
    </div>
  </nav>
</template>

<script setup>
import { Link, usePage } from "@inertiajs/vue3";

defineProps({
  items: { type: Array, required: true },
});

function isActive(href) {
  const url = usePage().url;
  if (href === "/") return url === "/";
  return url.startsWith(href);
}
</script>

<style scoped>
.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
</style>
