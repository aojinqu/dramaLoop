import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            const contentType = String(proxyRes.headers["content-type"] ?? "");
            if (contentType.indexOf("text/event-stream") !== -1) {
              proxyRes.headers["cache-control"] = "no-cache";
              proxyRes.headers["x-accel-buffering"] = "no";
              // Avoid proxy compression buffering for SSE.
              delete proxyRes.headers["content-encoding"];
              delete proxyRes.headers["content-length"];
            }
          });
        },
      },
      "/health": "http://127.0.0.1:8000",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
