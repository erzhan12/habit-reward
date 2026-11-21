import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  themes,
  defaultTheme,
  getTheme,
  resolveTheme,
  DEFAULTS,
  VALID_INTERACTIONS,
  VALID_CARD_ENTRANCES,
  VALID_REWARD_POPUP_VARIANTS,
  VALID_HOVER_MICROS,
  VALID_STREAK_FIRES,
  VALID_DISPLAY_MODES,
  VALID_HABIT_LAYOUTS,
  VALID_DENSITIES,
  VALID_ODDS_STYLES,
} from "../src/themes/index.js";

describe("Theme config schema", () => {
  const REQUIRED_CSS_VARS = [
    "--color-bg-primary",
    "--color-bg-card",
    "--color-bg-card-hover",
    "--color-text-primary",
    "--color-text-secondary",
    "--color-text-muted",
    "--color-accent",
    "--color-accent-hover",
    "--color-danger",
    "--color-streak-fire",
    "--color-border",
    "--color-track",
  ];

  const REQUIRED_CLASS_GROUPS = ["card", "button", "input", "badge", "select"];

  for (const [id, raw] of Object.entries(themes)) {
    describe(`theme: ${id}`, () => {
      const config = resolveTheme(raw);

      it("has all required CSS variables", () => {
        for (const v of REQUIRED_CSS_VARS) {
          expect(config.cssVars).toHaveProperty(v);
        }
      });

      it("has all required class groups", () => {
        for (const group of REQUIRED_CLASS_GROUPS) {
          expect(config.classes).toHaveProperty(group);
        }
      });

      it("has all extended config keys after resolveTheme()", () => {
        expect(config).toHaveProperty("font");
        expect(config.font).toHaveProperty("family");
        expect(config.font).toHaveProperty("import");
        expect(config.font).toHaveProperty("weight");
        expect(config.font).toHaveProperty("size");

        expect(config).toHaveProperty("interactions");
        expect(config.interactions).toHaveProperty("habitComplete");

        expect(config).toHaveProperty("animations");
        expect(config.animations).toHaveProperty("cardEntrance");
        expect(config.animations).toHaveProperty("hoverMicro");
        expect(config.animations).toHaveProperty("streakFire");
        // Forward-compat guard: deprecated key must not reappear via DEFAULTS
        // leakage or a raw theme block (deepMerge preserves unknown keys).
        expect("completionCelebration" in config.animations).toBe(false);

        expect(config).toHaveProperty("reward");
        expect(config.reward).toHaveProperty("displayMode");
        expect(config.reward).toHaveProperty("rewardPopupVariant");

        expect(config).toHaveProperty("pageLayout");
        expect(config.pageLayout).toHaveProperty("habitList");
        expect(config.pageLayout).toHaveProperty("density");
        expect(config.pageLayout).toHaveProperty("rewardList");
      });

      it("uses valid values for interaction type", () => {
        expect(VALID_INTERACTIONS.has(config.interactions.habitComplete)).toBe(true);
      });

      it("uses valid values for animations", () => {
        expect(VALID_CARD_ENTRANCES.has(config.animations.cardEntrance)).toBe(true);
        expect(VALID_REWARD_POPUP_VARIANTS.has(config.reward.rewardPopupVariant)).toBe(true);
        expect(VALID_HOVER_MICROS.has(config.animations.hoverMicro)).toBe(true);
        expect(VALID_STREAK_FIRES.has(config.animations.streakFire)).toBe(true);
      });

      it("uses valid values for page layout", () => {
        expect(VALID_DISPLAY_MODES.has(config.reward.displayMode)).toBe(true);
        expect(VALID_HABIT_LAYOUTS.has(config.pageLayout.habitList)).toBe(true);
        expect(VALID_DENSITIES.has(config.pageLayout.density)).toBe(true);
      });
    });
  }
});

describe("Deprecated keys", () => {
  // Diagnostic clarity: pinpoint the offending raw theme block on regression.
  for (const [id, raw] of Object.entries(themes)) {
    it(`raw theme "${id}" does not redeclare completionCelebration`, () => {
      expect("completionCelebration" in (raw.animations ?? {})).toBe(false);
    });
  }
});

describe("getTheme()", () => {
  it("returns default theme for unknown ID", () => {
    const config = getTheme("nonexistent_theme");
    expect(config.cssVars["--color-accent"]).toBe(
      themes[defaultTheme].cssVars["--color-accent"]
    );
  });

  it("returns clean_modern as the default theme", () => {
    expect(defaultTheme).toBe("clean_modern");
    expect(themes).toHaveProperty("clean_modern");
  });
});

describe("Old alias IDs", () => {
  const OLD_IDS = [
    "dark_emerald",
    "light_clean",
    "neon_cyberpunk",
    "warm_earth",
    "ocean_gradient",
    "ios_glass",
    "minimal_ink",
  ];

  for (const oldId of OLD_IDS) {
    it(`resolves old ID "${oldId}" to a valid theme`, () => {
      const config = getTheme(oldId);
      expect(config).toHaveProperty("cssVars");
      expect(config).toHaveProperty("classes");
      expect(config).toHaveProperty("font");
      expect(config).toHaveProperty("animations");
    });
  }
});

