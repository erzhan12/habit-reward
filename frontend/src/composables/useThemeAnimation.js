/**
 * Theme animation composable (Phase 1 infrastructure).
 *
 * Provides helpers to apply theme-driven animations:
 * - Card entrance styles (inline style objects)
 * - Streak fire CSS classes
 * - Hover micro-interaction CSS classes
 * - Completion celebration triggers
 */

import { computed } from "vue";
import { useTheme } from "./useTheme.js";

/**
 * Returns an inline style object for card entrance animation.
 *
 * @param {number} index - Card index in the list (for stagger delay)
 * @param {string} type - Animation type from theme config
 * @returns {object} CSS style object
 */
export function cardEntranceStyle(index, type) {
  switch (type) {
    case 'fade-in':
      return {
        animation: 'fadeIn 0.3s ease-out both',
      };
    case 'slide-up':
      return {
        animation: 'slideUp 0.35s ease-out both',
      };
    case 'stagger-fade':
      return {
        animation: 'fadeIn 0.3s ease-out both',
        animationDelay: `${index * 60}ms`,
      };
    default: // 'none'
      return {};
  }
}

/**
 * Returns a CSS class name for streak fire animation.
 *
 * @param {number} streakCount - Current streak count
 * @param {string} type - Animation type from theme config
 * @returns {string} CSS class name or empty string
 */
export function streakFireClass(streakCount, type) {
  if (!streakCount || streakCount <= 0) return '';
  switch (type) {
    case 'pulse-glow':
      return 'streak-fire-pulse-glow';
    case 'flicker-flame':
      return 'streak-fire-flicker-flame';
    case 'bounce':
      return 'streak-fire-bounce';
    default:
      return '';
  }
}

/**
 * Returns a CSS class name for hover micro-interaction.
 *
 * @param {string} type - Animation type from theme config
 * @returns {string} CSS class name or empty string
 */
export function hoverMicroClass(type) {
  switch (type) {
    case 'scale':
      return 'hover-micro-scale';
    case 'shadow-lift':
      return 'hover-micro-shadow-lift';
    case 'glow-border':
      return 'hover-micro-glow-border';
    default:
      return '';
  }
}

/**
 * Composable providing reactive animation helpers tied to current theme.
 */
export function useThemeAnimation() {
  const { themeConfig } = useTheme();

  const animations = computed(() => themeConfig.value.animations || {});

  const hoverClass = computed(() =>
    hoverMicroClass(animations.value.hoverMicro)
  );

  return {
    /**
     * Get inline style for card entrance animation.
     * @param {number} index
     * @returns {object}
     */
    getCardEntranceStyle(index) {
      return cardEntranceStyle(index, animations.value.cardEntrance);
    },

    /**
     * Get CSS class for streak fire.
     * @param {number} streakCount
     * @returns {string}
     */
    getStreakFireClass(streakCount) {
      return streakFireClass(streakCount, animations.value.streakFire);
    },

    /** Reactive hover micro-interaction class. */
    hoverClass,

    /**
     * Trigger a completion celebration animation on an element.
     * @param {HTMLElement} cardEl
     * @returns {Promise<void>}
     */
    async triggerCompletionCelebration(cardEl) {
      const type = animations.value.completionCelebration;
      switch (type) {
        case 'scale-up':
          await animateScaleUp(cardEl);
          break;
        case 'burst-particles':
          await animateBurstParticles(cardEl);
          break;
        case 'fade-quiet':
          await animateFadeQuiet(cardEl);
          break;
        default:
          break;
      }
    },
  };
}

// ── Internal animation handlers ─────────────────────────────────────

async function animateScaleUp(el) {
  if (!el) return;
  el.style.transition = 'transform 0.2s ease-out';
  el.style.transform = 'scale(1.03)';
  await sleep(200);
  el.style.transform = 'scale(1)';
  await sleep(200);
  el.style.transition = '';
  el.style.transform = '';
}

async function animateBurstParticles(el) {
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const { spawnParticles } = await import('../utils/particles.js');
  await spawnParticles({
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
    count: 12,
    colors: ['#06b6d4', '#ec4899', '#fbbf24', '#10b981'],
    duration: 600,
  });
}

async function animateFadeQuiet(el) {
  if (!el) return;
  el.style.transition = 'opacity 0.3s ease-out';
  el.style.opacity = '0.5';
  await sleep(300);
  el.style.opacity = '1';
  await sleep(300);
  el.style.transition = '';
  el.style.opacity = '';
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
