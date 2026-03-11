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

const VISIBILITY_DEBOUNCE_MS = 500;

export function useDayChange() {
  let lastKnownDate = null;
  let midnightTimer = null;
  let unmounted = false;
  let visibilityDebounceTimer = null;

  function scheduleMidnightTimer() {
    if (unmounted) return;
    clearTimeout(midnightTimer);
    const now = new Date();
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const msUntilMidnight = tomorrow - now + MIDNIGHT_BUFFER_MS;
    midnightTimer = setTimeout(onDayChange, msUntilMidnight);
  }

  function onDayChange() {
    if (unmounted) return;
    lastKnownDate = today();
    try {
      router.reload();
    } catch (err) {
      console.error("useDayChange: reload failed on midnight timer", err);
    }
    scheduleMidnightTimer();
  }

  function onVisibilityChange() {
    if (unmounted) return;
    if (document.visibilityState !== "visible") return;
    clearTimeout(visibilityDebounceTimer);
    visibilityDebounceTimer = setTimeout(checkDayChange, VISIBILITY_DEBOUNCE_MS);
  }

  function checkDayChange() {
    if (unmounted) return;
    const current = today();
    if (current === lastKnownDate) return;
    lastKnownDate = current;
    try {
      router.reload();
    } catch (err) {
      console.error("useDayChange: reload failed on visibility change", err);
    }
    scheduleMidnightTimer();
  }

  function setup() {
    lastKnownDate = today();
    scheduleMidnightTimer();
    document.addEventListener("visibilitychange", onVisibilityChange);
  }

  function cleanup() {
    unmounted = true;
    clearTimeout(midnightTimer);
    midnightTimer = null;
    clearTimeout(visibilityDebounceTimer);
    visibilityDebounceTimer = null;
    document.removeEventListener("visibilitychange", onVisibilityChange);
  }

  onMounted(setup);
  onUnmounted(cleanup);
}
