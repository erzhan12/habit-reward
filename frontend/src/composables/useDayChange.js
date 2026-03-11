/**
 * Composable that detects day boundaries and triggers a silent page reload.
 *
 * Two triggers:
 * 1. Midnight timer — setTimeout until local midnight + 1s buffer
 * 2. Tab focus — visibilitychange listener checks if date changed while hidden
 *
 * Uses browser local time for detection; the backend resolves the
 * authoritative "today" from the user's stored timezone on each request.
 */
import { onMounted, onUnmounted } from "vue";
import { router } from "@inertiajs/vue3";

const MIDNIGHT_BUFFER_MS = 1000;

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function useDayChange() {
  let lastKnownDate = null;
  let midnightTimer = null;

  function scheduleMidnightTimer() {
    clearTimeout(midnightTimer);
    const now = new Date();
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const msUntilMidnight = tomorrow - now + MIDNIGHT_BUFFER_MS;
    midnightTimer = setTimeout(onDayChange, msUntilMidnight);
  }

  function onDayChange() {
    lastKnownDate = today();
    router.reload();
    scheduleMidnightTimer();
  }

  function onVisibilityChange() {
    if (document.visibilityState !== "visible") return;
    const current = today();
    if (current === lastKnownDate) return;
    lastKnownDate = current;
    router.reload();
    scheduleMidnightTimer();
  }

  function setup() {
    lastKnownDate = today();
    scheduleMidnightTimer();
    document.addEventListener("visibilitychange", onVisibilityChange);
  }

  function cleanup() {
    clearTimeout(midnightTimer);
    midnightTimer = null;
    document.removeEventListener("visibilitychange", onVisibilityChange);
  }

  onMounted(setup);
  onUnmounted(cleanup);
}
