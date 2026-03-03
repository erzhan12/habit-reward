<template>
  <div class="px-4 pt-6 pb-8 max-w-3xl mx-auto">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-text-primary mb-1">Appearance</h1>
      <p class="text-sm text-text-secondary">Choose a design template for your interface.</p>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <button
        v-for="(theme, id) in themes"
        :key="id"
        @click="selectTheme(id)"
        :disabled="saving === id"
        class="relative text-left rounded-2xl overflow-hidden transition-all duration-200 focus:outline-none disabled:opacity-60"
        :class="[
          currentTheme === id
            ? 'ring-2 ring-accent scale-[1.02]'
            : 'hover:scale-[1.01] hover:shadow-lg opacity-90 hover:opacity-100',
        ]"
      >
        <!-- Mini preview rendered with each theme's own palette -->
        <div
          class="h-36 p-3 flex flex-col gap-2"
          :style="previewBgStyle(id)"
        >
          <!-- Mock nav bar -->
          <div
            class="h-2.5 rounded-full w-16 mb-1"
            :style="{ background: theme.cssVars['--color-accent'], opacity: 0.9 }"
          />

          <!-- Mock habit card -->
          <div
            class="flex-1 rounded-lg p-2 flex flex-col justify-between"
            :style="{
              background: theme.cssVars['--color-bg-card'],
              border: id === 'minimal_ink' ? '0 0 1px 0 solid #e5e7eb' : 'none',
              backdropFilter: isGlass(id) ? 'blur(8px)' : 'none',
            }"
          >
            <div class="flex items-center justify-between">
              <!-- Mock habit name lines -->
              <div class="flex flex-col gap-1 flex-1 mr-2">
                <div class="h-1.5 rounded-full w-16" :style="{ background: theme.cssVars['--color-text-primary'], opacity: 0.8 }" />
                <div class="h-1 rounded-full w-10" :style="{ background: theme.cssVars['--color-text-secondary'], opacity: 0.5 }" />
              </div>
              <!-- Mock Done button -->
              <div
                class="h-5 w-10 text-center flex items-center justify-center"
                :style="{
                  background: theme.cssVars['--color-accent'],
                  borderRadius: theme.classes.button.rounded === 'rounded-full' ? '9999px' : theme.classes.button.rounded === 'rounded-none' ? '0' : '6px',
                  opacity: 0.95,
                }"
              >
                <span class="text-white text-[8px] font-bold leading-none">Done</span>
              </div>
            </div>

            <!-- Mock streak indicator -->
            <div class="flex items-center gap-1 mt-1">
              <div class="w-1.5 h-1.5 rounded-full" :style="{ background: theme.cssVars['--color-streak-fire'] }" />
              <div class="h-1 rounded-full w-8" :style="{ background: theme.cssVars['--color-streak-fire'], opacity: 0.6 }" />
            </div>
          </div>
        </div>

        <!-- Theme label footer -->
        <div
          class="px-3 py-2.5 flex items-center gap-2"
          :style="{ background: previewFooterBg(id) }"
        >
          <span class="text-base leading-none">{{ theme.icon }}</span>
          <div class="flex-1 min-w-0">
            <p
              class="text-xs font-semibold truncate"
              :style="{ color: theme.cssVars['--color-text-primary'] }"
            >
              {{ theme.name }}
            </p>
            <p
              class="text-[10px] truncate mt-0.5"
              :style="{ color: theme.cssVars['--color-text-secondary'] }"
            >
              {{ theme.description }}
            </p>
          </div>
        </div>

        <!-- Active indicator -->
        <div
          v-if="currentTheme === id"
          class="absolute top-2 right-2 w-5 h-5 rounded-full bg-accent flex items-center justify-center shadow-lg"
        >
          <span class="text-white text-[10px] font-bold leading-none">✓</span>
        </div>

        <!-- Saving spinner -->
        <div
          v-if="saving === id"
          class="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-sm"
        >
          <div class="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin no-theme-transition" />
        </div>
      </button>
    </div>

    <p class="mt-6 text-xs text-text-secondary text-center">
      Your choice is saved automatically and synced across devices.
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { router } from "@inertiajs/vue3";
import { themes } from "../themes/index.js";

const props = defineProps({
  currentTheme: { type: String, default: "dark_emerald" },
});

const saving = ref(null);

function selectTheme(id) {
  if (id === props.currentTheme || saving.value) return;
  saving.value = id;

  router.post(
    "/theme/save/",
    { theme: id },
    {
      onFinish: () => {
        saving.value = null;
      },
    }
  );
}

function previewBgStyle(id) {
  const t = themes[id];
  const bg = t.cssVars["--color-bg-primary"];
  return { background: bg, minHeight: "6rem" };
}

function previewFooterBg(id) {
  const t = themes[id];
  const raw = t.cssVars["--color-bg-card"];
  if (raw.startsWith("rgba")) return raw;
  return raw;
}

function isGlass(id) {
  return id === "ios_glass" || id === "ocean_gradient";
}
</script>
