import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
const PRODUCT_API_PROXY_TARGET = (process.env.VITE_PRODUCT_API_BASE_URL || "http://127.0.0.1:8011").replace(/\/$/, "");

export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: PRODUCT_API_PROXY_TARGET,
        changeOrigin: true,
      },
    },
    host: "::",
    port: 8080,
    hmr: {
      overlay: false,
    },
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime", "@tanstack/react-query", "@tanstack/query-core"],
  },
});
