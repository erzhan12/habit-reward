import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import HabitCardContent from "../src/components/HabitCardContent.vue";

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
    expect(emoji.attributes("style")).toBeFalsy();
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
    expect(emoji.classes()).toContain("streak-fire-bounce");
    expect(text.classes()).toContain("streak-fire-bounce");
    expect(emoji.attributes("style")).toContain("filter: grayscale(1) opacity(0.5)");
  });

  it("does not render the streak block when there is no streak", () => {
    const wrapper = mountComponent({ streak: 0 });
    const spans = wrapper.findAll("span");

    expect(spans.some((span) => span.text() === "🔥")).toBe(false);
    expect(wrapper.text()).not.toContain("day streak");
  });

  it("renders without stray empty class tokens when streakClass is empty", () => {
    const wrapper = mountComponent({}, { streakClass: "" });
    const { emoji, text } = findStreakElements(wrapper);

    expect(emoji).toBeDefined();
    expect(text).toBeDefined();
    expect(emoji.classes()).not.toContain("");
    expect(text.classes()).not.toContain("");
  });
});
