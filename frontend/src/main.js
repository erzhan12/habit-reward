import { createApp, h } from "vue";
import { createInertiaApp, router } from "@inertiajs/vue3";
import Layout from "./components/Layout.vue";
import "./app.css";

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
