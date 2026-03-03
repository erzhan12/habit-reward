import { describe, it, expect } from "vitest";
import {
  themes,
  defaultTheme,
  getTheme,
  resolveTheme,
  DEFAULTS,
  VALID_INTERACTIONS,
  VALID_CARD_ENTRANCES,
  VALID_COMPLETION_CELEBRATIONS,
  VALID_HOVER_MICROS,
  VALID_STREAK_FIRES,
  VALID_DISPLAY_MODES,
  VALID_HABIT_LAYOUTS,
  VALID_DENSITIES,
} from "../src/themes/index.js";

describe("Theme config schema", () => {
  const REQUIRED_CSS_VARS = [
    "--color-bg-primary",
    "--color-bg-card",
    "--color-bg-card-hover",
    "--color-text-primary",
    "--color-text-secondary",
    "--color-accent",
    "--color-accent-hover",
    "--color-danger",
    "--color-streak-fire",
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
        expect(config.animations).toHaveProperty("completionCelebration");
        expect(config.animations).toHaveProperty("hoverMicro");
        expect(config.animations).toHaveProperty("streakFire");

        expect(config).toHaveProperty("reward");
        expect(config.reward).toHaveProperty("displayMode");

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
        expect(VALID_COMPLETION_CELEBRATIONS.has(config.animations.completionCelebration)).toBe(true);
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
