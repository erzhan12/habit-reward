import { computed, watch } from "vue";
import { usePage } from "@inertiajs/vue3";
import { getTheme, defaultTheme } from "../themes/index.js";

/**
 * Reactive theme composable.
 *
 * Reads `page.props.userTheme` (shared by InertiaFlashMiddleware), looks up
 * the full theme config, applies CSS custom properties to <html>, sets the
 * `data-theme` attribute, and returns reactive helpers for components.
 */
export function useTheme() {
  const page = usePage();

  const themeId = computed(() => page.props.userTheme || defaultTheme);
  const themeConfig = computed(() => getTheme(themeId.value));

  function applyTheme(id) {
    const config = getTheme(id);

    // Batch CSS custom property updates in a single animation frame
    // to avoid layout thrashing from setting properties one by one
    requestAnimationFrame(() => {
      const root = document.documentElement;
      for (const [prop, value] of Object.entries(config.cssVars)) {
        root.style.setProperty(prop, value);
      }

      // Set data-theme attribute for CSS-level overrides
      root.setAttribute("data-theme", id);
    });
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

  return { themeId, themeConfig };
}
