import { describe, it, expect, vi, beforeEach } from "vitest";

// vi.mock is hoisted — factory must be self-contained (no outer variables)
vi.mock("@zinewire/core/sources.js", async () => {
  const fs = await import("fs");
  const path = await import("path");
  const html = fs.readFileSync(
    path.resolve(__dirname, "../../../src/zinewire/config-form.html"),
    "utf-8"
  );
  return { configFormHtml: html };
});

import {
  getConfigFormHTML,
  populateForm,
  collectForm,
  configToToml,
} from "../src/config-panel.js";

describe("getConfigFormHTML", () => {
  it("replaces PAGE_SIZE_OPTIONS placeholder with actual options", () => {
    const html = getConfigFormHTML();
    expect(html).toContain('<option value="a5">a5</option>');
    expect(html).toContain('<option value="a4">a4</option>');
    expect(html).toContain('<option value="letter">letter</option>');
    expect(html).not.toContain("<!-- PAGE_SIZE_OPTIONS -->");
  });

  it("filters out landscape page sizes", () => {
    const html = getConfigFormHTML();
    expect(html).not.toContain("a4-landscape");
    expect(html).not.toContain("a5-landscape");
  });

  it("keeps the custom option", () => {
    const html = getConfigFormHTML();
    expect(html).toContain('<option value="custom">Custom...</option>');
  });

  it("contains orientation radio buttons", () => {
    const html = getConfigFormHTML();
    expect(html).toContain('name="orientation"');
    expect(html).toContain('value="portrait"');
    expect(html).toContain('value="landscape"');
  });

  it("contains imposition select", () => {
    const html = getConfigFormHTML();
    expect(html).toContain('data-f="imposition"');
    expect(html).toContain('value="booklet"');
    expect(html).toContain('value="trifold"');
  });

  it("contains font dropdowns with optgroups", () => {
    const html = getConfigFormHTML();
    expect(html).toContain("font-sel");
    expect(html).toContain("__custom");
    expect(html).toContain("<optgroup");
  });
});

describe("populateForm / collectForm round-trip", () => {
  let form;

  beforeEach(() => {
    const container = document.createElement("div");
    container.innerHTML = getConfigFormHTML();
    form = container.querySelector("form");
    document.body.innerHTML = "";
    document.body.appendChild(container);
  });

  it("populates defaults when given empty config", () => {
    populateForm(form, {});
    const titleInput = form.querySelector('input[data-f="title"]');
    expect(titleInput.value).toBe("Untitled Zine");
  });

  it("populates custom values", () => {
    populateForm(form, { title: "My Zine", font_heading: "Inter" });
    expect(form.querySelector('input[data-f="title"]').value).toBe("My Zine");
    // Inter is a preset font, should be selected in dropdown
    expect(form.querySelector('select[data-f="font_heading"]').value).toBe("Inter");
  });

  it("handles custom font not in presets", () => {
    populateForm(form, { font_heading: "Comic Sans MS" });
    const sel = form.querySelector('select[data-f="font_heading"]');
    expect(sel.value).toBe("__custom");
    const ci = sel.closest(".font-row").querySelector(".font-custom");
    expect(ci.value).toBe("Comic Sans MS");
    expect(ci.style.display).toBe("");
  });

  it("sets page size select", () => {
    populateForm(form, { page_size: "a4" });
    const sel = form.querySelector('select[name="page_size"]');
    expect(sel.value).toBe("a4");
  });

  it("handles landscape page size", () => {
    populateForm(form, { page_size: "a4-landscape" });
    const sel = form.querySelector('select[name="page_size"]');
    expect(sel.value).toBe("a4");
    const orient = form.querySelector('input[name="orientation"][value="landscape"]');
    expect(orient.checked).toBe(true);
  });

  it("handles custom page size", () => {
    populateForm(form, { page_size: "120x170mm" });
    const sel = form.querySelector('select[name="page_size"]');
    expect(sel.value).toBe("custom");
    expect(form.querySelector('input[name="page_size_custom"]').value).toBe("120x170mm");
  });

  it("sets imposition from booklet boolean", () => {
    populateForm(form, { booklet: true });
    expect(form.querySelector('[data-f="imposition"]').value).toBe("booklet");
  });

  it("sets imposition from trifold boolean", () => {
    populateForm(form, { trifold: true });
    expect(form.querySelector('[data-f="imposition"]').value).toBe("trifold");
  });

  it("defaults imposition to none", () => {
    populateForm(form, {});
    expect(form.querySelector('[data-f="imposition"]').value).toBe("none");
  });

  it("sets column range", () => {
    populateForm(form, { default_columns: 3 });
    const rng = form.querySelector('input[name="default_columns"]');
    expect(rng.value).toBe("3");
  });

  it("parses size values into number + unit", () => {
    populateForm(form, { margin_vertical: "15mm" });
    const si = form.querySelector('input[data-f="margin_vertical"]');
    expect(si.value).toBe("15");
    const unit = si.closest(".size-input").querySelector("select");
    expect(unit.value).toBe("mm");
  });

  it("round-trips config through populate and collect", () => {
    const config = {
      title: "Test Zine",
      page_size: "a6",
      default_columns: 3,
      font_heading: "Inter",
      color_text: "#222222",
      margin_vertical: "12mm",
    };

    populateForm(form, config);
    const collected = collectForm(form);

    expect(collected.title).toBe("Test Zine");
    expect(collected.page_size).toBe("a6");
    expect(collected.default_columns).toBe(3);
    expect(collected.font_heading).toBe("Inter");
    expect(collected.color_text).toBe("#222222");
    expect(collected.margin_vertical).toBe("12mm");
  });

  it("collects landscape orientation into page_size suffix", () => {
    populateForm(form, { page_size: "a5" });
    form.querySelector('input[name="orientation"][value="landscape"]').checked = true;
    const collected = collectForm(form);
    expect(collected.page_size).toBe("a5-landscape");
  });
});

