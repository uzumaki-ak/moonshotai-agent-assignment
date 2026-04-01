import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// this file configures vite dev server and build
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
