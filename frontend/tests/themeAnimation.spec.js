import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  animateSinkBounce,
  triggerCompletionCelebration,
} from "../src/composables/useThemeAnimation.js";

// Spy used by all tests to observe animate() calls.
let animateSpy;
// Stub returned by animate(); each test can swap finished/throw behaviour.
let animationStub;

/** @param {{top: number, left: number, width: number, height: number}} [rect] */
function makeCardEl(rect = { top: 0, left: 0, width: 200, height: 80 }) {
  return {
    getBoundingClientRect: () => ({
      ...rect,
      right: rect.left + rect.width,
      bottom: rect.top + rect.height,
    }),
    animate: animateSpy,
  };
}

vi.mock("../src/utils/particles.js", () => ({
  spawnParticles: vi.fn().mockResolvedValue(undefined),
}));

import { spawnParticles } from "../src/utils/particles.js";

beforeEach(() => {
  animationStub = {
    finished: Promise.resolve(),
    cancel: vi.fn(),
  };
  animateSpy = vi.fn(() => animationStub);
  // Default: reduced-motion off
  window.matchMedia = vi.fn().mockReturnValue({ matches: false });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("animateSinkBounce", () => {
  it("resolves after the Web Animation finishes", async () => {
    const cardEl = makeCardEl({ top: 100, left: 0, width: 200, height: 80 });
    const oldRect = { top: 40, left: 0, width: 200, height: 80 };

    const p = animateSinkBounce(cardEl, oldRect);
    await expect(p).resolves.toBeUndefined();

    expect(animateSpy).toHaveBeenCalledTimes(1);
    const [keyframes, options] = animateSpy.mock.calls[0];
    expect(keyframes[0].transform).toBe("translate(0px, -60px)");
    expect(keyframes[keyframes.length - 1].transform).toBe("translate(0, 0)");
    expect(options.duration).toBe(600);
  });

  it("no-ops with missing element", async () => {
    await expect(animateSinkBounce(null, { top: 0, left: 0 })).resolves.toBeUndefined();
    expect(animateSpy).not.toHaveBeenCalled();
  });

  it("no-ops when WAAPI is missing", async () => {
    const el = { getBoundingClientRect: () => ({ top: 0, left: 0 }) };
    await expect(animateSinkBounce(el, { top: 10, left: 0 })).resolves.toBeUndefined();
    expect(animateSpy).not.toHaveBeenCalled();
  });

  it("swallows animate() sync throws", async () => {
    animateSpy = vi.fn(() => {
      throw new Error("nope");
    });
    const el = makeCardEl({ top: 50, left: 0, width: 100, height: 30 });
    await expect(animateSinkBounce(el, { top: 0, left: 0 })).resolves.toBeUndefined();
  });

  it("swallows finished promise rejection (AbortError)", async () => {
    animationStub = {
      finished: Promise.reject(new Error("Aborted")),
      cancel: vi.fn(),
    };
    animateSpy = vi.fn(() => animationStub);
    const el = makeCardEl();
    await expect(animateSinkBounce(el, { top: 0, left: 0 })).resolves.toBeUndefined();
  });

  it("handles missing oldRect (renders an in-place mini-bounce)", async () => {
    const el = makeCardEl({ top: 50, left: 50, width: 200, height: 80 });
    await animateSinkBounce(el, null);
    const [keyframes] = animateSpy.mock.calls[0];
    expect(keyframes[0].transform).toBe("translate(0px, 0px)");
  });

  it("composes horizontal + vertical delta correctly", async () => {
    const el = makeCardEl({ top: 40, left: 50, width: 200, height: 80 });
    const oldRect = { top: 0, left: 100, width: 200, height: 80 };
    await animateSinkBounce(el, oldRect);
    const [keyframes] = animateSpy.mock.calls[0];
    expect(keyframes[0].transform).toBe("translate(50px, -40px)");
    expect(keyframes[keyframes.length - 1].transform).toBe("translate(0, 0)");
  });
});

describe("triggerCompletionCelebration", () => {
  it("invokes only sink when gotReward is false", async () => {
    const el = makeCardEl();
    await triggerCompletionCelebration(el, {
      oldRect: { top: 0, left: 0 },
      gotReward: false,
    });
    expect(animateSpy).toHaveBeenCalledTimes(1);
    expect(spawnParticles).not.toHaveBeenCalled();
  });

  it("invokes both sink and particle burst when gotReward is true", async () => {
    const el = makeCardEl();
    await triggerCompletionCelebration(el, {
      oldRect: { top: 0, left: 0 },
      gotReward: true,
    });
    expect(animateSpy).toHaveBeenCalledTimes(1);
    expect(spawnParticles).toHaveBeenCalledTimes(1);
  });

  it("skips animations entirely under prefers-reduced-motion", async () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });
    const el = makeCardEl();
    await triggerCompletionCelebration(el, {
      oldRect: { top: 0, left: 0 },
      gotReward: true,
    });
    expect(animateSpy).not.toHaveBeenCalled();
    expect(spawnParticles).not.toHaveBeenCalled();
  });

  it("particle rejection does not abort the sink animation wait", async () => {
    // Sink finishes after particles reject. Promise.all-without-catch would
    // reject early and Dashboard.vue's catch would open the popup before the
    // sink settled — guarded by animateBurstParticles' internal try/catch.
    let resolveSink;
    animationStub = {
      finished: new Promise((r) => { resolveSink = r; }),
      cancel: vi.fn(),
    };
    animateSpy = vi.fn(() => animationStub);
    spawnParticles.mockRejectedValueOnce(new Error("particle failure"));

    const el = makeCardEl();
    let resolved = false;
    const p = triggerCompletionCelebration(el, {
      oldRect: { top: 0, left: 0 },
      gotReward: true,
    }).then(() => { resolved = true; });

    // Let the particle rejection propagate through microtasks.
    await Promise.resolve();
    await Promise.resolve();
    expect(resolved).toBe(false);

    resolveSink();
    await p;
    expect(resolved).toBe(true);
  });
});
