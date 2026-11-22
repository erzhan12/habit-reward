import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

vi.mock("../src/composables/useTheme.js", async () => {
  const { ref } = await import("vue");
  return { useTheme: () => ({ themeConfig: ref({ classes: { card: { rounded: "" } } }) }) };
});

import FlashMessages from "../src/components/FlashMessages.vue";

// Messages are shown in onMounted, so the list renders one tick after mount.
async function mountFlash(messages) {
  const wrapper = mount(FlashMessages, { props: { messages } });
  await wrapper.vm.$nextTick();
  return wrapper;
}

describe("FlashMessages", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("renders a new node for each new batch instead of patching by index", async () => {
    const wrapper = await mountFlash([{ type: "success", text: "Saved" }]);
    const first = wrapper.get(".flash").element;

    await wrapper.setProps({ messages: [{ type: "error", text: "Failed" }] });
    await wrapper.vm.$nextTick();

    const second = wrapper.get(".flash");
    expect(second.text()).toBe("Failed");
    expect(second.element).not.toBe(first);
  });

  it("keeps a newer batch for its full time when an older one is still showing", async () => {
    const wrapper = await mountFlash([{ type: "success", text: "First" }]);
    vi.advanceTimersByTime(3000);
    await wrapper.setProps({ messages: [{ type: "success", text: "Second" }] });
    await wrapper.vm.$nextTick();

    vi.advanceTimersByTime(1500); // the first batch's 4 s timer has fired by now
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Second");

    vi.advanceTimersByTime(2600);
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".flash").exists()).toBe(false);
  });

  it("clears its pending hide timer on unmount", async () => {
    const wrapper = await mountFlash([{ type: "success", text: "Saved" }]);
    expect(vi.getTimerCount()).toBe(1);

    wrapper.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("marks errors as alerts inside a persistent live region", async () => {
    const wrapper = await mountFlash([{ type: "error", text: "Nope" }, { type: "info", text: "FYI" }]);
    expect(wrapper.attributes("aria-live")).toBe("polite");
    const items = wrapper.findAll(".flash");
    expect(items[0].attributes("role")).toBe("alert");
    expect(items[1].attributes("role")).toBeUndefined();
  });
});
