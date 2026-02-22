import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  root: resolve(__dirname),
  resolve: {
    alias: {
      "@zinewire/core": resolve(__dirname, "../core/src"),
    },
  },
  build: {
    outDir: "dist",
  },
  server: {
    port: 3000,
  },
});
