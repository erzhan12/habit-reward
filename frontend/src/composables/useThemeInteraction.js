/**
 * Theme interaction resolver (Phase 1 infrastructure).
 *
 * Reads `themeConfig.interactions.habitComplete` and resolves it to
 * a component reference + props. In Phase 1, all interaction types
 * map to HabitDoneButton.vue.
 */

import { computed } from "vue";
import { useTheme } from "./useTheme.js";
import HabitDoneButton from "../components/interactions/HabitDoneButton.vue";

/**
 * Detect coarse-pointer (touch) device.
 * @returns {boolean}
 */
function isTouchDevice() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(pointer: coarse)").matches;
}

/**
 * Composable returning the resolved interaction component and config.
 *
 * @returns {{ interactionType: import('vue').ComputedRef<string>,
 *             interactionComponent: import('vue').ComputedRef<object>,
 *             interactionProps: import('vue').ComputedRef<object> }}
 */
export function useThemeInteraction() {
  const { themeConfig } = useTheme();

  const interactionType = computed(() => {
    const configured = themeConfig.value.interactions?.habitComplete || "button-right";
    // Swipe falls back to button on non-touch devices
    if (configured === "swipe-reveal" && !isTouchDevice()) {
      return "button-right";
    }
    return configured;
  });

  // Phase 1: all types resolve to HabitDoneButton
  const interactionComponent = computed(() => HabitDoneButton);

  const interactionProps = computed(() => ({
    position: interactionType.value === "checkbox" ? "left" : "right",
  }));

  return { interactionType, interactionComponent, interactionProps };
}
