<template>
  <div class="min-h-screen bg-bg-primary flex items-center justify-center px-4">
    <div class="w-full max-w-sm text-center">
      <h1 class="text-3xl font-bold text-accent mb-2">Habit Reward</h1>
      <p class="text-text-secondary mb-8">Track habits. Earn rewards.</p>

      <div class="bg-bg-card rounded-xl p-6">
        <p class="text-sm text-text-secondary mb-6">Sign in with your Telegram account</p>

        <!-- Telegram Login Widget container -->
        <div ref="telegramWidget" class="flex justify-center" />

        <p v-if="error" class="mt-4 text-sm text-danger">{{ error }}</p>
      </div>

      <p class="text-xs text-text-secondary mt-6">
        You must use the Telegram bot first to create an account.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { router } from "@inertiajs/vue3";

// No Layout wrapper for login page
defineOptions({ layout: null });

const props = defineProps({
  telegramBotUsername: { type: String, required: true },
});

const telegramWidget = ref(null);
const error = ref(null);

// Global callback for Telegram widget
window.onTelegramAuth = async (user) => {
  error.value = null;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch("/auth/telegram/callback/", {
      signal: controller.signal,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(user),
    });
    clearTimeout(timeoutId);

    const data = await response.json();

    if (response.ok && data.success) {
      router.visit(data.redirect || "/");
    } else {
      error.value = data.error || "Authentication failed";
    }
  } catch (e) {
    clearTimeout(timeoutId);
    if (e.name === "AbortError") {
      error.value = "Request timed out. Please try again.";
    } else if (e.message === "CSRF token missing") {
      error.value = "Page configuration error. Please refresh.";
    } else {
      error.value = "Network error. Please try again.";
    }
  }
};

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta || !meta.content) {
    console.error("CSRF token not found in page meta tags");
    throw new Error("CSRF token missing");
  }
  return meta.content;
}

onMounted(() => {
  if (!props.telegramBotUsername) {
    error.value = "Telegram bot not configured";
    return;
  }

  const WIDGET_URL = "https://telegram.org/js/telegram-widget.js?22";
  const WIDGET_SRI = "sha384-I+W8gJkm5OWQibtRzgVIojXtlJek6sKioAqefhZ4f0SodL9LyEGvj4zjPPFhStA0";

  function appendWidgetScript(useIntegrity) {
    const script = document.createElement("script");
    script.src = WIDGET_URL;
    if (useIntegrity) {
      script.integrity = WIDGET_SRI;
      script.crossOrigin = "anonymous";
    }
    script.setAttribute("data-telegram-login", props.telegramBotUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "8");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    script.async = true;
    script.onerror = () => {
      if (useIntegrity) {
        console.warn(
          "[Login] Telegram widget SRI check failed; retrying without SRI. Update frontend hash: ./scripts/verify_telegram_widget_sri.sh --print"
        );
        if (telegramWidget.value) telegramWidget.value.innerHTML = "";
        appendWidgetScript(false);
      } else {
        error.value = "Failed to load Telegram widget. Please refresh the page.";
      }
    };
    if (telegramWidget.value) {
      telegramWidget.value.appendChild(script);
    }
  }

  appendWidgetScript(true);
});
</script>
