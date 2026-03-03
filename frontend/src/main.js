import { createApp, h } from "vue";
import { createInertiaApp, router } from "@inertiajs/vue3";
import Layout from "./components/Layout.vue";
import { getTheme, defaultTheme } from "./themes/index.js";
import "./app.css";

// Apply theme CSS variables immediately before Vue hydrates to avoid FOUC.
// The server-rendered HTML has no inline styles, so we read the data-theme
// attribute (if set by a prior page load) or fall back to the default.
(function applyInitialTheme() {
  const savedId = document.documentElement.getAttribute("data-theme") || defaultTheme;
  const config = getTheme(savedId);
  for (const [prop, value] of Object.entries(config.cssVars)) {
    document.documentElement.style.setProperty(prop, value);
  }
})();

// Inject Django CSRF token into every Inertia request
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

router.on("before", (event) => {
  const token = getCookie("csrftoken");
  if (token) {
    event.detail.visit.headers["X-CSRFToken"] = token;
  }
});

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob("./pages/**/*.vue", { eager: true });
    const page = pages[`./pages/${name}.vue`];
    if (!page) {
      throw new Error(`Page not found: ${name}`);
    }
    page.default.layout = page.default.layout || Layout;
    return page;
  },
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el);
  },
});
