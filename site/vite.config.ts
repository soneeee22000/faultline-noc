import { defineConfig } from "vite";

const PREVIEW_PORT = 4173;

export default defineConfig({
  base: "/",
  server: {
    fs: {
      allow: [".."],
    },
  },
  preview: {
    port: PREVIEW_PORT,
    strictPort: true,
  },
  build: {
    target: "es2022",
    sourcemap: false,
  },
});
