<template>
  <div class="px-4 pt-6 pb-8 max-w-3xl mx-auto">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-text-primary mb-1">Appearance</h1>
      <p class="text-sm text-text-secondary">Choose a design template for your interface.</p>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <button
        v-for="(theme, id, idx) in themes"
        :key="id"
        @click="selectTheme(id)"
        :disabled="saving === id"
        :style="getCardEntranceStyle(idx)"
        class="relative text-left rounded-2xl overflow-hidden transition-all duration-200 focus:outline-none disabled:opacity-60"
        :class="[
          activeId === id
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
              border: hasBorder(id) ? `1px solid ${theme.cssVars['--color-border']}` : 'none',
              backdropFilter: isGlass(id) ? 'blur(8px)' : 'none',
            }"
          >
            <div class="flex items-center justify-between">
              <!-- Mock habit name lines -->
              <div class="flex flex-col gap-1 flex-1 mr-2">
                <div class="h-1.5 rounded-full w-16" :style="{ background: theme.cssVars['--color-text-primary'], opacity: 0.8 }" />
                <div class="h-1 rounded-full w-10" :style="{ background: theme.cssVars['--color-text-secondary'], opacity: 0.5 }" />
              </div>
              <!-- Mock interaction indicator -->
              <div v-if="interactionIcon(id) === 'button'" class="h-5 w-10 text-center flex items-center justify-center"
                :style="{
                  background: theme.cssVars['--color-accent'],
                  borderRadius: buttonRadius(id),
                  opacity: 0.95,
                }"
              >
                <span class="text-white text-[8px] font-bold leading-none">Done</span>
              </div>
              <div v-else-if="interactionIcon(id) === 'checkbox'" class="w-5 h-5 rounded border-2 flex items-center justify-center"
                :style="{ borderColor: theme.cssVars['--color-accent'], background: theme.cssVars['--color-accent'] }"
              >
                <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div v-else-if="interactionIcon(id) === 'toggle'" class="w-9 h-5 rounded-full flex items-center px-0.5"
                :style="{ background: theme.cssVars['--color-accent'] }"
              >
                <div class="w-4 h-4 rounded-full bg-white ml-auto" />
              </div>
              <div v-else class="h-5 flex items-center gap-0.5">
                <svg class="w-4 h-4" :style="{ color: theme.cssVars['--color-accent'] }" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
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
          class="px-3 py-2.5"
          :style="{ background: previewFooterBg(id) }"
        >
          <div class="flex items-center gap-2 mb-1.5">
            <span class="text-base leading-none">{{ theme.icon }}</span>
            <div class="flex-1 min-w-0">
              <p
                class="text-xs font-semibold truncate"
                :style="{ color: theme.cssVars['--color-text-primary'] }"
              >
                {{ theme.name }}
              </p>
            </div>
          </div>

          <!-- Personality tags -->
          <div class="flex flex-wrap gap-1">
            <span
              v-for="tag in getPersonalityTags(id)"
              :key="tag"
              class="text-[9px] px-1.5 py-0.5 rounded-full font-medium"
              :style="{
                background: theme.cssVars['--color-accent'] + '20',
                color: theme.cssVars['--color-accent'],
              }"
            >
              {{ tag }}
            </span>
          </div>
        </div>

        <!-- Active indicator -->
        <div
          v-if="activeId === id"
          class="absolute top-2 right-2 w-5 h-5 rounded-full bg-accent flex items-center justify-center shadow-lg"
        >
          <span class="text-white text-[10px] font-bold leading-none">&#10003;</span>
        </div>

        <!-- Preview badge (shown when previewing a different theme) -->
        <div
          v-if="previewId && previewId === id && previewId !== savedTheme"
          class="absolute top-2 left-2 px-2 py-0.5 rounded-full text-[9px] font-bold shadow-lg"
          :style="{
            background: theme.cssVars['--color-accent'],
            color: '#fff',
          }"
        >
          Preview
        </div>

        <!-- Saving spinner -->
        <div
          v-if="saving === id"
          class="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-sm"
        >
          <div class="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </button>
    </div>

    <p class="mt-6 text-xs text-text-secondary text-center">
      Tap a theme to preview. Your choice is saved automatically.
    </p>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from "vue";
