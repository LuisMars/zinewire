/**
 * zinewire Pyodide Web Worker
 *
 * Runs the zinewire Python pipeline inside Pyodide (Python-in-WASM).
 * Communicates with the main thread via postMessage.
 *
 * Protocol:
 *   → { type: 'init', sources: Record<string,string>, themes: Record<string,string> }
 *   ← { type: 'status', msg: string }
 *   ← { type: 'ready' }
 *   → { type: 'build', markdown: string, config: string, mode: string }
 *   ← { type: 'result', html: string, pages: number, mode: string }
 *   ← { type: 'error', message: string, traceback: string }
 */

/* global importScripts, loadPyodide */

let pyodide = null;

function status(msg) {
  postMessage({ type: "status", msg });
}

async function init(sources, themes) {
  status("Loading Python runtime...");
  importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");
  pyodide = await loadPyodide();

  status("Installing markdown packages...");
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  await micropip.install(["markdown", "pymdown-extensions"]);

  status("Loading zinewire...");

  // Write Python source files into Pyodide's virtual filesystem
  pyodide.FS.mkdir("/zinewire_pkg");
  pyodide.FS.mkdir("/zinewire_pkg/zinewire");
  pyodide.FS.mkdir("/zinewire_pkg/zinewire/themes");

  for (const [filename, content] of Object.entries(sources)) {
    if (filename.startsWith("themes/")) {
      pyodide.FS.writeFile(`/zinewire_pkg/zinewire/${filename}`, content);
    } else {
      pyodide.FS.writeFile(`/zinewire_pkg/zinewire/${filename}`, content);
    }
  }

  // Write CSS theme files
  for (const [filename, content] of Object.entries(themes)) {
    pyodide.FS.writeFile(`/zinewire_pkg/zinewire/themes/${filename}`, content);
  }

  // Add to Python path and verify import
  pyodide.runPython(`
import sys
sys.path.insert(0, '/zinewire_pkg')

# Verify core imports work
from zinewire import build
from zinewire.config import ZineConfig
from zinewire.templates import THEMES_DIR
print(f"zinewire loaded, THEMES_DIR={THEMES_DIR}")
  `);

  // Create temp directories for builds
  pyodide.FS.mkdir("/tmp/zinewire");

  postMessage({ type: "ready" });
}

async function doBuild(markdown, configToml, mode) {
  // Write markdown to VFS
  pyodide.FS.writeFile("/tmp/zinewire/input.md", markdown);

  const buildScript = `
import sys, io, traceback

# Capture stdout (build() prints status)
_stdout = sys.stdout
sys.stdout = io.StringIO()

try:
    from zinewire import build
    from zinewire.config import ZineConfig, load_config

    config = ZineConfig()
    config_toml = ${JSON.stringify(configToml || "")}
    mode = ${JSON.stringify(mode || "print")}

    if config_toml.strip():
        import tomllib
        from zinewire.config import _TOML_LOAD_MAP
        data = tomllib.loads(config_toml)
        for section_key, section_data in data.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    field_name = _TOML_LOAD_MAP.get(key)
                    if field_name and hasattr(config, field_name):
                        setattr(config, field_name, value)
            else:
                field_name = _TOML_LOAD_MAP.get(section_key)
                if field_name and hasattr(config, field_name):
                    setattr(config, section_key, section_data)

    config.mode = mode

    html = build(
        source="/tmp/zinewire/input.md",
        output="/tmp/zinewire/output.html",
        config=config,
    )

    # Count pages
    page_count = html.count('<div class="page')
    result = {"html": html, "pages": page_count, "error": None}
except Exception as e:
    tb = traceback.format_exc()
    result = {"html": "", "pages": 0, "error": str(e), "traceback": tb}
finally:
    sys.stdout = _stdout

result
  `;

  const result = pyodide.runPython(buildScript).toJs({ dict_converter: Object.fromEntries });

  if (result.error) {
    postMessage({
      type: "error",
      message: result.error,
      traceback: result.traceback || "",
    });
  } else {
    postMessage({
      type: "result",
      html: result.html,
      pages: result.pages,
      mode: mode,
    });
  }
}

self.onmessage = async function (e) {
  const { type } = e.data;

  if (type === "init") {
    try {
      await init(e.data.sources, e.data.themes);
    } catch (err) {
      postMessage({ type: "error", message: err.message, traceback: err.stack });
    }
  } else if (type === "build") {
    try {
      await doBuild(e.data.markdown, e.data.config, e.data.mode);
    } catch (err) {
      postMessage({ type: "error", message: err.message, traceback: err.stack });
    }
  }
};
