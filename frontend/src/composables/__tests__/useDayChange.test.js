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

function simulateTabVisible() {
  Object.defineProperty(document, "visibilityState", {
    value: "visible",
    writable: true,
    configurable: true,
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

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
    vi.setSystemTime(new Date(2026, 2, 11, 23, 59, 58));
    useDayChange();
    mountedCb();

    expect(router.reload).not.toHaveBeenCalled();

    // Advance past midnight + 1s buffer
    vi.advanceTimersByTime(4000);
    expect(router.reload).toHaveBeenCalledTimes(1);
  });

  it("reloads on tab focus when day changed", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 12, 0, 0));
    useDayChange();
    mountedCb();

    // Simulate day change
    vi.setSystemTime(new Date(2026, 2, 12, 8, 0, 0));
    simulateTabVisible();

    // Advance past debounce (500ms)
    vi.advanceTimersByTime(500);
    expect(router.reload).toHaveBeenCalledTimes(1);
  });

  it("does NOT reload on tab focus if same day", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 12, 0, 0));
    useDayChange();
    mountedCb();

    simulateTabVisible();
    vi.advanceTimersByTime(500);

    expect(router.reload).not.toHaveBeenCalled();
  });

  it("cleans up on unmount — midnight timer does not fire", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 23, 59, 58));
    useDayChange();
    mountedCb();
    unmountedCb();

    vi.advanceTimersByTime(4000);
    expect(router.reload).not.toHaveBeenCalled();
  });

  it("cleans up on unmount — unmounted flag stops debounced visibility check", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 12, 0, 0));
    useDayChange();
    mountedCb();

    // Simulate day change and fire visibility event (queues debounce timer)
    vi.setSystemTime(new Date(2026, 2, 12, 8, 0, 0));
    simulateTabVisible();

    // Unmount BEFORE the 500ms debounce timer fires
    unmountedCb();

    // Advance past debounce — checkDayChange should bail via unmounted flag
    vi.advanceTimersByTime(500);
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

  it("debounces rapid tab focus events", () => {
    vi.setSystemTime(new Date(2026, 2, 11, 12, 0, 0));
    useDayChange();
    mountedCb();

    // Simulate day change
    vi.setSystemTime(new Date(2026, 2, 12, 8, 0, 0));

    // Rapid Alt+Tab: multiple visibility events within 500ms
    simulateTabVisible();
    vi.advanceTimersByTime(200);
    simulateTabVisible();
    vi.advanceTimersByTime(200);
    simulateTabVisible();

    // Advance past debounce from last event
    vi.advanceTimersByTime(500);
    expect(router.reload).toHaveBeenCalledTimes(1);
  });

  it("handles router.reload() errors gracefully", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    router.reload.mockImplementation(() => { throw new Error("network error"); });

    vi.setSystemTime(new Date(2026, 2, 11, 23, 59, 58));
    useDayChange();
    mountedCb();

    // Should not throw
    vi.advanceTimersByTime(4000);
    expect(consoleSpy).toHaveBeenCalledWith(
      "useDayChange: reload failed on midnight timer",
      expect.any(Error),
    );

    consoleSpy.mockRestore();
    router.reload.mockReset();
  });
});
