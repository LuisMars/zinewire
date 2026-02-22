import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

/**
 * Manages a WebView panel that runs the zinewire Pyodide worker
 * to render live previews of zine projects.
 *
 * Entry point is a zinewire.toml or a .md file.
 * The panel finds the TOML config, resolves markdown sources, and builds.
 */
export class PreviewPanel {
  private static instance: PreviewPanel | undefined;
  private readonly panel: vscode.WebviewPanel;
  private readonly context: vscode.ExtensionContext;
  private projectDir: string;
  private tomlPath: string | null;
  private disposed = false;

  static createOrShow(context: vscode.ExtensionContext, targetUri: vscode.Uri) {
    const fsPath = targetUri.fsPath;

    // Resolve project directory and config file path.
    // If the target is a .toml, use it directly as the config.
    // If it's a .md, walk up to find any .toml config file.
    let projectDir: string;
    let tomlPath: string | null = null;
    if (fsPath.endsWith(".toml")) {
      projectDir = path.dirname(fsPath);
      tomlPath = fsPath;
    } else {
      const found = findTomlFile(fsPath);
      if (found) {
        projectDir = path.dirname(found);
        tomlPath = found;
      } else {
        projectDir = path.dirname(fsPath);
      }
    }

    if (PreviewPanel.instance) {
      PreviewPanel.instance.projectDir = projectDir;
      PreviewPanel.instance.tomlPath = tomlPath;
      PreviewPanel.instance.panel.reveal(vscode.ViewColumn.Beside);
      PreviewPanel.instance.doBuild();
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "zinewirePreview",
      "zinewire Preview",
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
      }
    );

