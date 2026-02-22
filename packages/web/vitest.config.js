import { defineConfig } from "vitest/config";
import { resolve } from "path";

export default defineConfig({
  resolve: {
    alias: {
      "@zinewire/core": resolve(__dirname, "../core/src"),
    },
  },
  test: {
    environment: "jsdom",
  },
});
