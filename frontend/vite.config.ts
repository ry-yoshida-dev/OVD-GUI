import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backend = process.env.OVD_GUI_BACKEND ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../src/ovd_gui/web/static",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1024,
  },
  server: {
    proxy: {
      "/api": { target: backend, ws: true },
    },
  },
});
