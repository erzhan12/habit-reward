/**
 * Theme animation composable.
 *
 * Provides helpers for theme-driven animations:
 * - Card entrance styles
 * - Streak fire CSS classes
 * - Hover micro-interaction CSS classes
 * - Global sink-bounce completion animation with conditional particle burst
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
 * FLIP-based sink-bounce animation. Translates the card from its old position
 * to its new (post-rerender) resting slot with an overshoot-settle curve.
 *
 * @param {HTMLElement} cardEl
 * @param {DOMRect|null} oldRect
 * @returns {Promise<void>}
 */
export function animateSinkBounce(cardEl, oldRect) {
  if (!cardEl) return Promise.resolve();
  if (typeof cardEl.animate !== 'function') return Promise.resolve();
  try {
    const newRect = cardEl.getBoundingClientRect();
    const deltaX = oldRect ? oldRect.left - newRect.left : 0;
    const deltaY = oldRect ? oldRect.top - newRect.top : 0;
    const anim = cardEl.animate(
      [
        { transform: `translate(${deltaX}px, ${deltaY}px)` },
        { transform: 'translate(0, 20px)', offset: 0.55 },
        { transform: 'translate(0, -4px)', offset: 0.8 },
        { transform: 'translate(0, 0)' },
      ],
      { duration: 600, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)', fill: 'both' }
    );
    return anim.finished
      .catch(() => undefined)
      .finally(() => anim.cancel?.());
  } catch {
    return Promise.resolve();
  }
}

/**
 * Spawn a burst of particles from the card's center.
 *
 * @param {HTMLElement} el
 * @returns {Promise<void>}
 */
export async function animateBurstParticles(el) {
  try {
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
  } catch {
    // Particles are optional flair — never let their failure abort the
    // sink-bounce wait in Promise.all (which would cause the reward popup
    // to open mid-animation in Dashboard.vue).
  }
}

/**
 * Global completion celebration: sink-bounce, plus parallel particle burst on reward.
 * Reduced-motion gating is applied once at entry.
 *
 * @param {HTMLElement} cardEl
 * @param {{ oldRect?: DOMRect|null, gotReward?: boolean }} opts
 * @returns {Promise<void>}
 */
export function triggerCompletionCelebration(cardEl, opts = {}) {
  const { oldRect = null, gotReward = false } = opts;
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    return Promise.resolve();
  }
  const tasks = [animateSinkBounce(cardEl, oldRect)];
  if (gotReward) tasks.push(animateBurstParticles(cardEl));
  return Promise.all(tasks).then(() => undefined);
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
     * Delegates to the standalone named export — behavior is now global.
     * @param {HTMLElement} cardEl
     * @param {{ oldRect?: DOMRect|null, gotReward?: boolean }} opts
     * @returns {Promise<void>}
     */
    triggerCompletionCelebration,
  };
}
