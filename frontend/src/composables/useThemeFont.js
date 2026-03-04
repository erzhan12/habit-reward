/**
 * Theme font loading system.
 *
 * Loads Google Fonts dynamically based on theme config. Maintains an
 * in-memory cache of already-loaded font families to avoid duplicate
 * <link> injections.
 */

const loadedFonts = new Set();

/**
 * Load theme font and apply --font-family CSS variable.
 *
 * @param {{ family: string, import: string|null, weight: string, size: string }} fontConfig
 * @returns {Promise<void>}
 */
export async function loadThemeFont(fontConfig) {
  if (!fontConfig) return;

  const root = document.documentElement;

  // Always set the font-family CSS variable
  root.style.setProperty('--font-family', fontConfig.family);

  // If no external font URL, nothing more to load
  if (!fontConfig.import) return;

  // If already loaded this font family, skip injection
  if (loadedFonts.has(fontConfig.family)) return;

  // Inject <link> for Google Fonts
  try {
    await new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = fontConfig.import;
      link.onload = resolve;
      link.onerror = () => reject(new Error(`Failed to load font: ${fontConfig.import}`));
      document.head.appendChild(link);
    });
    loadedFonts.add(fontConfig.family);
  } catch (err) {
    console.warn('[useThemeFont]', err.message, '— falling back to system font');
    root.style.setProperty('--font-family', 'system-ui, -apple-system, sans-serif');
  }
}
