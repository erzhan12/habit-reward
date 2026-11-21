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

function dayButton(wrapper, day) {
  return wrapper.findAll("button").find((b) => b.attributes("aria-label")?.startsWith(`${day} November`));
}

describe("CalendarGrid day buttons", () => {
  it("expose the day-detail disclosure with aria-expanded and aria-controls", () => {
    const wrapper = mountGrid({ selectedDate: "2026-11-20", detailId: "day-detail" });

    const selected = dayButton(wrapper, 20);
    expect(selected.attributes("aria-expanded")).toBe("true");
    expect(selected.attributes("aria-controls")).toBe("day-detail");
    expect(selected.attributes("aria-pressed")).toBeUndefined();

    expect(dayButton(wrapper, 19).attributes("aria-expanded")).toBe("false");
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
