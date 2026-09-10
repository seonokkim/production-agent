import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Ports are intentional: sibling repo production-agent-dev uses 5173→8000.
  // This repo (prod-agent-dev) always uses 5174→8001 so browsers never mix them.
  server: {
    host: "0.0.0.0",
    port: 5174,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      "/api": "http://127.0.0.1:8001",
      "/storage": "http://127.0.0.1:8001",
    },
  },
});
