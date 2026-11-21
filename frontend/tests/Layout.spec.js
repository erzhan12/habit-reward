import { describe, it, expect, vi, afterEach } from "vitest";
import { mount } from "@vue/test-utils";

vi.mock("@inertiajs/vue3", () => ({
  Link: { template: "<a><slot /></a>" },
  router: { post: vi.fn() },
  usePage: () => ({ url: "/", props: { flash: [] } }),
}));

import { router } from "@inertiajs/vue3";
import Layout from "../src/components/Layout.vue";

function mountLayout() {
  return mount(Layout, {
    global: {
      stubs: {
        BottomNav: true,
        FlashMessages: true,
      },
    },
  });
}

// router.post returns void; Layout drives its state from the onStart/onFinish
// options, so the tests invoke the captured callbacks directly.
function lastPostOptions() {
  const calls = router.post.mock.calls;
  return calls[calls.length - 1][2];
}

describe("Layout.vue", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("calls logout endpoint when logout button is clicked", async () => {
    const wrapper = mountLayout();

    const logoutButton = wrapper.find('button[aria-label="Log out of your account"]');
    expect(logoutButton.exists()).toBe(true);

    await logoutButton.trigger("click");

    expect(router.post).toHaveBeenCalledWith("/auth/logout/", {}, expect.any(Object));
  });

  it("disables logout buttons while logging out", async () => {
    const wrapper = mountLayout();
    const logoutButton = wrapper.find('button[aria-label="Log out of your account"]');
    expect(logoutButton.attributes("disabled")).toBeUndefined();

    await logoutButton.trigger("click");
    lastPostOptions().onStart();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain("Logging out");
    for (const btn of wrapper.findAll('button[aria-label="Log out of your account"]')) {
      expect(btn.attributes("disabled")).toBeDefined();
      expect(btn.attributes("aria-busy")).toBe("true");
    }
  });

  it("re-enables the button when the request finishes", async () => {
    const wrapper = mountLayout();
    const logoutButton = wrapper.find('button[aria-label="Log out of your account"]');

    await logoutButton.trigger("click");
    const opts = lastPostOptions();
    opts.onStart();
    await wrapper.vm.$nextTick();
    opts.onFinish();
    await wrapper.vm.$nextTick();

    expect(logoutButton.attributes("disabled")).toBeUndefined();
    expect(wrapper.text()).not.toContain("Logging out");
    expect(wrapper.text()).toContain("Logout");
  });

  it("renders a logout button for mobile widths", () => {
    const wrapper = mountLayout();
    // sidebar (desktop) + mobile top bar
    expect(wrapper.findAll('button[aria-label="Log out of your account"]').length).toBe(2);
  });
});
