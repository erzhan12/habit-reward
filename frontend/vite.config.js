import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  root: resolve("./"),
  base: "/static/",
  server: {
    host: "localhost",
    port: 5173,
    open: false,
    watch: {
      usePolling: true,
      disableGlobbing: false,
    },
  },
  resolve: {
    extensions: [".js", ".vue", ".json"],
  },
  test: {
    environment: "jsdom",
  },
  build: {
    outDir: resolve("./dist"),
    assetsDir: "",
    manifest: "manifest.json",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve("./src/main.js"),
      },
    },
  },
});
