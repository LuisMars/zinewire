# zinewire web editor

Browser-based zine editor. Split-pane layout with a Monaco markdown editor on the left and a live zinewire preview on the right. Runs entirely client-side — no backend, no Python install.

Uses [Pyodide](https://pyodide.org/) to run the full zinewire Python pipeline in WebAssembly.

## Quick start

```bash
# From repo root
cd packages/web
npm install
npm run dev
```

Open `http://localhost:3000`. First load downloads the Pyodide runtime (~20 MB), which is cached by the browser for subsequent visits.

## How it works

1. A Web Worker loads Pyodide and installs `markdown` + `pymdown-extensions` via micropip
2. zinewire's Python source and CSS themes are bundled into a JS module at build time (`packages/core/scripts/bundle-sources.cjs`)
3. The Python files are written into Pyodide's virtual filesystem so imports work unchanged
4. On each editor change (400 ms debounce), the worker runs `zinewire.build()` and returns self-contained HTML
5. The preview iframe loads the HTML via a blob URL

## Features

- **Live preview** — rebuilds on every edit with 400 ms debounce
- **Mode switching** — print, manual, and landing modes
- **Config panel** — paste a `zinewire.toml` to configure fonts, page size, colors
- **Export** — download the rendered HTML
- **Persistence** — markdown, config, and mode are saved to localStorage
- **Draggable split** — resize editor and preview panes

## Build for production

```bash
npm run build
```

Output goes to `dist/` — a static site deployable to GitHub Pages, Netlify, or any static host.

## Limitations

- `/table data.json` directives don't work (no real filesystem in the browser)
- `/cover image.jpg` with local images won't work — use URLs instead
- First load is slow (~10-15 s) while Pyodide downloads; cached loads are ~1-2 s

## Architecture

```
packages/web/
├── index.html           # App shell (toolbar, editor, preview, config panel)
├── vite.config.js       # Vite bundler config
├── public/
│   └── worker.js        # Pyodide Web Worker (served as-is, not bundled)
└── src/
    ├── main.js          # App init, wires editor ↔ worker ↔ preview
    ├── editor.js        # Monaco editor setup (loaded from CDN)
    ├── preview.js       # iframe blob-URL preview manager
    └── style.css        # Dark theme app layout
```

Depends on `packages/core/` for the shared worker, bridge, and bundled Python sources.