describe("Validation constants", () => {
  it("VALID_INTERACTIONS has expected values", () => {
    expect(VALID_INTERACTIONS.has("button-right")).toBe(true);
    expect(VALID_INTERACTIONS.has("checkbox")).toBe(true);
    expect(VALID_INTERACTIONS.has("swipe-reveal")).toBe(true);
  });

  it("VALID_CARD_ENTRANCES has expected values", () => {
    expect(VALID_CARD_ENTRANCES.has("none")).toBe(true);
    expect(VALID_CARD_ENTRANCES.has("fade-in")).toBe(true);
    expect(VALID_CARD_ENTRANCES.has("slide-up")).toBe(true);
    expect(VALID_CARD_ENTRANCES.has("stagger-fade")).toBe(true);
  });

  it("VALID_DENSITIES has expected values", () => {
    expect(VALID_DENSITIES.has("spacious")).toBe(true);
    expect(VALID_DENSITIES.has("normal")).toBe(true);
    expect(VALID_DENSITIES.has("compact")).toBe(true);
  });
});

describe("DEFAULTS", () => {
  it("provides fallback for all extended keys", () => {
    expect(DEFAULTS.font.family).toContain("system-ui");
    expect(DEFAULTS.font.import).toBeNull();
    expect(DEFAULTS.interactions.habitComplete).toBe("button-right");
    expect(DEFAULTS.animations.cardEntrance).toBe("none");
    expect(DEFAULTS.reward.displayMode).toBe("expand-from-card");
    expect(DEFAULTS.pageLayout.habitList).toBe("list");
    expect(DEFAULTS.pageLayout.density).toBe("normal");
  });
});

// ── Contrast floor (WCAG AA 4.5:1) ─────────────────────────────────
function parseColor(value, base) {
  const v = value.replace(/\s+/g, "");
  if (v.startsWith("#")) {
    const h = v.slice(1);
    return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  }
  const m = v.match(/[\d.]+/g).map(Number);
  const alpha = m.length > 3 ? m[3] : 1;
  return [0, 1, 2].map((i) => m[i] * alpha + base[i] * (1 - alpha));
}

function luminance(rgb) {
  const [r, g, b] = rgb.map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe("Theme text contrast", () => {
  for (const [id, raw] of Object.entries(themes)) {
    it(`${id}: muted and secondary text reach 4.5:1 on card and page`, () => {
      const v = raw.cssVars;
      const page = parseColor(v["--color-bg-primary"], [0, 0, 0]);
      // Translucent cards (ios_native) are composited over the page colour.
      const card = parseColor(v["--color-bg-card"], page);
      for (const key of ["--color-text-muted", "--color-text-secondary"]) {
        const fg = parseColor(v[key], page);
        expect(contrast(fg, card), `${key} on card`).toBeGreaterThanOrEqual(4.5);
        expect(contrast(fg, page), `${key} on page`).toBeGreaterThanOrEqual(4.5);
      }
    });
  }
});

// ── app.css mirrors cssVars (pre-hydration paint) ───────────────────
describe("app.css theme blocks match themes/index.js cssVars", () => {
  const css = readFileSync(resolve(__dirname, "../src/app.css"), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "");
  const norm = (value) => value.replace(/\s+/g, "").toLowerCase();

  function cssBlockVars(selector) {
    const start = css.indexOf(selector);
    expect(start, `missing ${selector} in app.css`).toBeGreaterThanOrEqual(0);
    const body = css.slice(css.indexOf("{", start) + 1, css.indexOf("}", start));
    const vars = {};
    for (const m of body.matchAll(/(--color-[\w-]+)\s*:\s*([^;]+);/g)) vars[m[1]] = norm(m[2]);
    return vars;
  }

  for (const [id, raw] of Object.entries(themes)) {
    it(`${id}: every --color-* value is mirrored`, () => {
      const selector = id === defaultTheme ? "@theme" : `[data-theme="${id}"]`;
      const cssVars = cssBlockVars(selector);
      for (const [key, value] of Object.entries(raw.cssVars)) {
        expect(cssVars[key], `${id} ${key}`).toBe(norm(value));
      }
    });
  }
});

describe("habitCard.oddsStyle", () => {
  for (const id of Object.keys(themes)) {
    it(`${id}: resolves to a valid odds style`, () => {
      expect(VALID_ODDS_STYLES.has(getTheme(id).habitCard.oddsStyle)).toBe(true);
    });
  }

  it("gives the three reward-economy themes their own odds style", () => {
    expect(getTheme("night_arcade").habitCard.oddsStyle).toBe("chip");
    expect(getTheme("ticket_stub").habitCard.oddsStyle).toBe("stub");
    expect(getTheme("quest_log").habitCard.oddsStyle).toBe("drop");
    expect(getTheme("clean_modern").habitCard.oddsStyle).toBe("badge");
  });
});
