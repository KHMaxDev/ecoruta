import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Puerto del backend EcoRuta (evita el 8000, que suele ocupar `php artisan serve`).
const apiTarget = process.env.VITE_API_TARGET ?? "http://localhost:8010";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true }
    }
  },
  preview: {
    port: 4173,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true }
    }
  },
  build: {
    outDir: "dist",
    sourcemap: true
  }
});