    PreviewPanel.instance = new PreviewPanel(panel, context, projectDir, tomlPath);
    PreviewPanel.instance.doBuild();
  }

  static rebuild() {
    if (PreviewPanel.instance && !PreviewPanel.instance.disposed) {
      PreviewPanel.instance.doBuild();
    }
  }

  static dispose() {
    if (PreviewPanel.instance) {
      PreviewPanel.instance.panel.dispose();
    }
  }

  private constructor(
    panel: vscode.WebviewPanel,
    context: vscode.ExtensionContext,
    projectDir: string,
    tomlPath: string | null
  ) {
    this.panel = panel;
    this.context = context;
    this.projectDir = projectDir;
    this.tomlPath = tomlPath;

    this.panel.webview.html = this.getWebviewContent();

    this.panel.onDidDispose(() => {
      this.disposed = true;
      PreviewPanel.instance = undefined;
    });
  }

  private doBuild() {
    const configToml = this.tomlPath && fs.existsSync(this.tomlPath)
      ? fs.readFileSync(this.tomlPath, "utf-8")
      : "";

    // Resolve markdown sources: TOML files list > *.md in project dir
    const markdown = this.resolveMarkdown(configToml);
    if (!markdown) {
      this.panel.webview.postMessage({
        type: "update",
        markdown: "# No markdown files found\n\nAdd `.md` files to your project or specify `files` in `zinewire.toml`.",
        config: "",
      });
      return;
    }

    // Collect data files referenced by /table directives
    const dataFiles = this.collectDataFiles(markdown);

    // Collect custom CSS if referenced in config
    const customCssMatch = configToml.match(/^custom-css\s*=\s*"([^"]+)"/m);
    if (customCssMatch) {
      const cssPath = path.join(this.projectDir, customCssMatch[1]);
      if (fs.existsSync(cssPath)) {
        dataFiles[customCssMatch[1]] = fs.readFileSync(cssPath, "utf-8");
      }
    }

    // Send content to WebView — it manages mode/sub-tab state internally
    this.panel.webview.postMessage({
      type: "update",
      markdown,
      config: configToml,
      dataFiles,
    });
  }

  private resolveMarkdown(configToml: string): string {
    // Parse files list from TOML (simple extraction)
    const filesMatch = configToml.match(
      /^files\s*=\s*\[([^\]]*)\]/m
    );

    let patterns: string[] = [];
    if (filesMatch) {
      patterns = filesMatch[1]
        .split(",")
        .map((s) => s.trim().replace(/^["']|["']$/g, ""))
        .filter(Boolean);
    }

    // Resolve file list
    let mdFiles: string[] = [];
    if (patterns.length > 0) {
      for (const pattern of patterns) {
        const matches = simpleGlob(pattern, this.projectDir);
        mdFiles.push(...matches);
      }
    } else {
      // Auto-detect *.md in project dir
      mdFiles = simpleGlob("*.md", this.projectDir);
    }

    if (mdFiles.length === 0) {
      return "";
    }

    // Concatenate all markdown files (with /page separator like the CLI)
    const parts: string[] = [];
    for (const file of mdFiles) {
      const fullPath = path.join(this.projectDir, file);
      if (fs.existsSync(fullPath)) {
        parts.push(fs.readFileSync(fullPath, "utf-8"));
      }
    }

    return parts.join("\n\n/page\n\n");
  }

  /**
   * Scan markdown for /table directives and read the referenced JSON files
   * from the project directory, returning a map of { relativePath: content }.
   */
  private collectDataFiles(markdown: string): Record<string, string> {
    const dataFiles: Record<string, string> = {};
    const tableRegex = /^\/table\s+(\S+)\s*$/gm;
    let match: RegExpExecArray | null;

    while ((match = tableRegex.exec(markdown)) !== null) {
      const relPath = match[1];
      if (dataFiles[relPath]) continue; // already collected
      const fullPath = path.join(this.projectDir, relPath);
      if (fs.existsSync(fullPath)) {
        try {
          dataFiles[relPath] = fs.readFileSync(fullPath, "utf-8");
        } catch {}
      }
    }

    return dataFiles;
  }

  private getWebviewContent(): string {
    const outDir = path.join(this.context.extensionPath, "out");
    const sourcesJsonFile = path.join(outDir, "sources.json");
    const workerFile = path.join(outDir, "worker.js");

    let sourcesData = "{}";
    let themesData = "{}";
    let workerCode = "";

    // Escape </ sequences to prevent </script> in Python sources from breaking HTML
    const safeJson = (obj: unknown) =>
      JSON.stringify(obj).replace(/<\//g, "<\\/");

    if (fs.existsSync(sourcesJsonFile)) {
      const data = JSON.parse(fs.readFileSync(sourcesJsonFile, "utf-8"));
      sourcesData = safeJson(data.pythonSources);
      themesData = safeJson(data.themeCss);
    }

    if (fs.existsSync(workerFile)) {
      workerCode = fs.readFileSync(workerFile, "utf-8");
    }

    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { height: 100%; overflow: hidden; background: #1e1e1e; font-family: -apple-system, system-ui, sans-serif; color: #ccc; }
    body { display: flex; flex-direction: column; }

    /* Toolbar */
    .toolbar {
      display: flex; align-items: center; height: 32px; flex-shrink: 0;
      background: #252526; border-bottom: 1px solid #3c3c3c;
      padding: 0 8px; gap: 2px;
    }
    .mode-btn {
      background: transparent; border: none; color: #888;
      font: 500 11px -apple-system, system-ui, sans-serif;
      padding: 4px 10px; border-radius: 3px; cursor: pointer;
    }
    .mode-btn:hover { color: #ccc; background: #333; }
    .mode-btn.active { color: #fff; background: #444; }

    .sub-tabs {
      display: none; align-items: center; gap: 1px;
      margin-left: 2px; padding-left: 6px;
      border-left: 1px solid #444;
    }
    .sub-tabs.visible { display: flex; }
    .sub-tab {
      background: transparent; border: none; color: #555;
      font: 500 9px -apple-system, system-ui, sans-serif;
      padding: 3px 6px; border-radius: 3px; cursor: pointer;
    }
    .sub-tab:hover { color: #bbb; background: #333; }
    .sub-tab.active { color: #ddd; background: #3a3a3a; }

    .sep {
      width: 1px; height: 16px; background: #444; margin: 0 4px;
    }
    .zoom-controls {
      display: flex; align-items: center; gap: 4px;
    }
    .zoom-btn {
      background: transparent; border: none; color: #888;
      font: 600 13px monospace; width: 20px; height: 20px;
      border-radius: 3px; cursor: pointer; display: flex;
      align-items: center; justify-content: center; line-height: 1;
    }
    .zoom-btn:hover { color: #ccc; background: #333; }
    .zoom-range {
      width: 80px; accent-color: #666; height: 3px;
    }
    .zoom-label {
      font: 500 10px -apple-system, system-ui, sans-serif;
      color: #888; min-width: 30px; text-align: right;
      font-variant-numeric: tabular-nums;
    }

    .spacer { flex: 1; }
    .status {
      font-size: 11px; color: #888; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis;
    }

    /* Preview — iframe fills all available space, zoom applied inside */
    #preview {
      flex: 1; width: 100%;
      border: none; display: block;
    }
  </style>
</head>
<body>
  <div class="toolbar">
    <button class="mode-btn active" data-mode="print">print</button>
    <button class="mode-btn" data-mode="manual">manual</button>
    <button class="mode-btn" data-mode="web">web</button>
    <div id="sub-tabs" class="sub-tabs">
      <button class="sub-tab active" data-sub="default">Default</button>
      <button class="sub-tab" data-sub="singles">Singles</button>
    </div>
    <div class="sep"></div>
    <div class="zoom-controls">
      <button class="zoom-btn" id="zoom-out">-</button>
      <input type="range" class="zoom-range" id="zoom-range" min="25" max="200" value="100" step="5">
      <button class="zoom-btn" id="zoom-in">+</button>
      <span class="zoom-label" id="zoom-label">100%</span>
    </div>
    <div class="spacer"></div>
    <span id="status" class="status">Initializing zinewire...</span>
  </div>
  <iframe id="preview" sandbox="allow-scripts allow-same-origin"></iframe>

  <script>
    var statusEl = document.getElementById('status');
    var previewEl = document.getElementById('preview');
    var subTabs = document.getElementById('sub-tabs');
    var zoomRange = document.getElementById('zoom-range');
    var zoomLabel = document.getElementById('zoom-label');

    // State
    var currentMode = 'print';
    var currentSub = 'default';
    var lastMarkdown = '';
    var lastConfig = '';
    var lastDataFiles = {};
    var lastHtml = '';
    var zoom = 1;

    // --- Zoom ---
    // Inject zoom style into HTML and reload the blob — reliable in any sandbox.
    function applyZoom() {
      zoomLabel.textContent = Math.round(zoom * 100) + '%';
      zoomRange.value = Math.round(zoom * 100);
      if (lastHtml) {
        showHtml(lastHtml);
      }
    }

    function showHtml(html) {
      lastHtml = html;
      if (zoom !== 1) {
        html = html.replace('</head>', '<style>html{zoom:' + zoom + '}</style></head>');
      }
      var blob = new Blob([html], { type: 'text/html' });
      previewEl.src = URL.createObjectURL(blob);
    }

    zoomRange.addEventListener('input', function() {
      zoom = parseInt(zoomRange.value) / 100;
      applyZoom();
    });
    document.getElementById('zoom-out').addEventListener('click', function() {
      zoom = Math.max(0.25, Math.round((zoom - 0.1) * 20) / 20);
      applyZoom();
    });
    document.getElementById('zoom-in').addEventListener('click', function() {
      zoom = Math.min(2, Math.round((zoom + 0.1) * 20) / 20);
      applyZoom();
    });

    // Worker setup
    var workerCode = ${safeJson(workerCode)};
    var workerBlob = new Blob([workerCode], { type: 'application/javascript' });
    var workerUrl = URL.createObjectURL(workerBlob);
    var worker = new Worker(workerUrl);

    var sources = ${sourcesData};
    var themes = ${themesData};

    var ready = false;
    var pendingBuild = null;

    // --- Imposition detection from TOML config ---
    function hasImposition(config) {
      return /^(booklet|mini-zine|trifold|french-fold|micro-mini)\\s*=\\s*true/m.test(config);
    }

    function updateSubTabs() {
      var show = currentMode === 'print' && hasImposition(lastConfig);
      subTabs.classList.toggle('visible', show);
    }

    // --- Build ---
    function triggerBuild() {
      if (!lastMarkdown) return;
      var singles = currentMode === 'print' && currentSub === 'singles';
      var msg = { type: 'build', markdown: lastMarkdown, config: lastConfig, mode: currentMode, singles: singles, dataFiles: lastDataFiles };
      if (ready) {
        worker.postMessage(msg);
        statusEl.textContent = 'Building...';
      } else {
        pendingBuild = msg;
      }
    }

    // --- Mode switching ---
    document.querySelectorAll('.mode-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        currentMode = btn.dataset.mode;
        document.querySelectorAll('.mode-btn').forEach(function(b) {
          b.classList.toggle('active', b.dataset.mode === currentMode);
        });
        if (currentMode === 'print' && hasImposition(lastConfig)) {
          currentSub = 'default';
          document.querySelectorAll('.sub-tab').forEach(function(t) {
            t.classList.toggle('active', t.dataset.sub === 'default');
          });
        }
        updateSubTabs();
        triggerBuild();
      });
    });

    // --- Sub-tab switching ---
    subTabs.addEventListener('click', function(e) {
      var tab = e.target.closest('.sub-tab');
      if (!tab) return;
      currentSub = tab.dataset.sub;
      document.querySelectorAll('.sub-tab').forEach(function(t) {
        t.classList.toggle('active', t.dataset.sub === currentSub);
      });
      triggerBuild();
    });

    // --- Worker messages ---
    worker.onmessage = function(e) {
      var data = e.data;
      if (data.type === 'status') {
        statusEl.textContent = data.msg;
      } else if (data.type === 'ready') {
        ready = true;
        statusEl.textContent = 'Ready';
        if (pendingBuild) {
          worker.postMessage(pendingBuild);
          pendingBuild = null;
        }
      } else if (data.type === 'result') {
        showHtml(data.html);
        var pages = data.pages > 0 ? ' \\u00b7 ' + data.pages + ' pages' : '';
        statusEl.textContent = 'Ready' + pages;
      } else if (data.type === 'error') {
        statusEl.textContent = 'Error: ' + data.message;
      }
    };

    // Initialize worker
    worker.postMessage({ type: 'init', sources: sources, themes: themes });

    // Listen for content updates from the extension
    window.addEventListener('message', function(e) {
      var msg = e.data;
      if (msg.type === 'update') {
        lastMarkdown = msg.markdown;
        lastConfig = msg.config || '';
        lastDataFiles = msg.dataFiles || {};
        var dfCount = Object.keys(lastDataFiles).length;
        statusEl.textContent = 'Update received: ' + lastMarkdown.length + ' chars, ' + dfCount + ' data files';
        updateSubTabs();
        triggerBuild();
      }
    });
  </script>
</body>
</html>`;
  }
}

/**
 * Simple glob matching for patterns like "*.md", "chapter*.md", "docs/*.md".
 * Covers the patterns used in zinewire.toml files lists.
 */
function simpleGlob(pattern: string, cwd: string): string[] {
  const dir = path.dirname(pattern) || ".";
  const base = path.basename(pattern);
  const searchDir = dir === "." ? cwd : path.join(cwd, dir);

  if (!fs.existsSync(searchDir)) {
    return [];
  }

  // Convert glob pattern to regex: * → [^/]*, ? → [^/]
  const regexStr = "^" + base.replace(/\*/g, "[^/]*").replace(/\?/g, "[^/]") + "$";
  const regex = new RegExp(regexStr);

  return fs.readdirSync(searchDir)
    .filter((f) => regex.test(f))
    .sort()
    .map((f) => (dir === "." ? f : path.join(dir, f)));
}

/** Walk up from a file path looking for a .toml config file (zinewire.toml or any *.toml). */
function findTomlFile(filePath: string): string | null {
  const workspaceRoot =
    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || "";
  let dir = path.dirname(filePath);

  while (dir.length >= workspaceRoot.length) {
    // Prefer zinewire.toml if it exists
    const canonical = path.join(dir, "zinewire.toml");
    if (fs.existsSync(canonical)) {
      return canonical;
    }
    // Otherwise look for any .toml file in this directory
    try {
      const toml = fs.readdirSync(dir).find((f) => f.endsWith(".toml"));
      if (toml) {
        return path.join(dir, toml);
      }
    } catch {}
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}
