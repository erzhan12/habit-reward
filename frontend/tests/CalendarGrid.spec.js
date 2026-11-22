import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

vi.mock("../src/composables/useTheme.js", async () => {
  const { ref } = await import("vue");
  return { useTheme: () => ({ themeConfig: ref({ classes: { card: { rounded: "" } } }) }) };
});

import CalendarGrid from "../src/components/CalendarGrid.vue";

function mountGrid(props = {}) {
  return mount(CalendarGrid, {
    props: {
      currentMonth: "2026-11",
      userToday: "2026-11-21",
      completions: { 1: ["2026-11-20"], 2: ["2026-11-20"] },
      ...props,
    },
  });
}

// Fails with a readable message instead of a TypeError when the day is missing.
function dayButton(wrapper, day) {
  const button = wrapper.findAll("button").find((b) => b.attributes("aria-label")?.startsWith(`${day} November`));
  if (!button) throw new Error(`No day button for ${day} November`);
  return button;
}

describe("CalendarGrid day buttons", () => {
  it("expose the day-detail disclosure with aria-expanded and aria-controls", () => {
    const wrapper = mountGrid({ selectedDate: "2026-11-20", detailId: "day-detail" });

    const selected = dayButton(wrapper, 20);
    expect(selected.attributes("aria-expanded")).toBe("true");
    expect(selected.attributes("aria-controls")).toBe("day-detail");
    expect(selected.attributes("aria-pressed")).toBeUndefined();

    const other = dayButton(wrapper, 19);
    expect(other.attributes("aria-expanded")).toBe("false");
    // Only the open day points at the panel; it is not in the DOM otherwise.
    expect(other.attributes("aria-controls")).toBeUndefined();
  });

  it("points no day at the panel while nothing is selected", () => {
    const wrapper = mountGrid({ detailId: "day-detail" });
    for (const day of [19, 20]) {
      const button = dayButton(wrapper, day);
      expect(button.attributes("aria-expanded")).toBe("false");
      expect(button.attributes("aria-controls")).toBeUndefined();
    }
  });

  it("omits the disclosure attributes when there is no detail panel", () => {
    const wrapper = mountGrid({ selectedDate: "2026-11-20" });
    for (const day of [19, 20]) {
      const button = dayButton(wrapper, day);
      expect(button.attributes("aria-expanded")).toBeUndefined();
      expect(button.attributes("aria-controls")).toBeUndefined();
    }
  });

  it("labels each day with its completion count", () => {
    const wrapper = mountGrid();
    expect(dayButton(wrapper, 20).attributes("aria-label")).toBe("20 November, 2 habits completed");
    expect(dayButton(wrapper, 19).attributes("aria-label")).toBe("19 November, 0 habits completed");
  });

  it("emits the ISO date when a day is chosen", async () => {
    const wrapper = mountGrid();
    await dayButton(wrapper, 5).trigger("click");
    expect(wrapper.emitted("selectDay")).toEqual([["2026-11-05"]]);
  });
});
