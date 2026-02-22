# zinewire preview for VSCode

Live preview extension for zinewire markdown zines. Opens a side-by-side preview panel that renders your zine as you edit.

Uses the same Pyodide engine as the web editor — no Python install required.

## Development

```bash
# From repo root
cd packages/vscode
npm install
npm run compile
```

Then press **F5** in VSCode to launch the Extension Development Host. Open any `.md` file and run the command:

> **zinewire: Open Preview**

Or click the preview icon in the editor title bar (visible on markdown files).

## How it works

1. The extension opens a WebView panel beside your editor
2. The WebView runs a Pyodide Web Worker (same as the web editor)
3. Pyodide is downloaded from CDN on first use and cached locally
4. On file save, the extension reads the markdown content + any `zinewire.toml` config and sends it to the worker
5. The worker runs `zinewire.build()` and the preview updates

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `zinewire.previewMode` | `print` | Preview mode: `print`, `manual`, or `landing` |

## Config auto-detection

The extension walks up from your markdown file's directory looking for `zinewire.toml`. If found, it's passed to the builder automatically.

## Building the extension

```bash
# Compile TypeScript
npm run compile

# Package as .vsix
npm run package
```

## Architecture

```
packages/vscode/
├── package.json         # Extension manifest, commands, settings
├── tsconfig.json
└── src/
    ├── extension.ts     # Activation, command registration, save listener
    └── preview-panel.ts # WebView panel lifecycle + embedded Pyodide worker
```

Depends on `packages/core/` for the shared worker code and bundled Python sources.
