import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useDayChange } from "../useDayChange.js";

// Mock Inertia router
vi.mock("@inertiajs/vue3", () => ({
  router: { reload: vi.fn() },
}));

// Mock Vue lifecycle hooks to call handlers synchronously
let mountedCb = null;
let unmountedCb = null;
vi.mock("vue", () => ({
  onMounted: (cb) => { mountedCb = cb; },
  onUnmounted: (cb) => { unmountedCb = cb; },
}));

import { router } from "@inertiajs/vue3";

describe("useDayChange", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mountedCb = null;
    unmountedCb = null;
    router.reload.mockClear();
  });

  afterEach(() => {
    if (unmountedCb) unmountedCb();
    vi.useRealTimers();
  });

  it("fires reload at midnight", () => {
    // Set time to 23:59:58
    vi.setSystemTime(new Date(2026, 2, 11, 23, 59, 58));
    useDayChange();
    mountedCb();

    expect(router.reload).not.toHaveBeenCalled();

    // Advance past midnight + 1s buffer = need ~3s to cross midnight + 1s buffer
    vi.advanceTimersByTime(4000);
    expect(router.reload).toHaveBeenCalledTimes(1);
  });

  it("reloads on tab focus when day changed", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 12, 0, 0));
    useDayChange();
    mountedCb();

    // Simulate day change
    vi.setSystemTime(new Date(2026, 2, 12, 8, 0, 0));

    // Simulate tab becoming visible
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));

    expect(router.reload).toHaveBeenCalledTimes(1);
  });

  it("does NOT reload on tab focus if same day", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 12, 0, 0));
    useDayChange();
    mountedCb();

    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));

    expect(router.reload).not.toHaveBeenCalled();
  });

  it("cleans up on unmount", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 23, 59, 58));
    useDayChange();
    mountedCb();
    unmountedCb();

    // Advance past midnight — should NOT reload because we cleaned up
    vi.advanceTimersByTime(4000);
    expect(router.reload).not.toHaveBeenCalled();

    // Tab focus should also not trigger
    vi.setSystemTime(new Date(2026, 2, 12, 8, 0, 0));
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
    expect(router.reload).not.toHaveBeenCalled();
  });

  it("re-arms timer after midnight fires", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 23, 59, 58));
    useDayChange();
    mountedCb();

    // First midnight
    vi.advanceTimersByTime(4000);
    expect(router.reload).toHaveBeenCalledTimes(1);

    // Advance a full day + buffer for next midnight
    vi.advanceTimersByTime(24 * 60 * 60 * 1000 + 1000);
    expect(router.reload).toHaveBeenCalledTimes(2);
  });
});
