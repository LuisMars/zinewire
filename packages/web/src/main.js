/**
 * zinewire web editor — main entry point.
 * Wires together: Monaco editor ↔ Pyodide worker ↔ preview iframe.
 */

import { ZinewireBridge } from "@zinewire/core/bridge.js";
import { pythonSources, themeCss } from "@zinewire/core/sources.js";
import { createEditor } from "./editor.js";
import { Preview } from "./preview.js";
import { samples } from "./samples.js";
import {
  getConfigFormHTML,
  injectConfigFormCSS,
  populateForm,
  collectForm,
  configToToml,
  initConfigListeners,
} from "./config-panel.js";

// DOM references
const loadingEl = document.getElementById("loading");
const loadingStatus = document.getElementById("loading-status");
const appEl = document.getElementById("app");
const statusText = document.getElementById("status-text");
const previewFrame = document.getElementById("preview-frame");
const configPanel = document.getElementById("config-panel");
const configFormContainer = document.getElementById("config-form-container");
const sampleSelect = document.getElementById("sample-select");

// State
let currentMode = "print";
let currentSub = "default"; // 'default' or 'singles' (print sub-tab)
let editor = null;
let lastHtml = "";

// Preview manager
const preview = new Preview(previewFrame);

// Bridge to Pyodide worker
// Worker is in public/ so it's served as-is (not bundled by Vite).
// Classic workers need importScripts() which requires non-module context.
const bridge = new ZinewireBridge("/worker.js");

bridge.onStatus((msg) => {
  loadingStatus.textContent = msg;
});

// --- Config form setup ---

injectConfigFormCSS();
configFormContainer.innerHTML = getConfigFormHTML();
const configForm = document.getElementById("cf");

// Debounced config change → rebuild
let configTimer = null;
function onConfigChange() {
  if (configTimer) clearTimeout(configTimer);
  configTimer = setTimeout(() => {
    // Persist form state
    const collected = collectForm(configForm);
    localStorage.setItem("zinewire:config", JSON.stringify(collected));
    updateSubTabs();
    if (editor) doBuild(editor.getValue());
  }, 300);
}

initConfigListeners(configForm, onConfigChange);

// --- Samples setup ---

/** Parse our simple TOML subset into a flat config object for the form. */
function parseSimpleToml(toml) {
  const config = {};
  let section = "";
  for (const line of toml.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const secMatch = trimmed.match(/^\[(\w+)\]$/);
    if (secMatch) { section = secMatch[1]; continue; }
    const kvMatch = trimmed.match(/^([\w-]+)\s*=\s*(.+)$/);
    if (!kvMatch) continue;
    let [, key, val] = kvMatch;
    key = key.replace(/-/g, "_");
    val = val.trim();
    if (val === "true") val = true;
    else if (val === "false") val = false;
    else if (/^\d+$/.test(val)) val = parseInt(val);
    else val = val.replace(/^"(.*)"$/, "$1");
    // Map margin section keys
    if (section === "margins" && ["vertical", "horizontal", "spine"].includes(key)) {
      key = "margin_" + key;
    }
    config[key] = val;
  }
  return config;
}

samples.forEach((sample, i) => {
  const opt = document.createElement("option");
  opt.value = i;
  opt.textContent = sample.name;
  sampleSelect.appendChild(opt);
});

sampleSelect.addEventListener("change", () => {
  const sample = samples[sampleSelect.value];
  if (!sample || !editor) return;

  // Set editor content
  editor.setValue(sample.markdown);
  localStorage.setItem("zinewire:content", sample.markdown);

  // Populate form from sample config (or reset to defaults)
  const parsed = sample.config ? parseSimpleToml(sample.config) : {};
  populateForm(configForm, parsed);
  const collected = collectForm(configForm);
  localStorage.setItem("zinewire:config", JSON.stringify(collected));
  localStorage.removeItem("zinewire:config-toml");
  updateSubTabs();

  // Reset select to placeholder
  sampleSelect.value = "";

  doBuild(sample.markdown);
});

// --- Initialization ---

async function init() {
  try {
    // Start editor loading in parallel with Pyodide init
    const editorPromise = createEditor(
      document.getElementById("editor-pane"),
      onEditorChange
    );

    await bridge.init(pythonSources, themeCss);

    editor = await editorPromise;

    // Show app, hide loading
    loadingEl.classList.add("hidden");
    appEl.classList.remove("hidden");

    // Populate config form: saved values or defaults
    const savedConfig = localStorage.getItem("zinewire:config");
    try {
      populateForm(configForm, savedConfig ? JSON.parse(savedConfig) : {});
    } catch (_) {
      populateForm(configForm, {});
    }

    // Restore mode from localStorage
    const savedMode = localStorage.getItem("zinewire:mode");
    if (savedMode) setMode(savedMode);
    updateSubTabs();

    // Apply zoom now that the app is visible
    applyZoom(zoomSlider.value);

    // Trigger initial build
    await doBuild(editor.getValue());
  } catch (err) {
    loadingStatus.textContent = `Error: ${err.message}`;
    console.error("Init failed:", err);
  }
}