import { router } from "@inertiajs/vue3";
import { themes, getTheme } from "../themes/index.js";
import { useTheme } from "../composables/useTheme.js";
import { useThemeAnimation } from "../composables/useThemeAnimation.js";

const props = defineProps({
  currentTheme: { type: String, default: "clean_modern" },
});

const { applyTheme } = useTheme();
const { getCardEntranceStyle } = useThemeAnimation();

const saving = ref(null);
const previewId = ref(null);
const savedTheme = ref(props.currentTheme);
const saveTimer = ref(null);

// The visually active theme (preview or saved)
const activeId = computed(() => previewId.value || savedTheme.value);

onUnmounted(() => {
  if (saveTimer.value) clearTimeout(saveTimer.value);
  // Revert to saved theme if leaving page during preview
  if (previewId.value && previewId.value !== savedTheme.value) {
    applyTheme(savedTheme.value);
  }
});

function selectTheme(id) {
  if (saving.value) return;

  // Tapping the already-saved theme — just clear preview
  if (id === savedTheme.value) {
    if (previewId.value) {
      previewId.value = null;
      applyTheme(savedTheme.value);
    }
    return;
  }

  // Apply live preview immediately
  previewId.value = id;
  applyTheme(id);

  // Debounce save — 600ms after last tap
  if (saveTimer.value) clearTimeout(saveTimer.value);
  saveTimer.value = setTimeout(() => {
    persistTheme(id);
  }, 600);
}

function persistTheme(id) {
  saving.value = id;

  router.post(
    "/theme/save/",
    { theme: id },
    {
      preserveState: true,
      preserveScroll: true,
      onSuccess: () => {
        savedTheme.value = id;
        previewId.value = null;
      },
      onError: (errors) => {
        console.error("Theme save failed:", errors);
        // Revert to saved theme on error
        previewId.value = null;
        applyTheme(savedTheme.value);
      },
      onFinish: () => {
        saving.value = null;
      },
    }
  );
}

// --- Preview helpers ---

function interactionIcon(id) {
  const config = getTheme(id);
  const type = config.interactions?.habitComplete || 'button-right';
  if (type === 'checkbox') return 'checkbox';
  if (type === 'toggle') return 'toggle';
  if (type === 'swipe-reveal') return 'swipe';
  return 'button';
}

function buttonRadius(id) {
  const t = themes[id];
  const r = t.classes.button.rounded;
  if (r === 'rounded-full') return '9999px';
  if (r === 'rounded-none') return '0';
  return '6px';
}

function previewBgStyle(id) {
  const t = themes[id];
  return { background: t.cssVars["--color-bg-primary"], minHeight: "6rem" };
}

function previewFooterBg(id) {
  return themes[id].cssVars["--color-bg-card"];
}

function isGlass(id) {
  return themes[id].classes.card.bg?.includes("backdrop-blur") || false;
}

function hasBorder(id) {
  const border = themes[id].classes.card.border;
  return border && border !== 'border-transparent' && border !== '';
}

function getPersonalityTags(id) {
  const config = getTheme(id);
  const tags = [];

  // Interaction type
  const interaction = config.interactions?.habitComplete || 'button-right';
  if (interaction === 'swipe-reveal') tags.push('Swipe');
  else if (interaction === 'checkbox') tags.push('Checkbox');
  else if (interaction === 'toggle') tags.push('Toggle');

  // Layout
  const layout = config.pageLayout?.habitList || 'list';
  if (layout === 'grid-2') tags.push('Grid');

  // Density
  const density = config.pageLayout?.density || 'normal';
  if (density === 'spacious') tags.push('Spacious');
  else if (density === 'compact') tags.push('Compact');

  // Animation highlights
  const anims = config.animations || {};
  if (anims.completionCelebration === 'burst-particles') tags.push('Particles');
  else if (anims.completionCelebration === 'fade-quiet') tags.push('Quiet');

  if (anims.cardEntrance === 'slide-up') tags.push('Slide');
  else if (anims.cardEntrance === 'stagger-fade') tags.push('Stagger');

  // Font (if custom)
  if (config.font?.import) tags.push('Custom font');

  return tags;
}
</script>
