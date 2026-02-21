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
  try {
    const response = await fetch("/auth/telegram/callback/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(user),
    });

    const data = await response.json();

    if (response.ok && data.success) {
      router.visit(data.redirect || "/");
    } else {
      error.value = data.error || "Authentication failed";
    }
  } catch (e) {
    error.value = "Network error. Please try again.";
  }
};

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.content : "";
}

onMounted(() => {
  if (!props.telegramBotUsername) {
    error.value = "Telegram bot not configured";
    return;
  }

  // Load Telegram widget script
  const script = document.createElement("script");
  script.src = "https://telegram.org/js/telegram-widget.js?22";
  script.setAttribute("data-telegram-login", props.telegramBotUsername);
  script.setAttribute("data-size", "large");
  script.setAttribute("data-radius", "8");
  script.setAttribute("data-onauth", "onTelegramAuth(user)");
  script.setAttribute("data-request-access", "write");
  script.async = true;

  if (telegramWidget.value) {
    telegramWidget.value.appendChild(script);
  }
});
</script>
