/**
 * Tests for Login.vue using Vitest + @vue/test-utils.
 *
 * Prerequisites:
 *   npm install -D vitest @vue/test-utils happy-dom
 *
 * Run:
 *   npx vitest run tests/Login.spec.js
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";

// Stub Inertia router before importing the component.
vi.mock("@inertiajs/vue3", () => ({
  router: { visit: vi.fn() },
}));

import Login from "../src/pages/Login.vue";

function createWrapper() {
  // Provide a CSRF meta tag in the DOM.
  const meta = document.createElement("meta");
  meta.setAttribute("name", "csrf-token");
  meta.setAttribute("content", "test-csrf-token");
  document.head.appendChild(meta);

  return mount(Login, {
    global: {
      stubs: {},
    },
  });
}

describe("Login.vue", () => {
  let wrapper;

  afterEach(() => {
    if (wrapper) wrapper.unmount();
    // Clean up meta tags.
    document
      .querySelectorAll('meta[name="csrf-token"]')
      .forEach((el) => el.remove());
    vi.restoreAllMocks();
  });

  // --- Username validation ---

  it("rejects usernames shorter than 3 chars", async () => {
    wrapper = createWrapper();
    const input = wrapper.find("input");
    await input.setValue("ab");
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("Invalid Telegram username");
  });

  it("rejects usernames with special characters", async () => {
    wrapper = createWrapper();
    await wrapper.find("input").setValue("user@name!");
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("Invalid Telegram username");
  });

  it("accepts valid usernames", async () => {
    wrapper = createWrapper();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          token: "abc123",
          expires_at: new Date(Date.now() + 300000).toISOString(),
          message: "ok",
        }),
    });

    await wrapper.find("input").setValue("valid_user");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    // Should transition to "waiting" state (no error shown).
    expect(wrapper.text()).toContain("Check your Telegram");
  });

  // --- State machine transitions ---

  it("transitions idle → waiting on successful submit", async () => {
    wrapper = createWrapper();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ token: "tok", expires_at: "2099-01-01T00:00:00Z", message: "ok" }),
    });

    await wrapper.find("input").setValue("gooduser");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("Check your Telegram");
  });

  it("transitions to error state on network failure", async () => {
    wrapper = createWrapper();
    global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

    await wrapper.find("input").setValue("gooduser");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("Network error");
  });

  // --- Error handling ---

  it("shows error on 429 rate limit", async () => {
    wrapper = createWrapper();
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: () => Promise.resolve({ error: "Rate limited" }),
    });

    await wrapper.find("input").setValue("gooduser");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("Too many attempts");
  });

  it("shows error on 500 server error", async () => {
    wrapper = createWrapper();
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    });

    await wrapper.find("input").setValue("gooduser");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("Server error");
  });

  // --- Expired state transition ---

  it("transitions to expired state after timeout", async () => {
    vi.useFakeTimers();
    wrapper = createWrapper();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          token: "tok_expire",
          expires_at: new Date(Date.now() + 300000).toISOString(),
          message: "ok",
        }),
    });

    await wrapper.find("input").setValue("gooduser");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    // Should be in waiting state now
    expect(wrapper.text()).toContain("Check your Telegram");

    // Mock status poll to keep returning "pending"
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: "pending" }),
    });

    // Advance past the 5-minute LOGIN_EXPIRY_MS timeout
    vi.advanceTimersByTime(300_000);
    await flushPromises();

    // Should now show the expired state
    expect(wrapper.text()).toContain("Request expired");
    expect(wrapper.text()).toContain("timed out");

    vi.useRealTimers();
  });

  // --- Multiple rapid clicks (debouncing) ---

  it("ignores rapid duplicate submits while submitting is true", async () => {
    wrapper = createWrapper();
    let resolveFirst;
    const firstCall = new Promise((r) => {
      resolveFirst = r;
    });
    global.fetch = vi.fn().mockReturnValue(firstCall);

    await wrapper.find("input").setValue("gooduser");
    // First submit
    wrapper.find("form").trigger("submit");
    await flushPromises();

    // Second submit while first is in-flight — should be a no-op.
    wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Resolve the first call to clean up.
    resolveFirst({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ token: "t", expires_at: "2099-01-01", message: "ok" }),
    });
    await flushPromises();
  });
});