describe("collectForm", () => {
  let form;

  beforeEach(() => {
    const container = document.createElement("div");
    container.innerHTML = getConfigFormHTML();
    form = container.querySelector("form");
    document.body.innerHTML = "";
    document.body.appendChild(container);
    populateForm(form, {});
  });

  it("collects all text inputs with data-f", () => {
    const collected = collectForm(form);
    expect(collected).toHaveProperty("title");
    expect(collected).toHaveProperty("margin_vertical");
  });

  it("collects default_columns as integer", () => {
    const collected = collectForm(form);
    expect(typeof collected.default_columns).toBe("number");
    expect(Number.isInteger(collected.default_columns)).toBe(true);
  });

  it("collects imposition as boolean fields", () => {
    form.querySelector('[data-f="imposition"]').value = "booklet";
    const collected = collectForm(form);
    expect(collected.booklet).toBe(true);
    expect(collected.mini_zine).toBe(false);
    expect(collected.trifold).toBe(false);
    expect(collected.french_fold).toBe(false);
    expect(collected.micro_mini).toBe(false);
  });

  it("collects custom page size when selected", () => {
    const sel = form.querySelector('select[name="page_size"]');
    sel.value = "custom";
    form.querySelector('input[name="page_size_custom"]').value = "100x150mm";
    const collected = collectForm(form);
    expect(collected.page_size).toBe("100x150mm");
  });

  it("collects size inputs as combined value+unit", () => {
    const inp = form.querySelector('input[data-f="margin_vertical"]');
    inp.value = "15";
    inp.closest(".size-input").querySelector("select").value = "mm";
    const collected = collectForm(form);
    expect(collected.margin_vertical).toBe("15mm");
  });

  it("collects font select with custom value", () => {
    const sel = form.querySelector('select[data-f="font_heading"]');
    sel.value = "__custom";
    const ci = sel.closest(".font-row").querySelector(".font-custom");
    ci.value = "Comic Sans MS";
    const collected = collectForm(form);
    expect(collected.font_heading).toBe("Comic Sans MS");
  });
});

describe("configToToml", () => {
  it("returns empty string for all-default values", () => {
    const toml = configToToml({
      title: "Untitled Zine",
      page_size: "a4",  // a4 is the default
      default_columns: 2,
      font_heading: "Montserrat",
      font_body: "PT Serif",
      font_mono: "Ubuntu Mono",
      color_text: "#1a1a1a",
      margin_vertical: "10mm",
      margin_horizontal: "8mm",
      margin_spine: "12mm",
    });
    expect(toml.trim()).toBe("");
  });

  it("generates [zine] section for non-default title", () => {
    const toml = configToToml({ title: "My Zine" });
    expect(toml).toContain("[zine]");
    expect(toml).toContain('title = "My Zine"');
  });

  it("generates [zine] section for non-default page size", () => {
    const toml = configToToml({ page_size: "letter" });
    expect(toml).toContain("[zine]");
    expect(toml).toContain('page-size = "letter"');
  });

  it("generates boolean values without quotes", () => {
    const toml = configToToml({ booklet: true });
    expect(toml).toContain("booklet = true");
    expect(toml).not.toContain('"true"');
  });

  it("omits false boolean imposition values", () => {
    const toml = configToToml({ booklet: false, mini_zine: false });
    expect(toml).not.toContain("booklet");
    expect(toml).not.toContain("mini-zine");
  });

  it("generates [theme] section for non-default fonts", () => {
    const toml = configToToml({ font_heading: "Inter" });
    expect(toml).toContain("[theme]");
    expect(toml).toContain('font-heading = "Inter"');
  });

  it("generates [theme] section for non-default colors", () => {
    const toml = configToToml({ color_accent: "#ff0000" });
    expect(toml).toContain("[theme]");
    expect(toml).toContain('color-accent = "#ff0000"');
  });

  it("generates [margins] section for non-default margins", () => {
    const toml = configToToml({ margin_vertical: "15mm" });
    expect(toml).toContain("[margins]");
    expect(toml).toContain('vertical = "15mm"');
  });

  it("converts underscores to hyphens in TOML keys", () => {
    const toml = configToToml({
      font_size_body: "10pt",
      color_bg_muted: "#eee",
    });
    expect(toml).toContain("font-size-body");
    expect(toml).toContain("color-bg-muted");
  });

  it("omits empty string values", () => {
    const toml = configToToml({ version: "", font_size_h1: "" });
    expect(toml).not.toContain("version");
    expect(toml).not.toContain("font-size-h1");
  });

  it("generates multiple sections", () => {
    const toml = configToToml({
      title: "Test",
      font_heading: "Arial",
      margin_vertical: "5mm",
    });
    expect(toml).toContain("[zine]");
    expect(toml).toContain("[theme]");
    expect(toml).toContain("[margins]");
  });

  it("includes imposition booleans like trifold", () => {
    const toml = configToToml({ trifold: true });
    expect(toml).toContain("[zine]");
    expect(toml).toContain("trifold = true");
  });
});
