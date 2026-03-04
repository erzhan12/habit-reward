/**
 * Theme interaction resolver.
 *
 * Reads `themeConfig.interactions.habitComplete` and resolves it to
 * a component reference + props for the HabitCard dynamic slot.
 */

import { computed } from "vue";
import { useTheme } from "./useTheme.js";
import HabitDoneButton from "../components/interactions/HabitDoneButton.vue";
import HabitDoneCheckbox from "../components/interactions/HabitDoneCheckbox.vue";
import HabitDoneToggle from "../components/interactions/HabitDoneToggle.vue";
import HabitDoneSwipe from "../components/interactions/HabitDoneSwipe.vue";

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

  const interactionComponent = computed(() => {
    switch (interactionType.value) {
      case "checkbox":
        return HabitDoneCheckbox;
      case "swipe-reveal":
        return HabitDoneSwipe;
      case "toggle":
        return HabitDoneToggle;
      default:
        return HabitDoneButton;
    }
  });

  const interactionProps = computed(() => {
    switch (interactionType.value) {
      case "checkbox":
        return { position: "left" };
      case "toggle":
        return { position: "right" };
      default:
        return { position: "right" };
    }
  });

  // Swipe wraps the entire card — the layout must be different
  const isSwipeMode = computed(() => interactionType.value === "swipe-reveal");

  return { interactionType, interactionComponent, interactionProps, isSwipeMode };
}
