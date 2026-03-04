import { computed, watch } from "vue";
import { usePage } from "@inertiajs/vue3";
import { getTheme, defaultTheme } from "../themes/index.js";
import { loadThemeFont } from "./useThemeFont.js";

/**
 * Reactive theme composable.
 *
 * Reads `page.props.userTheme` (shared by InertiaFlashMiddleware), looks up
 * the full theme config, applies CSS custom properties to <html>, sets the
 * `data-theme` attribute, and returns reactive helpers for components.
 *
 * Uses the View Transitions API when available for smooth theme switches.
 * Falls back to an opacity cross-fade for browsers without support.
 */
export function useTheme() {
  const page = usePage();

  const themeId = computed(() => page.props.userTheme || defaultTheme);
  const themeConfig = computed(() => getTheme(themeId.value));

  /**
   * Synchronously apply CSS vars and data-theme attribute.
   * Must be synchronous for View Transitions API callback.
   */
  function applyDomUpdates(id, config) {
    const root = document.documentElement;
    for (const [prop, value] of Object.entries(config.cssVars)) {
      root.style.setProperty(prop, value);
    }
    root.setAttribute("data-theme", id);
  }

  function applyTheme(id) {
    const config = getTheme(id);

    if (typeof document === "undefined") return;

    // Use View Transitions API for smooth theme switch
    if (document.startViewTransition) {
      document.startViewTransition(() => {
        applyDomUpdates(id, config);
      });
    } else {
      // Fallback: subtle opacity cross-fade
      const root = document.documentElement;
      root.style.transition = "opacity 0.15s ease-out";
      root.style.opacity = "0.95";
      requestAnimationFrame(() => {
        applyDomUpdates(id, config);
        requestAnimationFrame(() => {
          root.style.opacity = "1";
          // Clean up transition after it completes
          setTimeout(() => {
            root.style.transition = "";
          }, 200);
        });
      });
    }

    // Load font async (fire-and-forget)
    loadThemeFont(config.font);
  }

  // Apply immediately (works on initial render via main.js call too)
  if (typeof document !== "undefined") {
    applyTheme(themeId.value);
  }

  // Re-apply whenever the theme changes (e.g. after Inertia navigation)
  watch(themeId, (id) => {
    if (typeof document !== "undefined") {
      applyTheme(id);
    }
  }, { immediate: false });

  return { themeId, themeConfig, applyTheme };
}
