<template>
  <!-- `contents`: the chip sits in the parent's flex meta row; the hint
       (basis-full) wraps onto its own full-width line under that row. -->
  <div class="contents">
    <button
      type="button"
      class="relative inline-flex items-center shrink-0 cursor-pointer before:absolute before:-inset-x-1 before:-inset-y-1.5 before:content-['']"
      :class="chipClass"
      :aria-expanded="open"
      :aria-controls="hintId"
      data-testid="odds-chip"
      @click.stop="open = !open"
      @pointerdown.stop
      @touchstart.stop
      @touchmove.stop
      @touchend.stop
    >
      {{ label }}
    </button>

    <div
      v-if="open"
      :id="hintId"
      class="basis-full w-full flex flex-col items-start gap-1 mt-1 text-xs text-text-secondary"
      data-testid="odds-hint"
    >
      <svg
        v-if="points"
        class="w-28 h-7 shrink-0 text-accent"
        viewBox="0 0 120 32"
        fill="none"
        aria-hidden="true"
      >
        <polyline :points="points" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" opacity="0.5" />
        <circle :cx="dot.x" :cy="dot.y" r="3" fill="currentColor" />
      </svg>
      <p class="leading-snug">{{ hint }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, useId } from "vue";

const props = defineProps({
  rewardChance: { type: Number, required: true },
  completed: { type: Boolean, default: false },
  nextStreak: { type: Number, default: 1 },
  // { curve: [day1 %, day2 %, ...], cap } from the dashboard view, or null
  chance: { type: Object, default: null },
  oddsStyle: { type: String, default: "badge" },
  badgeClass: { type: String, default: "" },
});

const open = ref(false);
const hintId = useId();

// Static class strings per style (Tailwind cannot see composed class names).
const STYLE_CLASSES = {
  badge: "text-xs px-1.5 py-0.5",
  chip: "text-xs font-semibold px-2 py-0.5 rounded-full border",
  stub: "odds-stub text-[11px] font-medium px-1.5 py-0.5 rounded-sm border border-dashed",
  drop: "odds-mono text-xs",
};

const STATE_CLASSES = {
  badge: { open: "", done: "" },
  chip: { open: "border-accent/60 text-accent", done: "border-border text-text-secondary" },
  stub: { open: "border-accent text-text-primary", done: "border-border text-text-secondary" },
  drop: { open: "text-accent", done: "text-text-secondary" },
};

const style = computed(() => (STYLE_CLASSES[props.oddsStyle] ? props.oddsStyle : "badge"));

const chipClass = computed(() => [
  STYLE_CLASSES[style.value],
  STATE_CLASSES[style.value][props.completed ? "done" : "open"],
  style.value === "badge" ? props.badgeClass : "",
]);

const label = computed(() => {
  if (props.completed) return `rolled at ${props.rewardChance}%`;
  if (style.value === "stub") return `ODDS ${props.rewardChance}%`;
  if (style.value === "drop") return `drop: ${props.rewardChance}%`;
  return `🎲 ${props.rewardChance}% next`;
});

const curve = computed(() => (Array.isArray(props.chance?.curve) ? props.chance.curve : []));

// Chance on streak day `day`, clamping days past the end of the curve.
function chanceOn(day) {
  const c = curve.value;
  return c[Math.min(Math.max(day, 1), c.length) - 1];
}

const hint = computed(() => {
  if (!curve.value.length) {
    return "Your chance grows with your streak and starts over if the streak breaks.";
  }
  const next = chanceOn(props.nextStreak);
  const restart = `If the streak breaks, it starts again at ${curve.value[0]}%.`;
  if (props.completed) {
    return `Today's roll was at ${props.rewardChance}%. Next completion ${next}%.`;
  }
  const cap = props.chance.cap;
  if (next >= cap) {
    return `You're at the top: ${cap}% on every completion while the streak holds. ${restart}`;
  }
  const after = chanceOn(props.nextStreak + 1);
  return `Next completion ${next}%, the one after ${after}%. Levels off near ${cap}%. ${restart}`;
});

const W = 120;
const H = 32;
const PAD = 3;

function toPoint(index, value) {
  const c = curve.value;
  const min = c[0];
  const max = Math.max(props.chance?.cap ?? c[c.length - 1], min + 1);
  const x = PAD + (index / Math.max(c.length - 1, 1)) * (W - 2 * PAD);
  const y = H - PAD - ((value - min) / (max - min)) * (H - 2 * PAD);
  return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10 };
}

const points = computed(() => {
  if (curve.value.length < 2) return "";
  return curve.value.map((v, i) => {
    const p = toPoint(i, v);
    return `${p.x},${p.y}`;
  }).join(" ");
});

const dot = computed(() => {
  const c = curve.value;
  const index = Math.min(Math.max(props.nextStreak, 1), c.length) - 1;
  return toPoint(index, c[index]);
});
</script>

<style scoped>
/* Explicit families: the theme fonts load IBM Plex Mono for ticket_stub /
   quest_log, but no --font-mono token points at it. */
.odds-stub {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  letter-spacing: 0.04em;
}
.odds-mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
</style>
