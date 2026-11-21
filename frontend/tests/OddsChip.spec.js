import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import OddsChip from "../src/components/OddsChip.vue";

// Rounded p(s) for days 1..30, as the dashboard view sends it.
const CURVE = [20, 25, 29, 33, 36, 38, 40, 42, 43, 44, 45, 46, 47, 47, 48, 48, 48, 49, 49, 49, 49, 49, 49, 50, 50, 50, 50, 50, 50, 50];
const CHANCE = { curve: CURVE, cap: 50 };

function mountChip(props = {}) {
  return mount(OddsChip, {
    props: { rewardChance: 40, nextStreak: 7, chance: CHANCE, ...props },
  });
}

describe("OddsChip", () => {
  it.each([
    ["badge", "🎲 40% next"],
    ["chip", "🎲 40% next"],
    ["stub", "ODDS 40%"],
    ["drop", "drop: 40%"],
  ])("labels the next completion in %s style", (oddsStyle, text) => {
    expect(mountChip({ oddsStyle }).get('[data-testid="odds-chip"]').text()).toBe(text);
  });

  it.each(["badge", "chip", "stub", "drop"])("labels a completed habit in %s style", (oddsStyle) => {
    const chip = mountChip({ oddsStyle, completed: true, rewardChance: 29 }).get('[data-testid="odds-chip"]');
    expect(chip.text()).toBe("rolled at 29%");
  });

  it("falls back to the badge style for an unknown style", () => {
    expect(mountChip({ oddsStyle: "nope" }).text()).toBe("🎲 40% next");
  });

  it("applies the theme badge class only in badge style", () => {
    expect(mountChip({ oddsStyle: "badge", badgeClass: "theme-badge" }).get("button").classes()).toContain("theme-badge");
    expect(mountChip({ oddsStyle: "chip", badgeClass: "theme-badge" }).get("button").classes()).not.toContain("theme-badge");
  });

  it("toggles the hint and aria-expanded", async () => {
    const wrapper = mountChip();
    const chip = wrapper.get("button");
    expect(chip.attributes("aria-expanded")).toBe("false");
    expect(wrapper.find('[data-testid="odds-hint"]').exists()).toBe(false);

    await chip.trigger("click");
    const hint = wrapper.get('[data-testid="odds-hint"]');
    expect(chip.attributes("aria-expanded")).toBe("true");
    expect(chip.attributes("aria-controls")).toBe(hint.attributes("id"));
    expect(hint.text()).toBe(
      "Next completion 40%, the one after 42%. Levels off near 50%. If the streak breaks, it starts again at 20%.",
    );
    expect(hint.find("svg").exists()).toBe(true);

    await chip.trigger("click");
    expect(wrapper.find('[data-testid="odds-hint"]').exists()).toBe(false);
  });

  it("explains the roll on a completed habit", async () => {
    const wrapper = mountChip({ completed: true, rewardChance: 36, nextStreak: 6 });
    await wrapper.get("button").trigger("click");
    expect(wrapper.get('[data-testid="odds-hint"]').text()).toBe("Today's roll was at 36%. Next completion 38%.");
  });

  it("clamps streak days past the end of the curve", async () => {
    const wrapper = mountChip({ rewardChance: 50, nextStreak: 40 });
    await wrapper.get("button").trigger("click");
    expect(wrapper.get('[data-testid="odds-hint"]').text()).toBe(
      "You're at the top: 50% on every completion while the streak holds. If the streak breaks, it starts again at 20%.",
    );
  });

  it("falls back to the curve's last value when the cap is missing", async () => {
    const wrapper = mountChip({ chance: { curve: CURVE } });
    await wrapper.get("button").trigger("click");
    expect(wrapper.get('[data-testid="odds-hint"]').text()).toBe(
      "Next completion 40%, the one after 42%. Levels off near 50%. If the streak breaks, it starts again at 20%.",
    );
  });

  it("works without the chance curve", async () => {
    const wrapper = mountChip({ chance: null });
    expect(wrapper.get("button").text()).toBe("🎲 40% next");
    await wrapper.get("button").trigger("click");
    const hint = wrapper.get('[data-testid="odds-hint"]');
    expect(hint.text()).toBe("Your chance grows with your streak and starts over if the streak breaks.");
    expect(hint.find("svg").exists()).toBe(false);
  });

  it("keeps touches on the chip from reaching a swipe wrapper", async () => {
    const seen = [];
    const Parent = {
      components: { OddsChip },
      template: `<div @touchstart="seen.push('start')" @touchmove="seen.push('move')" @touchend="seen.push('end')" @click="seen.push('click')">
        <OddsChip :reward-chance="40" />
      </div>`,
      setup: () => ({ seen }),
    };
    const wrapper = mount(Parent);
    const chip = wrapper.get("button");
    for (const ev of ["touchstart", "touchmove", "touchend", "click"]) await chip.trigger(ev);
    expect(seen).toEqual([]);
  });
});
