import { describe, expect, it } from "vitest";
import { dayCompletions } from "../src/utils/dayCompletions.js";

const habits = [
  { id: 1, name: "Run" },
  { id: 2, name: "Read" },
  { id: 3, name: "Journal" },
];

const completions = {
  1: ["2026-11-20", "2026-11-21"],
  2: ["2026-11-21"],
  3: ["2026-11-19"],
  9: ["2026-11-21"], // habit no longer active
};

describe("dayCompletions", () => {
  it("counts every completion and names the active habits in order", () => {
    expect(dayCompletions(completions, habits, "2026-11-21")).toEqual({
      count: 3,
      names: ["Run", "Read"],
      otherCount: 1,
    });
  });

  it("matches string keys against numeric habit ids", () => {
    const result = dayCompletions({ "3": ["2026-11-19"] }, habits, "2026-11-19");
    expect(result.names).toEqual(["Journal"]);
  });

  it("handles a day with nothing done", () => {
    expect(dayCompletions(completions, habits, "2026-11-01")).toEqual({ count: 0, names: [], otherCount: 0 });
  });

  it("tolerates missing inputs", () => {
    expect(dayCompletions(null, null, "2026-11-01")).toEqual({ count: 0, names: [], otherCount: 0 });
  });
});
