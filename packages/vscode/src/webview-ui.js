/**
 * zinewire VSCode Preview — WebView UI
 *
 * Loaded as an external script via webview.asWebviewUri() to avoid CSP issues
 * with inline scripts. Dynamic data (worker code, sources, themes) is injected
 * into window.__ZW by a nonce-protected inline <script> in the HTML template,
 * OR delivered via a 'init-data' postMessage from the extension host.
 */
(function () {
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

  // Worker state — set up once init-data arrives
  var worker = null;
  var ready = false;
  var pendingBuild = null;
  var pendingUpdate = null;  // update that arrived before worker init

  // --- Zoom ---
  function applyZoom() {
    zoomLabel.textContent = Math.round(zoom * 100) + '%';
    zoomRange.value = Math.round(zoom * 100);
    if (lastHtml) {
      showHtml(lastHtml);
    }
  }

  async function inlineFonts(html) {
    // VSCode blob iframes can't load external URLs — inline Google Fonts CSS
    html = html.replace(/<link[^>]+rel="preconnect"[^>]*>/g, '');
    var linkRe = /<link[^>]+href="(https:\/\/fonts\.googleapis\.com[^"]+)"[^>]*>/g;
    var matches = [];
    var m;
    while ((m = linkRe.exec(html)) !== null) {
      matches.push({ full: m[0], url: m[1] });
    }
    for (var i = 0; i < matches.length; i++) {
      try {
        var resp = await fetch(matches[i].url);
        var css = await resp.text();
        html = html.replace(matches[i].full, '<style>' + css + '</style>');
      } catch (e) { /* leave as-is if fetch fails */ }
    }
    return html;
  }

  async function showHtml(html) {
    lastHtml = html;
    html = await inlineFonts(html);
    if (zoom !== 1) {
      html = html.replace('</head>', '<style>html{zoom:' + zoom + '}</style></head>');
    }
    var blob = new Blob([html], { type: 'text/html' });
    previewEl.src = URL.createObjectURL(blob);
  }

  zoomRange.addEventListener('input', function () {
    zoom = parseInt(zoomRange.value) / 100;
    applyZoom();
  });
  document.getElementById('zoom-out').addEventListener('click', function () {
    zoom = Math.max(0.25, Math.round((zoom - 0.1) * 20) / 20);
    applyZoom();
  });
  document.getElementById('zoom-in').addEventListener('click', function () {
    zoom = Math.min(2, Math.round((zoom + 0.1) * 20) / 20);
    applyZoom();
  });

  // --- Imposition detection from TOML config ---
  function hasImposition(config) {
    return /^(booklet|mini-zine|trifold|french-fold|micro-mini)\s*=\s*true/m.test(config);
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
  document.querySelectorAll('.mode-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      currentMode = btn.dataset.mode;
      document.querySelectorAll('.mode-btn').forEach(function (b) {
        b.classList.toggle('active', b.dataset.mode === currentMode);
      });
      if (currentMode === 'print' && hasImposition(lastConfig)) {
        currentSub = 'default';
        document.querySelectorAll('.sub-tab').forEach(function (t) {
          t.classList.toggle('active', t.dataset.sub === 'default');
        });
      }
      updateSubTabs();
      triggerBuild();
    });
  });

  // --- Sub-tab switching ---
  subTabs.addEventListener('click', function (e) {
    var tab = e.target.closest('.sub-tab');
    if (!tab) return;
    currentSub = tab.dataset.sub;
    document.querySelectorAll('.sub-tab').forEach(function (t) {
      t.classList.toggle('active', t.dataset.sub === currentSub);
    });
    triggerBuild();
  });

  // --- Worker init ---
  function initWorker(workerCode, sources, themes) {
    if (!workerCode) {
      statusEl.textContent = 'Error: worker code missing';
      return;
    }
    var workerBlob = new Blob([workerCode], { type: 'application/javascript' });
    var workerUrl = URL.createObjectURL(workerBlob);
    try {
      worker = new Worker(workerUrl);
    } catch (e) {
      statusEl.textContent = 'Worker error: ' + e.message;
      return;
    }

    worker.onerror = function (e) {
      statusEl.textContent = 'Worker error: ' + (e.message || '?');
    };

    worker.onmessage = function (e) {
      var data = e.data;
      if (data.type === 'status') {
        statusEl.textContent = data.msg;
      } else if (data.type === 'ready') {
        ready = true;
        statusEl.textContent = 'Ready';
        if (pendingBuild) {
          worker.postMessage(pendingBuild);
          pendingBuild = null;
          statusEl.textContent = 'Building...';
        }
      } else if (data.type === 'result') {
        showHtml(data.html);
        var pages = data.pages > 0 ? ' \u00b7 ' + data.pages + ' pages' : '';
        statusEl.textContent = 'Ready' + pages;
      } else if (data.type === 'error') {
        statusEl.textContent = 'Error: ' + data.message;
      }
    };

    worker.postMessage({ type: 'init', sources: sources, themes: themes });

    // Apply any update that arrived before the worker was ready
    if (pendingUpdate) {
      applyUpdate(pendingUpdate);
      pendingUpdate = null;
    }
  }

  function applyUpdate(msg) {
    lastMarkdown = msg.markdown;
    lastConfig = msg.config || '';
    lastDataFiles = msg.dataFiles || {};
    updateSubTabs();
    triggerBuild();
  }

  // --- Messages from extension host ---
  window.addEventListener('message', function (e) {
    var msg = e.data;
    if (msg.type === 'init-data') {
      initWorker(msg.workerCode, msg.sources, msg.themes);
    } else if (msg.type === 'update') {
      if (worker) {
        applyUpdate(msg);
      } else {
        pendingUpdate = msg;  // will be applied once init-data arrives
      }
    }
  });

  // Signal to the extension that the listener is registered and we're ready
  // to receive init-data. Must happen AFTER addEventListener to avoid a race.
  try {
    acquireVsCodeApi().postMessage({ type: 'webview-ready' });
  } catch (e) { /* not in a VSCode context */ }

})();

