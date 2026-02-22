#!/usr/bin/env node
/**
 * Copy bundled assets (sources.json, worker.js) into out/ so the VSIX
 * is self-contained and doesn't need the monorepo at runtime.
 */
const fs = require("fs");
const path = require("path");

const coreDir = path.resolve(__dirname, "../../core/src");
const outDir = path.resolve(__dirname, "../out");

const files = ["sources.json", "worker.js"];

for (const file of files) {
  const src = path.join(coreDir, file);
  const dest = path.join(outDir, file);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    console.log(`Copied ${file} → out/`);
  } else {
    console.error(`Warning: ${src} not found`);
  }
}
