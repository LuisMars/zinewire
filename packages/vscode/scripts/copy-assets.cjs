#!/usr/bin/env node
/**
 * Copy bundled assets (sources.json, worker.js) into out/ so the VSIX
 * is self-contained and doesn't need the monorepo at runtime.
 */
const fs = require("fs");
const path = require("path");

const coreDir = path.resolve(__dirname, "../../core/src");
const srcDir = path.resolve(__dirname, "../src");
const outDir = path.resolve(__dirname, "../out");

// Files from core/src
const coreFiles = ["sources.json", "worker.js"];
for (const file of coreFiles) {
  const src = path.join(coreDir, file);
  const dest = path.join(outDir, file);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    console.log(`Copied ${file} → out/`);
  } else {
    console.error(`Warning: ${src} not found`);
  }
}

// Files from vscode/src (JS assets that don't go through tsc)
const srcFiles = ["webview-ui.js"];
for (const file of srcFiles) {
  const src = path.join(srcDir, file);
  const dest = path.join(outDir, file);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    console.log(`Copied ${file} → out/`);
  } else {
    console.error(`Warning: ${src} not found`);
  }
}
