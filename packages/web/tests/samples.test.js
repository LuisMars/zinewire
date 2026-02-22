import { describe, it, expect } from "vitest";
import { samples } from "../src/samples.js";

describe("samples", () => {
  it("has at least 3 samples", () => {
    expect(samples.length).toBeGreaterThanOrEqual(3);
  });

  it("each sample has required fields", () => {
    for (const sample of samples) {
      expect(sample).toHaveProperty("name");
      expect(sample).toHaveProperty("markdown");
      expect(typeof sample.name).toBe("string");
      expect(typeof sample.markdown).toBe("string");
      expect(sample.name.length).toBeGreaterThan(0);
      expect(sample.markdown.length).toBeGreaterThan(0);
    }
  });

  it("each sample has unique name", () => {
    const names = samples.map((s) => s.name);
    expect(new Set(names).size).toBe(names.length);
  });

  it("markdown contains zinewire directives", () => {
    // At least some samples should use zinewire directives
    const allMarkdown = samples.map((s) => s.markdown).join("\n");
    expect(allMarkdown).toContain("/page");
    expect(allMarkdown).toContain("/title");
  });

  it("config strings are valid (empty or contain TOML sections)", () => {
    for (const sample of samples) {
      if (sample.config && sample.config.trim()) {
        // Should contain a TOML section header
        expect(sample.config).toMatch(/\[.+\]/);
      }
    }
  });

  it("Poetry Chapbook has custom font config", () => {
    const poetry = samples.find((s) => s.name === "Poetry Chapbook");
    expect(poetry).toBeDefined();
    expect(poetry.config).toContain("font-heading");
  });

  it("Recipe Zine has accent color", () => {
    const recipe = samples.find((s) => s.name === "Recipe Zine");
    expect(recipe).toBeDefined();
    expect(recipe.config).toContain("color-accent");
  });
});
