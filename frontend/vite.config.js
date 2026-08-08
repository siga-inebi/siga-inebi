import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendProxyTarget =
    env.VITE_BACKEND_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        // changeOrigin is off on purpose: Django builds absolute media URLs
        // (e.g. student photos) from the inbound Host header. Rewriting it to
        // the backend's own docker-internal host would bake an unreachable
        // hostname into those URLs; keeping the original Host (as seen by the
        // browser) means the URLs it gets back are ones it can actually load.
        "/api": {
          target: backendProxyTarget,
          changeOrigin: false,
        },
        "/media": {
          target: backendProxyTarget,
          changeOrigin: false,
        },
      },
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: "./src/test/setup.js",
      coverage: {
        provider: "v8",
        reporter: ["text", "json", "html"],
        include: ["src/**/*.{js,jsx}"],
        exclude: ["src/main.jsx", "src/styles.css"],
        thresholds: {
          lines: 60,
          functions: 60,
          branches: 50,
          statements: 60,
        },
      },
    },
  };
});
