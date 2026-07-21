import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Local dev only (npm run dev) — proxies API calls so you
    // don't need Nginx running during development.
    proxy: {
      "/auth":   "http://localhost:8001",
      "/tickets": "http://localhost:8002",
      "/assign": "http://localhost:8003",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,   // disable in production to reduce bundle size
  },
});