// --- Build ---

async function doBuild(markdown) {
  if (!bridge.isReady) return;

  statusText.textContent = "Building...";

  try {
    // Collect config from form and convert to TOML for the worker
    const collected = collectForm(configForm);
    // Singles sub-tab: strip imposition so we get plain reading pages
    if (currentMode === "print" && currentSub === "singles") {
      collected.booklet = false;
      collected.mini_zine = false;
      collected.trifold = false;
      collected.french_fold = false;
      collected.micro_mini = false;
    }
    let toml = configToToml(collected);

    // If a sample's raw TOML was loaded, use that instead
    const sampleToml = localStorage.getItem("zinewire:config-toml");
    if (sampleToml) {
      toml = sampleToml;
      // Clear it after first use — form changes take over
      localStorage.removeItem("zinewire:config-toml");
    }

    const result = await bridge.build(markdown, toml, currentMode);
    lastHtml = result.html;
    preview.update(result.html);

    const pageInfo =
      currentMode === "print" ? ` \u00b7 ${result.pages} pages` : "";
    statusText.textContent = `Ready${pageInfo}`;
  } catch (err) {
    preview.showError(err.message, err.traceback);
    statusText.textContent = "Build error";
  }
}

function onEditorChange(content) {
  doBuild(content);
}

// --- Mode switching ---

const subTabs = document.getElementById("sub-tabs");

function hasImposition() {
  const imp = configForm.querySelector('[data-f="imposition"]');
  return imp && imp.value !== "none";
}

function updateSubTabs() {
  const show = currentMode === "print" && hasImposition();
  subTabs.classList.toggle("visible", show);
}

function setSubTab(sub) {
  currentSub = sub;
  subTabs.querySelectorAll(".sub-tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.sub === sub);
  });
}

function setMode(mode) {
  currentMode = mode;
  localStorage.setItem("zinewire:mode", mode);

  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });

  // Reset sub-tab to default when switching to print with imposition
  if (mode === "print" && hasImposition()) {
    setSubTab("default");
  }
  updateSubTabs();

  if (editor) doBuild(editor.getValue());
}

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => setMode(btn.dataset.mode));
});

// Sub-tab clicks
subTabs.addEventListener("click", (e) => {
  const tab = e.target.closest(".sub-tab");
  if (!tab) return;
  setSubTab(tab.dataset.sub);
  if (editor) doBuild(editor.getValue());
});

// --- Zoom ---

const zoomSlider = document.getElementById("zoom-slider");
const zoomOutput = document.getElementById("zoom-output");
const previewPane = document.getElementById("preview-pane");

function applyZoom(val) {
  const pct = val / 100;
  const paneW = previewPane.clientWidth / pct;
  const paneH = previewPane.clientHeight / pct;
  previewFrame.style.width = paneW + "px";
  previewFrame.style.height = paneH + "px";
  previewFrame.style.transform = `translateX(-50%) scale(${pct})`;
  zoomOutput.textContent = val + "%";
}

zoomSlider.addEventListener("input", () => applyZoom(zoomSlider.value));
window.addEventListener("resize", () => applyZoom(zoomSlider.value));

// --- Config panel toggle ---

document.getElementById("btn-config").addEventListener("click", () => {
  configPanel.classList.toggle("hidden");
  requestAnimationFrame(() => applyZoom(zoomSlider.value));
});

document.getElementById("btn-config-close").addEventListener("click", () => {
  configPanel.classList.add("hidden");
  requestAnimationFrame(() => applyZoom(zoomSlider.value));
});

document.getElementById("btn-config-reset").addEventListener("click", () => {
  populateForm(configForm, {});
  localStorage.removeItem("zinewire:config");
  onConfigChange();
});

// --- Export ---

function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

document.getElementById("btn-export").addEventListener("click", () => {
  // Export HTML
  if (lastHtml) {
    downloadFile(lastHtml, "zine.html", "text/html");
  }

  // Export markdown
  if (editor) {
    downloadFile(editor.getValue(), "zine.md", "text/markdown");
  }

  // Export TOML config (only if non-default values exist)
  const toml = configToToml(collectForm(configForm));
  if (toml.trim()) {
    downloadFile(toml, "zinewire.toml", "text/plain");
  }
});

// --- Draggable divider ---

const divider = document.getElementById("divider");
const editorPane = document.getElementById("editor-pane");

divider.addEventListener("mousedown", (e) => {
  e.preventDefault();
  divider.classList.add("dragging");

  const onMove = (e) => {
    const containerRect = editorPane.parentElement.getBoundingClientRect();
    const fraction =
      (e.clientX - containerRect.left) / containerRect.width;
    const clamped = Math.max(0.15, Math.min(0.85, fraction));
    editorPane.style.flex = `0 0 ${clamped * 100}%`;
  };

  const onUp = () => {
    divider.classList.remove("dragging");
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
});

// --- Start ---

init();
