/**
 * Config panel — form-based config editor.
 * Uses the shared config-form.html (single source of truth with the dev server).
 * The form HTML is bundled into sources.js by bundle-sources.cjs.
 */

import { configFormHtml, configFormCss } from "@zinewire/core/sources.js";

const PAGE_SIZES = [
  "a4", "a5", "a6", "a7",
  "letter", "half-letter", "quarter-letter", "eighth-letter",
  "digest",
];

const DEFAULTS = {
  title: "Untitled Zine",
  page_size: "a4",
  default_columns: 2,
  version: "",
  imposition: "none",
  font_heading: "Montserrat",
  font_body: "PT Serif",
  font_mono: "Ubuntu Mono",
  font_size_body: "",
  font_size_h1: "",
  font_size_h2: "",
  font_size_h3: "",
  font_size_h4: "",
  color_text: "#1a1a1a",
  color_border: "#333",
  color_bg_muted: "#f5f5f5",
  color_text_muted: "#666",
  color_table_header_bg: "#000",
  color_table_header_text: "#fff",
  color_accent: "#2563EB",
  page_number_color: "",
  page_number_size: "",
  page_number_font: "",
  column_justify: "",
  margin_vertical: "10mm",
  margin_horizontal: "8mm",
  margin_spine: "12mm",
  custom_css: "",
};

/**
 * Inject the shared config form CSS into the document (once).
 */
export function injectConfigFormCSS() {
  if (!document.getElementById("config-form-css")) {
    const style = document.createElement("style");
    style.id = "config-form-css";
    style.textContent = configFormCss;
    document.head.appendChild(style);
  }
}

/**
 * Get the config form HTML from the shared template.
 * Injects page size options into the placeholder.
 * Filters out landscape variants (orientation is a separate toggle).
 */
export function getConfigFormHTML() {
  const sizeOpts = PAGE_SIZES.filter((s) => !s.endsWith("-landscape"))
    .map((s) => `<option value="${s}">${s}</option>`)
    .join("\n");

  return configFormHtml.replace("<!-- PAGE_SIZE_OPTIONS -->", sizeOpts);
}

/**
 * Populate form fields from a config object.
 */
export function populateForm(form, config) {
  const c = { ...DEFAULTS, ...config };

  // Text inputs
  form.querySelectorAll('input[type="text"]').forEach((el) => {
    const k = el.dataset.f;
    if (k && c[k] !== undefined) el.value = c[k];
  });

  // Selects with data-f (column_justify, fonts, imposition etc.)
  form.querySelectorAll("select[data-f]").forEach((el) => {
    const v = c[el.dataset.f];
    if (v === undefined) return;
    // Font selects: check if value is in preset options
    if (el.classList.contains("font-sel")) {
      const ci = el.closest(".font-row")?.querySelector(".font-custom");
      const hasPreset = Array.from(el.options).some(
        (o) => o.value === v && o.value !== "__custom"
      );
      if (hasPreset) {
        el.value = v;
        if (ci) { ci.style.display = "none"; ci.value = ""; }
      } else if (v) {
        el.value = "__custom";
        if (ci) { ci.style.display = ""; ci.value = v; }
      }
      return;
    }
    // Non-font selects
    if (!Array.from(el.options).some((o) => o.value === v)) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.text = v;
      el.insertBefore(opt, el.firstChild);
    }
    el.value = v;
  });

  // Page size + orientation
  const sel = form.querySelector('select[name="page_size"]');
  let ps = c.page_size || "a5";
  const isLandscape = ps.endsWith("-landscape");
  const baseSize = isLandscape ? ps.replace("-landscape", "") : ps;
  // Set orientation radio
  const oRadio = form.querySelector(
    `input[name="orientation"][value="${isLandscape ? "landscape" : "portrait"}"]`
  );
  if (oRadio) oRadio.checked = true;
  // Set page size dropdown (without -landscape suffix)
  if (PAGE_SIZES.includes(ps) || PAGE_SIZES.includes(baseSize)) {
    sel.value = baseSize;
    const customSz = form.querySelector("#custom-sz");
    if (customSz) customSz.style.display = "none";
  } else {
    sel.value = "custom";
    const customSz = form.querySelector("#custom-sz");
    if (customSz) customSz.style.display = "";
    form.querySelector('input[name="page_size_custom"]').value = ps;
  }

  // Checkboxes
  form.querySelectorAll('input[type="checkbox"]').forEach((el) => {
    if (el.dataset.f && c[el.dataset.f] !== undefined)
      el.checked = c[el.dataset.f];
  });

  // Range
  const rng = form.querySelector('input[name="default_columns"]');
  if (rng && c.default_columns !== undefined) {
    rng.value = c.default_columns;
    form.querySelector('output[name="col_out"]').textContent = c.default_columns;
  }

  // Imposition booleans → imposition select
  const imp = form.querySelector('[data-f="imposition"]');
  if (imp) {
    if (c.micro_mini) imp.value = "micro_mini";
    else if (c.mini_zine) imp.value = "mini_zine";
    else if (c.trifold) imp.value = "trifold";
    else if (c.french_fold) imp.value = "french_fold";
    else if (c.booklet) imp.value = "booklet";
    else if (c.imposition && c.imposition !== "none") imp.value = c.imposition;
    else imp.value = "none";
  }

  // Size inputs: parse "10mm" → number=10, unit="mm"
  form.querySelectorAll(".size-input").forEach((si) => {
    const inp = si.querySelector('input[type="number"]');
    const unitSel = si.querySelector("select");
    const k = inp.dataset.f;
    const val = c[k];
    if (!val) {
      inp.value = "";
      unitSel.value = unitSel.options[0].value;
      return;
    }
    const m = String(val).match(/^([0-9]*\.?[0-9]+)\s*(.+)$/);
    if (m) {
      inp.value = m[1];
      unitSel.value = m[2];
    } else {
      inp.value = val;
    }
  });

  // Sync color pickers from text values
  syncColorsFromText(form);
}

