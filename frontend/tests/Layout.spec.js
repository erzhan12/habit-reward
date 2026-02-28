import { describe, it, expect, vi, afterEach } from "vitest";
import { mount } from "@vue/test-utils";

vi.mock("@inertiajs/vue3", () => ({
  Link: { template: "<a><slot /></a>" },
  router: { post: vi.fn() },
  usePage: () => ({ url: "/", props: { flash: [] } }),
}));

import { router } from "@inertiajs/vue3";
import Layout from "../src/components/Layout.vue";

describe("Layout.vue", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("calls logout endpoint when logout button is clicked", async () => {
    const wrapper = mount(Layout, {
      global: {
        stubs: {
          BottomNav: true,
          FlashMessages: true,
        },
      },
    });

    const logoutButton = wrapper.find('button[aria-label="Log out of your account"]');
    expect(logoutButton.exists()).toBe(true);

    await logoutButton.trigger("click");

    expect(router.post).toHaveBeenCalledWith("/auth/logout/");
  });

  it("logs error and re-enables button when logout fails", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    router.post.mockRejectedValue(new Error("Network failure"));

    const wrapper = mount(Layout, {
      global: {
        stubs: {
          BottomNav: true,
          FlashMessages: true,
        },
      },
    });

    const logoutButton = wrapper.find('button[aria-label="Log out of your account"]');
    await logoutButton.trigger("click");
    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith("Logout failed:", expect.any(Error));
    });

    // Button should be re-enabled after error
    expect(logoutButton.attributes("disabled")).toBeUndefined();
    expect(wrapper.text()).toContain("Logout");

    // Should show error message to user
    expect(wrapper.text()).toContain("Logout failed");

    consoleSpy.mockRestore();
  });

  it("disables logout button while logging out", async () => {
    // Make router.post return a pending promise so isLoggingOut stays true
    router.post.mockReturnValue(new Promise(() => {}));

    const wrapper = mount(Layout, {
      global: {
        stubs: {
          BottomNav: true,
          FlashMessages: true,
        },
      },
    });

    const logoutButton = wrapper.find('button[aria-label="Log out of your account"]');

    expect(logoutButton.attributes("disabled")).toBeUndefined();

    // Click should set loading state
    await logoutButton.trigger("click");
    await wrapper.vm.$nextTick();

    // Button text should change
    expect(wrapper.text()).toContain("Logging out");
  });
});
