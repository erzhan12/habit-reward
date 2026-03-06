/**
 * WebSocket composable for real-time dashboard updates.
 *
 * Connects to /ws/updates/, listens for "dashboard_update" messages,
 * and calls Inertia router.reload() to silently refresh page props.
 * Auto-reconnects with exponential backoff on disconnection.
 */
import { ref, onMounted, onUnmounted } from "vue";
import { router } from "@inertiajs/vue3";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 16000;
// Server close codes that mean "don't reconnect"
const TERMINAL_CLOSE_CODES = new Set([4401, 1008]);

export function useRealtimeSync() {
  const isConnected = ref(false);

  let ws = null;
  let reconnectTimer = null;
  let reconnectDelay = RECONNECT_BASE_MS;
  let unmounted = false;

  function getWsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}/ws/updates/`;
  }

  function connect() {
    if (unmounted) return;

    try {
      ws = new WebSocket(getWsUrl());
    } catch {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      isConnected.value = true;
      reconnectDelay = RECONNECT_BASE_MS;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          return;
        }
        if (data.type === "dashboard_update") {
          router.reload();
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = (event) => {
      isConnected.value = false;
      ws = null;
      if (!TERMINAL_CLOSE_CODES.has(event.code)) {
        scheduleReconnect();
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror, which handles reconnect
    };
  }

  function scheduleReconnect() {
    if (unmounted || reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
      connect();
    }, reconnectDelay);
  }

  function cleanup() {
    unmounted = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws) {
      ws.onclose = null; // Prevent reconnect on intentional close
      ws.close();
      ws = null;
    }
    isConnected.value = false;
  }

  onMounted(connect);
  onUnmounted(cleanup);

  return { isConnected };
}