/**
 * Collect form values into a config object.
 */
export function collectForm(form) {
  const d = {};

  form.querySelectorAll('input[type="text"]').forEach((el) => {
    if (el.dataset.f) d[el.dataset.f] = el.value;
  });

  form.querySelectorAll("select[data-f]").forEach((el) => {
    if (el.dataset.f === "imposition") return; // handled below
    let val = el.value;
    // Font selects: use custom input value when Custom... is selected
    if (el.classList.contains("font-sel") && val === "__custom") {
      const ci = el.closest(".font-row")?.querySelector(".font-custom");
      val = ci ? ci.value : "";
    }
    d[el.dataset.f] = val;
  });

  // Page size + orientation
  const sel = form.querySelector('select[name="page_size"]');
  let ps =
    sel.value === "custom"
      ? form.querySelector('input[name="page_size_custom"]').value
      : sel.value;
  const orient = form.querySelector('input[name="orientation"]:checked');
  if (orient && orient.value === "landscape" && !ps.endsWith("-landscape") && sel.value !== "custom") {
    ps += "-landscape";
  }
  d.page_size = ps;

  form.querySelectorAll('input[type="checkbox"]').forEach((el) => {
    if (el.dataset.f) d[el.dataset.f] = el.checked;
  });

  const rng = form.querySelector('input[name="default_columns"]');
  if (rng) d.default_columns = parseInt(rng.value);

  // Imposition select → config booleans
  const imp = form.querySelector('[data-f="imposition"]');
  if (imp) {
    d.booklet = imp.value === "booklet";
    d.mini_zine = imp.value === "mini_zine";
    d.trifold = imp.value === "trifold";
    d.french_fold = imp.value === "french_fold";
    d.micro_mini = imp.value === "micro_mini";
  }

  // Size inputs: combine number + unit → "10mm"
  form.querySelectorAll(".size-input").forEach((si) => {
    const inp = si.querySelector('input[type="number"]');
    const unitSel = si.querySelector("select");
    const k = inp.dataset.f;
    if (inp.value) d[k] = inp.value + unitSel.value;
    else d[k] = "";
  });

  return d;
}

/**
 * Convert a config object to TOML string for the worker.
 */
