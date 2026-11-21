import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import HabitCardContent from "../src/components/HabitCardContent.vue";

vi.mock("../src/composables/useTheme.js", () => ({
  useTheme: () => ({
    themeConfig: { value: { habitCard: { oddsStyle: "badge", showOutcome: false } } },
  }),
}));

const baseHabit = {
  name: "Morning walk",
  weight: 2,
  rewardChance: 50,
  streak: 3,
  completedToday: false,
};

function mountComponent(habitOverrides = {}, propOverrides = {}) {
  return mount(HabitCardContent, {
    props: {
      habit: { ...baseHabit, ...habitOverrides },
      tc: { badge: { base: "" } },
      streakClass: "streak-fire-bounce",
      ...propOverrides,
    },
  });
}

function findStreakElements(wrapper) {
  const spans = wrapper.findAll("span");

  return {
    emoji: spans.find((span) => span.text() === "🔥"),
    text: spans.find((span) => span.text().includes("day streak")),
  };
}

describe("HabitCardContent", () => {
  it("shows the reward chance without the weight prefix", () => {
    const wrapper = mountComponent({ weight: 7, rewardChance: 33 });

    expect(wrapper.text()).toContain("33%");
    expect(wrapper.text()).not.toContain("7w");
    expect(wrapper.text()).not.toContain("·");
  });

  it("keeps bright streak styling for incomplete habits", () => {
    const wrapper = mountComponent({ completedToday: false });
    const { emoji, text } = findStreakElements(wrapper);

    expect(emoji).toBeDefined();
    expect(text).toBeDefined();
    expect(emoji.classes()).toContain("text-streak-fire");
    expect(text.classes()).toContain("text-streak-fire");
    expect(emoji.classes()).toContain("streak-fire-bounce");
    expect(text.classes()).toContain("streak-fire-bounce");
    expect(emoji.classes()).not.toContain("text-text-muted");
    expect(text.classes()).not.toContain("text-text-muted");
    expect(emoji.classes()).not.toContain("streak-emoji-muted");
  });

  it("uses muted streak styling for completed habits", () => {
    const wrapper = mountComponent({ completedToday: true });
    const { emoji, text } = findStreakElements(wrapper);

    expect(wrapper.find("h3").classes()).toContain("line-through");
    expect(emoji).toBeDefined();
    expect(text).toBeDefined();
    expect(emoji.classes()).not.toContain("text-streak-fire");
    expect(text.classes()).not.toContain("text-streak-fire");
    expect(emoji.classes()).toContain("text-text-muted");
    expect(text.classes()).toContain("text-text-muted");
    expect(emoji.classes()).not.toContain("streak-fire-bounce");
    expect(text.classes()).not.toContain("streak-fire-bounce");
    expect(emoji.classes()).toContain("streak-emoji-muted");
  });

  it("does not render the streak block when there is no streak", () => {
    const wrapper = mountComponent({ streak: 0 });
    const spans = wrapper.findAll("span");

    expect(spans.some((span) => span.text() === "🔥")).toBe(false);
    expect(wrapper.text()).not.toContain("day streak");
  });

  it("puts the odds chip on the meta line, also with no streak", () => {
    const wrapper = mountComponent({ streak: 0, rewardChance: 20 });
    expect(wrapper.find("h3").text()).toBe("Morning walk");
    expect(wrapper.get('[data-testid="odds-chip"]').text()).toBe("🎲 20% next");
  });

  it("shows the outcome on its own line under the title", async () => {
    vi.resetModules();
    vi.doMock("../src/composables/useTheme.js", () => ({
      useTheme: () => ({ themeConfig: { value: { habitCard: { oddsStyle: "chip", showOutcome: true } } } }),
    }));
    const { default: Card } = await import("../src/components/HabitCardContent.vue");
    const wrapper = mount(Card, {
      props: {
        habit: {
          ...baseHabit,
          completedToday: true,
          todayResult: { gotReward: true, rewardName: "Sushi dinner" },
        },
        tc: { badge: { base: "" } },
      },
    });
    expect(wrapper.find("h3").text()).toBe("Morning walk");
    expect(wrapper.find('[data-testid="outcome"]').text()).toBe("🎁 piece won — Sushi dinner");
    vi.doUnmock("../src/composables/useTheme.js");
  });

  it("renders without stray empty class tokens when streakClass is empty", () => {
    const wrapper = mountComponent({}, { streakClass: "" });
    const { emoji, text } = findStreakElements(wrapper);

    expect(emoji).toBeDefined();
    expect(text).toBeDefined();
    expect(emoji.classes()).not.toContain("");
    expect(text.classes()).not.toContain("");
  });

  it("shows the freeze chip only when a freeze is held", () => {
    expect(mountComponent({ freezeCount: 1 }).find('[data-testid="freeze-chip"]').text()).toBe("❄️");
    expect(mountComponent({ freezeCount: 2 }).find('[data-testid="freeze-chip"]').text()).toBe("❄️×2");
    expect(mountComponent({ freezeCount: 0 }).find('[data-testid="freeze-chip"]').exists()).toBe(false);
  });

  it("shows the freeze chip with no streak", () => {
    const wrapper = mountComponent({ streak: 0, freezeCount: 1 });
    expect(wrapper.find('[data-testid="freeze-chip"]').exists()).toBe(true);
    expect(wrapper.text()).not.toContain("day streak");
  });

  it.each([
    ["badge", "🎲 50% next"],
    ["chip", "🎲 50% next"],
    ["stub", "ODDS 50%"],
    ["drop", "drop: 50%"],
  ])("shows the chance next to the freeze chip in %s style", async (oddsStyle, label) => {
    vi.resetModules();
    vi.doMock("../src/composables/useTheme.js", () => ({
      useTheme: () => ({ themeConfig: { value: { habitCard: { oddsStyle, showOutcome: true } } } }),
    }));
    const { default: Card } = await import("../src/components/HabitCardContent.vue");
    const wrapper = mount(Card, {
      props: { habit: { ...baseHabit, freezeCount: 1 }, tc: { badge: { base: "" } } },
    });
    expect(wrapper.get('[data-testid="odds-chip"]').text()).toBe(label);
    expect(wrapper.find('[data-testid="freeze-chip"]').exists()).toBe(true);
    vi.doUnmock("../src/composables/useTheme.js");
  });

  it("hints the covered day without a timezone shift", () => {
    const hint = mountComponent({ freezeUsedFor: "2026-11-01" }).find('[data-testid="freeze-hint"]');
    expect(hint.text()).toContain("Freeze used for 1 Nov");
  });

  it("hints an at-risk freeze", () => {
    const hint = mountComponent({ freezeCount: 1, freezeAtRisk: true }).find('[data-testid="freeze-hint"]');
    expect(hint.text()).toContain("Skip today and your freeze will be used tonight.");
  });

  it("hides freeze hints once completed today", () => {
    const wrapper = mountComponent({ completedToday: true, freezeAtRisk: true, freezeUsedFor: "2026-11-17" });
    expect(wrapper.find('[data-testid="freeze-hint"]').exists()).toBe(false);
  });
});
