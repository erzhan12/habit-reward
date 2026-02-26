<template>
  <div class="min-h-screen bg-bg-primary flex items-center justify-center px-4">
    <div class="w-full max-w-sm text-center">
      <h1 class="text-3xl font-bold text-accent mb-2">Habit Reward</h1>
      <p class="text-text-secondary mb-8">Track habits. Earn rewards.</p>

      <div class="bg-bg-card rounded-xl p-6">
        <!-- Idle state: username input -->
        <template v-if="state === 'idle' || state === 'error'">
          <p class="text-sm text-text-secondary mb-4">Enter your Telegram username to sign in</p>

          <form @submit.prevent="submitLogin" class="space-y-4">
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">@</span>
              <input
                v-model="username"
                type="text"
                placeholder="username"
                class="w-full pl-8 pr-4 py-3 bg-bg-primary border border-border rounded-lg text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent"
                :disabled="submitting"
                autocomplete="username"
                autofocus
              />
            </div>

            <button
              type="submit"
              :disabled="!username.trim() || submitting"
              class="w-full py-3 bg-accent text-white rounded-lg font-medium transition-colors hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="submitting">Sending...</span>
              <span v-else>Send login request</span>
            </button>
          </form>

          <p v-if="error" class="mt-4 text-sm text-danger">{{ error }}</p>
        </template>

        <!-- Waiting state: polling for confirmation -->
        <template v-if="state === 'waiting'">
          <div class="flex flex-col items-center space-y-4">
            <div class="animate-spin h-8 w-8 border-2 border-accent border-t-transparent rounded-full" />
            <p class="text-text-primary font-medium">Check your Telegram</p>
            <p class="text-sm text-text-secondary">
              We sent a login confirmation to your Telegram. Tap <strong>Confirm</strong> to sign in.
            </p>
            <button
              @click="cancelLogin"
              class="text-sm text-text-secondary hover:text-text-primary underline"
            >
              Cancel
            </button>
          </div>
        </template>

        <!-- Denied state -->
        <template v-if="state === 'denied'">
          <div class="flex flex-col items-center space-y-4">
            <p class="text-danger font-medium">Login denied</p>
            <p class="text-sm text-text-secondary">The login request was rejected in Telegram.</p>
            <button
              @click="resetState"
              class="px-4 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent/90"
            >
              Try again
            </button>
          </div>
        </template>

        <!-- Expired state -->
        <template v-if="state === 'expired'">
          <div class="flex flex-col items-center space-y-4">
            <p class="text-text-secondary font-medium">Request expired</p>
            <p class="text-sm text-text-secondary">The login request timed out. Please try again.</p>
            <button
              @click="resetState"
              class="px-4 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent/90"
            >
              Try again
            </button>
          </div>
        </template>
      </div>

      <p class="text-xs text-text-secondary mt-6">
        You must use the Telegram bot first to create an account.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from "vue";
import { router } from "@inertiajs/vue3";

// No Layout wrapper for login page
defineOptions({ layout: null });

// Polling constants — must stay in sync with server's LOGIN_REQUEST_EXPIRY_MINUTES (5 min)
const POLL_INITIAL_DELAY_MS = 2000; // First poll after 2s
const POLL_BACKOFF_STEP_MS = 1000; // Add 1s per poll
const POLL_MAX_DELAY_MS = 5000; // Cap at 5s between polls
const LOGIN_EXPIRY_MS = 300_000; // 5 minutes — matches server expiry

// Must match backend regex in auth.py: ^[a-zA-Z0-9_]{3,32}$
const TELEGRAM_USERNAME_RE = /^[a-zA-Z0-9_]{3,32}$/;

const username = ref("");
const state = ref("idle"); // idle | waiting | denied | expired | error
const error = ref(null);
const submitting = ref(false);
const loginToken = ref(null);
let pollTimer = null;
let expiryTimer = null;
let pollDelay = 0;

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta || !meta.content) {
    throw new Error("CSRF token missing");
  }
  return meta.content;
}

async function submitLogin() {
  if (!username.value.trim() || submitting.value) return;

  const cleaned = username.value.trim().replace(/^@/, "");
  if (!TELEGRAM_USERNAME_RE.test(cleaned)) {
    error.value = "Invalid Telegram username (3-32 characters, letters/numbers/underscores)";
    state.value = "error";
    return;
  }

  submitting.value = true;
  error.value = null;

  try {
    const response = await fetch("/auth/bot-login/request/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ username: cleaned }),
    });

    if (response.status === 429) {
      error.value = "Too many attempts. Please wait a moment and try again.";
      state.value = "error";
      submitting.value = false;
      return;
    }

    const data = await response.json();

    if (response.status >= 500) {
      error.value = "Server error. Please try again later.";
      state.value = "error";
      submitting.value = false;
      return;
    }

    if (!response.ok) {
      error.value = data.error || "Request failed";
      state.value = "error";
      submitting.value = false;
      return;
    }

    loginToken.value = data.token;
    state.value = "waiting";
    submitting.value = false;
    startPolling();
  } catch {
    error.value = "Network error. Please try again.";
    state.value = "error";
    submitting.value = false;
  }
}

function startPolling() {
  stopPolling();
  pollDelay = POLL_INITIAL_DELAY_MS;

  function schedulePoll() {
    pollTimer = setTimeout(async () => {
      await pollStatus();
      if (state.value === "waiting") {
        pollDelay = Math.min(pollDelay + POLL_BACKOFF_STEP_MS, POLL_MAX_DELAY_MS);
        schedulePoll();
      }
    }, pollDelay);
  }

  schedulePoll();

  expiryTimer = setTimeout(() => {
    stopPolling();
    state.value = "expired";
  }, LOGIN_EXPIRY_MS);
}

function stopPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  if (expiryTimer) {
    clearTimeout(expiryTimer);
    expiryTimer = null;
  }
}

async function pollStatus() {
  if (!loginToken.value) return;

  try {
    const response = await fetch(`/auth/bot-login/status/${loginToken.value}/`);
    const data = await response.json();

    if (data.status === "confirmed") {
      stopPolling();
      await completeLogin();
    } else if (data.status === "denied") {
      stopPolling();
      state.value = "denied";
    } else if (data.status === "expired" || data.status === "not_found") {
      stopPolling();
      state.value = "expired";
    } else if (data.status === "used") {
      // Login completed in another tab — session already exists
      stopPolling();
      router.visit("/");
    }
    // 'pending' — keep polling
  } catch {
    // Network error during poll — back off to max delay before retrying
    pollDelay = POLL_MAX_DELAY_MS;
  }
}

async function completeLogin() {
  try {
    const response = await fetch("/auth/bot-login/complete/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ token: loginToken.value }),
    });

    if (response.status === 429) {
      error.value = "Too many attempts. Please wait a moment and try again.";
      state.value = "error";
      return;
    }

    const data = await response.json();

    if (response.ok && data.success) {
      router.visit(data.redirect || "/");
    } else if (response.status >= 500) {
      error.value = "Server error. Please try again later.";
      state.value = "error";
    } else {
      error.value = data.error || "Login failed";
      state.value = "error";
    }
  } catch {
    error.value = "Network error during login. Please try again.";
    state.value = "error";
  }
}

function cancelLogin() {
  stopPolling();
  resetState();
}

function resetState() {
  state.value = "idle";
  error.value = null;
  loginToken.value = null;
  submitting.value = false;
}

onUnmounted(() => {
  stopPolling();
});
</script>