export function configToToml(config) {
  const lines = [];

  // [zine] section
  const zineFields = [
    "title", "page_size", "default_columns", "mode", "version",
    "booklet", "mini_zine", "trifold", "french_fold", "micro_mini",
  ];
  const zineLines = [];
  for (const k of zineFields) {
    if (config[k] === undefined || config[k] === "" || config[k] === DEFAULTS[k]) continue;
    if (typeof config[k] === "boolean" && config[k] === false) continue;
    const tomlKey = k.replace(/_/g, "-");
    const val = typeof config[k] === "string" ? `"${config[k]}"` : config[k];
    zineLines.push(`${tomlKey} = ${val}`);
  }
  if (zineLines.length) {
    lines.push("[zine]", ...zineLines, "");
  }

  // [theme] section
  const themeFields = [
    "font_heading", "font_body", "font_mono",
    "font_size_body", "font_size_h1", "font_size_h2", "font_size_h3", "font_size_h4",
    "color_text", "color_border", "color_bg_muted", "color_text_muted",
    "color_table_header_bg", "color_table_header_text", "color_accent",
    "page_number_color", "page_number_size", "page_number_font",
    "column_justify", "custom_css",
  ];
  const themeLines = [];
  for (const k of themeFields) {
    if (config[k] === undefined || config[k] === "" || config[k] === DEFAULTS[k]) continue;
    const tomlKey = k.replace(/_/g, "-");
    themeLines.push(`${tomlKey} = "${config[k]}"`);
  }
  if (themeLines.length) {
    lines.push("[theme]", ...themeLines, "");
  }

  // [margins] section
  const marginFields = ["margin_vertical", "margin_horizontal", "margin_spine"];
  const marginLines = [];
  for (const k of marginFields) {
    if (config[k] === undefined || config[k] === "" || config[k] === DEFAULTS[k]) continue;
    const tomlKey = k.replace("margin_", "");
    marginLines.push(`${tomlKey} = "${config[k]}"`);
  }
  if (marginLines.length) {
    lines.push("[margins]", ...marginLines, "");
  }

  return lines.join("\n");
}

/**
 * Initialize config panel event listeners.
 * @param {HTMLFormElement} form
 * @param {function} onChange - called on any form change
 */
export function initConfigListeners(form, onChange) {
  // Page size toggle
  form.querySelector('select[name="page_size"]').addEventListener("change", function () {
    const customSz = form.querySelector("#custom-sz");
    if (customSz) customSz.style.display = this.value === "custom" ? "" : "none";
    onChange();
  });

  // Columns slider
  form.querySelector('input[name="default_columns"]').addEventListener("input", function () {
    form.querySelector('output[name="col_out"]').textContent = this.value;
    onChange();
  });

  // Font select: show/hide custom input
  form.querySelectorAll("select.font-sel").forEach((sel) => {
    sel.addEventListener("change", function () {
      const ci = this.closest(".font-row")?.querySelector(".font-custom");
      if (ci) ci.style.display = this.value === "__custom" ? "" : "none";
      onChange();
    });
  });

  // Custom font input
  form.querySelectorAll(".font-custom").forEach((ci) => {
    ci.addEventListener("input", () => onChange());
  });

  // Color picker <-> text input sync
  form.querySelectorAll("input[data-cp]").forEach((cp) => {
    const tf = form.querySelector(`input[data-f="${cp.dataset.cp}"]`);
    if (!tf) return;
    cp.addEventListener("input", () => {
      tf.value = cp.value;
      onChange();
    });
    tf.addEventListener("input", () => {
      if (/^#[0-9a-fA-F]{3,6}$/.test(tf.value))
        cp.value = normalizeColor(tf.value);
    });
  });

  // Auto-preview on any form change
  form.addEventListener("input", (e) => {
    if (e.target.name === "default_columns") return;
    if (e.target.dataset && e.target.dataset.cp) return;
    onChange();
  });
  form.addEventListener("change", () => onChange());
}

function normalizeColor(v) {
  if (/^#[0-9a-fA-F]{3}$/.test(v))
    return "#" + v[1] + v[1] + v[2] + v[2] + v[3] + v[3];
  return v;
}

function syncColorsFromText(form) {
  form.querySelectorAll("input[data-cp]").forEach((cp) => {
    const tf = form.querySelector(`input[data-f="${cp.dataset.cp}"]`);
    if (tf && tf.value && /^#[0-9a-fA-F]{3,6}$/.test(tf.value)) {
      cp.value = normalizeColor(tf.value);
    }
  });
}
