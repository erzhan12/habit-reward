import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import Analytics from "../src/pages/Analytics.vue";

// Mock Chart.js and vue-chartjs
vi.mock("vue-chartjs", () => ({
  Bar: { template: '<canvas data-testid="chart" />', props: ["data", "options"] },
}));
vi.mock("chart.js", () => ({
  Chart: { register: vi.fn() },
  BarElement: {},
  CategoryScale: {},
  LinearScale: {},
  Tooltip: {},
}));

// Mock Inertia router
const { mockRouterGet } = vi.hoisted(() => ({
  mockRouterGet: vi.fn(),
}));
vi.mock("@inertiajs/vue3", () => ({
  router: { get: mockRouterGet },
}));

// Mock composables
vi.mock("../src/composables/useTheme.js", () => ({
  useTheme: () => ({
    themeConfig: {
      value: {
        classes: {
          card: { rounded: "rounded", shadow: "shadow", border: "border", bg: "bg", extra: "" },
          button: { primary: "btn-primary", secondary: "btn-secondary" },
          select: { base: "select-base" },
        },
      },
    },
  }),
}));

vi.mock("../src/composables/useThemeAnimation.js", () => ({
  useThemeAnimation: () => ({
    getCardEntranceStyle: () => ({}),
    hoverClass: "hover-class",
  }),
}));

const baseProps = {
  rates: [
    { habit_id: 1, habit_name: "Running", completion_rate: 0.8, completed_days: 24, available_days: 30 },
    { habit_id: 2, habit_name: "Reading", completion_rate: 0.6, completed_days: 18, available_days: 30 },
  ],
  rankings: [
    { rank: 1, habit_id: 1, habit_name: "Running", completion_rate: 0.8, total_completions: 24, current_streak: 5, longest_streak_in_range: 10 },
    { rank: 2, habit_id: 2, habit_name: "Reading", completion_rate: 0.6, total_completions: 18, current_streak: 3, longest_streak_in_range: 7 },
  ],
  trends: {
    daily: [{ date: "2026-03-01", completions: 2 }],
    weekly: [{ week_start: "2026-02-23", completions: 10, available_days: 14, rate: 0.71 }],
  },
  summary: {
    avgCompletionRate: 0.7,
    totalCompletions: 42,
    bestHabit: { name: "Running", rate: 0.8 },
    totalAvailableDays: 60,
  },
  currentPeriod: "30d",
};

describe("Analytics page", () => {
  beforeEach(() => {
    mockRouterGet.mockClear();
  });

  it("renders summary cards with correct values", () => {
    const wrapper = mount(Analytics, { props: baseProps });
    const text = wrapper.text();
    expect(text).toContain("70%");
    expect(text).toContain("42");
    expect(text).toContain("Running");
    expect(text).toContain("60");
  });

  it("renders completion rate bars", () => {
    const wrapper = mount(Analytics, { props: baseProps });
    const text = wrapper.text();
    expect(text).toContain("Running");
    expect(text).toContain("80%");
    expect(text).toContain("24 of 30 days");
    expect(text).toContain("Reading");
    expect(text).toContain("60%");
    expect(text).toContain("18 of 30 days");
  });

  it("renders rankings list", () => {
    const wrapper = mount(Analytics, { props: baseProps });
    const text = wrapper.text();
    expect(text).toContain("#1");
    expect(text).toContain("#2");
    expect(text).toContain("🔥 5");
    expect(text).toContain("Best: 10");
  });

  it("period buttons highlight active period", () => {
    const wrapper = mount(Analytics, { props: baseProps });
    const buttons = wrapper.findAll("button");
    const btn30d = buttons.find((b) => b.text() === "30d");
    const btn7d = buttons.find((b) => b.text() === "7d");
    expect(btn30d.classes()).toContain("btn-primary");
    expect(btn7d.classes()).toContain("btn-secondary");
  });

  it("empty state shown when no data", () => {
    const wrapper = mount(Analytics, {
      props: {
        ...baseProps,
        rates: [],
        rankings: [],
        trends: { daily: [], weekly: [] },
        summary: { avgCompletionRate: 0, totalCompletions: 0, bestHabit: null, totalAvailableDays: 0 },
      },
    });
    expect(wrapper.text()).toContain("No analytics data available");
  });

  it("clicking period button triggers navigation", async () => {
    const wrapper = mount(Analytics, { props: baseProps });
    const btn7d = wrapper.findAll("button").find((b) => b.text() === "7d");
    await btn7d.trigger("click");
    expect(mockRouterGet).toHaveBeenCalledWith("/analytics/", { period: "7d" }, { preserveScroll: true });
  });
});
