"""Dev server with live reload and web-based config editor.

Zero external dependencies — uses only Python stdlib.
"""

import glob as glob_mod
import json
import tempfile
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn

from .config import ZineConfig, PAGE_SIZES, _FIELD_TOML_MAP, load_config


# ---------------------------------------------------------------------------
# Live-reload script (injected into preview HTML before </body>)
# ---------------------------------------------------------------------------

_LIVE_RELOAD_SCRIPT = """<script>
(function() {
    var es = new EventSource('/_events');
    es.addEventListener('reload', function() { location.reload(); });
    es.onerror = function() {
        setTimeout(function() { location.reload(); }, 2000);
    };
})();
</script>"""

_SPREAD_SCRIPT = """<script>
document.addEventListener('DOMContentLoaded', function() {
    var content = document.querySelector('.content');
    if (!content) return;
    var pages = Array.from(content.querySelectorAll('.page'));
    if (pages.length < 2) return;

    // Clear content
    content.innerHTML = '';

    // First page (cover) shown alone, right-aligned
    var first = document.createElement('div');
    first.className = 'spread';
    var blank = document.createElement('div');
    blank.className = 'spread-blank';
    first.appendChild(blank);
    first.appendChild(pages[0]);
    content.appendChild(first);

    // Pair remaining pages: [2,3], [4,5], etc.
    for (var i = 1; i < pages.length; i += 2) {
        var spread = document.createElement('div');
        spread.className = 'spread';
        spread.appendChild(pages[i]);
        if (i + 1 < pages.length) {
            spread.appendChild(pages[i + 1]);
        } else {
            var blank2 = document.createElement('div');
            blank2.className = 'spread-blank';
            spread.appendChild(blank2);
        }
        content.appendChild(spread);
    }
});
</script>
<style>
.spread {
    display: flex; justify-content: center; gap: 0;
    margin: 1em auto; box-shadow: 0 2px 8px rgba(0,0,0,.15);
    width: fit-content;
}
.spread .page {
    margin: 0 !important; box-shadow: none !important;
}
.spread-blank {
    width: var(--page-width, 148mm);
    height: var(--page-height, 210mm);
    background: #f8f8f8;
}
/* Spine shadow between pages */
.spread .page:first-child { border-right: 1px solid #ddd; }
@media print { .spread { break-inside: avoid; } }
</style>"""


# ---------------------------------------------------------------------------
# File watcher — poll-based mtime watcher
# ---------------------------------------------------------------------------

class FileWatcher:
    """Poll source files for mtime changes and trigger a callback."""

    def __init__(self, paths, callback, interval=0.5):
        self._paths = [Path(p).resolve() for p in paths]
        self._callback = callback
        self._interval = interval
        self._running = False
        self._thread = None
        self._mtimes = {}
        self._refresh_counter = 0
        self._snapshot()

    def _snapshot(self):
        for p in self._paths:
            try:
                self._mtimes[p] = p.stat().st_mtime
            except OSError:
                self._mtimes[p] = 0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def update_paths(self, paths):
        """Update the watched path list (e.g. after config change)."""
        self._paths = [Path(p).resolve() for p in paths]
        self._snapshot()

    def _poll_loop(self):
        while self._running:
            time.sleep(self._interval)
            for p in self._paths:
                try:
                    mtime = p.stat().st_mtime
                except OSError:
                    continue
                if mtime != self._mtimes.get(p, 0):
                    self._mtimes[p] = mtime
                    self._callback(p)
                    break  # One callback per cycle; debounce handles the rest


# ---------------------------------------------------------------------------
# Dev Server
# ---------------------------------------------------------------------------

class DevServer:
    """Orchestrates HTTP server, file watcher, and build loop."""

    def __init__(
        self,
        source,
        port=5555,
        config_path=None,
        config=None,
        auto_open=True,
    ):
        self.source = Path(source).resolve()
        self.port = port
        self.config_path = Path(config_path).resolve() if config_path else None
        self.auto_open = auto_open

        # Output goes into _build/ next to source
        source_dir = self.source.parent if self.source.is_file() else self.source
        self.output_dir = source_dir / "_build"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        name = self.source.with_suffix(".html").name if self.source.is_file() else "index.html"
        self.output_file = self.output_dir / name

        # Config
        if config is not None:
            self.config = config
        elif self.config_path and self.config_path.exists():
            self.config = load_config(str(self.config_path))
        else:
            self.config = ZineConfig()

        # SSE clients
        self._sse_clients = []
        self._sse_lock = threading.Lock()

        # Rebuild state
        self._rebuild_timer = None
        self._rebuild_lock = threading.Lock()
        self._build_count = 0
        self._last_error = None

        # Cached output per mode
        self._mode_html = {}  # {"print": html, "manual": html, "landing": html}
        self._current_html = None  # backward compat: points to default mode

    def start(self):
        """Start: initial build, file watcher, HTTP server."""
        self._do_rebuild()

        self._watcher = FileWatcher(
            paths=self._get_watch_paths(),
            callback=self._on_file_change,
            interval=0.5,
        )
        self._watcher.start()

        server = _ThreadingHTTPServer(("", self.port), _DevHandler)
        server.dev_server = self
        # Capture actual port (important when port=0 for tests)
        self.port = server.server_address[1]

        url = f"http://localhost:{self.port}"
        print(f"\n  zinewire dev server")
        print(f"  Print:    {url}/print")
        print(f"  Manual:   {url}/manual")
        print(f"  Landing:  {url}/landing")
        print(f"  Config:   {url}/_config")
        print(f"  Press Ctrl+C to stop\n")

        if self.auto_open:
            webbrowser.open(f"{url}/_config")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            self._watcher.stop()
            server.shutdown()

    def _get_watch_paths(self):
        paths = []
        if self.source.is_file():
            paths.append(self.source)
        elif self.source.is_dir():
            paths.extend(self.source.rglob("*.md"))
        if self.config_path and self.config_path.exists():
            paths.append(self.config_path)
        # CSS in source dir
        source_dir = self.source.parent if self.source.is_file() else self.source
        paths.extend(source_dir.rglob("*.css"))
        # Multi-file sources
        if self.config.files:
            base = self.config_path.parent if self.config_path else Path(".")
            for pattern in self.config.files:
                paths.extend(Path(p) for p in glob_mod.glob(str(base / pattern)))
        return paths

    def _on_file_change(self, changed_path):
        print(f"  Changed: {changed_path.name}")
        self._debounced_rebuild()

    def _debounced_rebuild(self, delay=0.3):
        with self._rebuild_lock:
            if self._rebuild_timer is not None:
                self._rebuild_timer.cancel()
            self._rebuild_timer = threading.Timer(delay, self._do_rebuild)
            self._rebuild_timer.daemon = True
            self._rebuild_timer.start()

    def _do_rebuild(self, modes=None):
        import copy
        from . import build as do_build

        if modes is None:
            modes = ("print", "manual", "landing")

        try:
            source = str(self.source)
            if self.config.files and self.config_path:
                source = self._concatenate_sources()

            for mode in modes:
                mode_config = copy.copy(self.config)
                mode_config.mode = mode
                mode_config.dev_mode = True
                stem = self.output_file.stem
                out = self.output_dir / f"{stem}-{mode}.html"
                html = do_build(source, output=str(out), config=mode_config)
                self._mode_html[mode] = html

            self._current_html = self._mode_html.get("print")
            self._build_count += 1
            self._last_error = None
            self._notify_sse()
        except Exception as e:
            self._last_error = str(e)
            print(f"  Build error: {e}")

    def _concatenate_sources(self):
        base_dir = self.config_path.parent if self.config_path else Path(".")
        parts = []
        for pattern in self.config.files:
            matches = sorted(glob_mod.glob(str(base_dir / pattern)))
            for match in matches:
                parts.append(Path(match).read_text(encoding="utf-8"))
        if not parts:
            raise RuntimeError("No source files found from config.")
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        tmp.write("\n\n".join(parts))
        tmp.close()
        return tmp.name

    def _notify_sse(self):
        ts = int(time.time() * 1000)
        msg = f"event: reload\ndata: {ts}\n\n".encode("utf-8")
        with self._sse_lock:
            dead = []
            for wfile in self._sse_clients:
                try:
                    wfile.write(msg)
                    wfile.flush()
                except Exception:
                    dead.append(wfile)
            for d in dead:
                self._sse_clients.remove(d)

    def register_sse(self, wfile):
        with self._sse_lock:
            self._sse_clients.append(wfile)

    def unregister_sse(self, wfile):
        with self._sse_lock:
            if wfile in self._sse_clients:
                self._sse_clients.remove(wfile)

    def update_config(self, updates, save=True):
        for key, value in updates.items():
            if key.startswith("_"):
                continue
            if hasattr(self.config, key):
                current = getattr(self.config, key)
                if isinstance(current, bool):
                    value = bool(value)
                elif isinstance(current, int):
                    value = int(value)
                setattr(self.config, key, value)

        if save:
            # Save to TOML
            if self.config_path:
                self.config.save_toml(self.config_path)
            else:
                # Create zinewire.toml next to source
                source_dir = self.source.parent if self.source.is_file() else self.source
                toml_path = source_dir / "zinewire.toml"
                self.config.save_toml(toml_path)
                self.config_path = toml_path
                print(f"  Created {toml_path}")
            # Full rebuild on save
            self._debounced_rebuild(delay=0.1)
        else:
            # Preview: only rebuild print mode for speed
            self._debounced_rebuild_single(delay=0.1)
        return self.config

    def _debounced_rebuild_single(self, delay=0.1):
        """Debounced rebuild of only print mode (for fast preview)."""
        with self._rebuild_lock:
            if self._rebuild_timer is not None:
                self._rebuild_timer.cancel()
            self._rebuild_timer = threading.Timer(
                delay, self._do_rebuild, kwargs={"modes": ("print",)}
            )
            self._rebuild_timer.daemon = True
            self._rebuild_timer.start()


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    dev_server: DevServer


class _DevHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Suppress default access log

    @property
    def dev(self):
        return self.server.dev_server

    def do_GET(self):
        # Strip query string for route matching (used for cache-busting)
        path = self.path.split("?")[0]
        if path == "/" or path == "/print":
            self._serve_preview("print")
        elif path == "/spread":
            self._serve_preview("print", spread=True)
        elif path == "/mini":
            self._serve_preview("print", mini_zine=True)
        elif path == "/manual":
            self._serve_preview("manual")
        elif path == "/landing":
            self._serve_preview("landing")
        elif path == "/_config":
            self._serve_config_page()
        elif path == "/_api/config":
            self._get_config()
        elif path == "/_events":
            self._serve_sse()
        else:
            self._serve_static()

    def do_POST(self):
        if self.path == "/_api/config":
            self._update_config()
        elif self.path == "/_api/preview":
            self._preview_config()
        elif self.path == "/_api/rebuild":
            self._trigger_rebuild()
        else:
            self.send_error(404)

    # --- Routes ---

    def _serve_preview(self, mode="print", spread=False, mini_zine=False):
        if mini_zine:
            html = self._build_mini_zine_preview()
            if html is None:
                self._send_html("<html><body><h1>Building...</h1></body></html>")
                return
            active = "mini"
        elif spread:
            html = self.dev._mode_html.get(mode) or self.dev._current_html
            active = "spread"
        else:
            html = self.dev._mode_html.get(mode) or self.dev._current_html
            active = mode

        if html is None:
            self._send_html("<html><body><h1>Building...</h1></body></html>")
            return
        switcher = _mode_switcher_html(active)
        extras = switcher + "\n" + _LIVE_RELOAD_SCRIPT
        if spread:
            extras += "\n" + _SPREAD_SCRIPT
        html = html.replace("</body>", f"{extras}\n</body>")
        self._send_html(html)

    def _build_mini_zine_preview(self):
        """Build a mini zine preview on demand from source."""
        import copy
        from . import build as do_build
        try:
            source = str(self.dev.source)
            if self.dev.config.files and self.dev.config_path:
                source = self.dev._concatenate_sources()
            mini_config = copy.copy(self.dev.config)
            mini_config.mode = "print"
            mini_config.mini_zine = True
            mini_config.dev_mode = True
            stem = self.dev.output_file.stem
            out = self.dev.output_dir / f"{stem}-minizine.html"
            return do_build(source, output=str(out), config=mini_config)
        except Exception as e:
            return f"<html><body><h1>Mini zine build error</h1><pre>{e}</pre></body></html>"

    def _serve_config_page(self):
        self._send_html(_config_page_html(self.dev.config))

    def _get_config(self):
        data = self.dev.config.to_dict()
        data["_page_sizes"] = list(PAGE_SIZES.keys())
        data["_modes"] = ["print", "landing", "manual"]
        data["_build_count"] = self.dev._build_count
        data["_last_error"] = self.dev._last_error
        self._send_json(data)

    def _update_config(self):
        body = self._read_body()
        try:
            updates = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        config = self.dev.update_config(updates, save=True)
        self._send_json(config.to_dict())

    def _preview_config(self):
        body = self._read_body()
        try:
            updates = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        config = self.dev.update_config(updates, save=False)
        self._send_json(config.to_dict())

    def _trigger_rebuild(self):
        self.dev._debounced_rebuild(delay=0)
        self._send_json({"status": "rebuilding"})

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        self.dev.register_sse(self.wfile)
        try:
            self.wfile.write(b"event: connected\ndata: ok\n\n")
            self.wfile.flush()
            while True:
                time.sleep(15)
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except Exception:
            pass
        finally:
            self.dev.unregister_sse(self.wfile)

    def _serve_static(self):
        rel_path = self.path.lstrip("/")
        if ".." in rel_path:
            self.send_error(403)
            return
        for base in [self.dev.output_dir, self.dev.source.parent]:
            candidate = base / rel_path
            if candidate.exists() and candidate.is_file():
                content = candidate.read_bytes()
                ct = _guess_content_type(candidate.suffix)
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
        self.send_error(404)

    # --- Helpers ---

    def _send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj):
        data = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------

def _mode_switcher_html(active_mode):
    """Floating mode switcher bar injected into preview pages."""
    links = []
    for mode in ("print", "spread", "mini", "manual", "landing"):
        cls = "active" if mode == active_mode else ""
        links.append(f'<a href="/{mode}" class="{cls}" data-mode="{mode}">{mode}</a>')
    links.append('<a href="/_config" class="cfg" data-mode="config">config</a>')
    return f"""<div id="zw-switcher" style="
        position:fixed;bottom:12px;right:12px;z-index:99999;
        display:flex;gap:2px;padding:3px;
        background:#1a1a1a;border-radius:6px;
        font:600 11px -apple-system,system-ui,sans-serif;
        box-shadow:0 2px 8px rgba(0,0,0,.3);
    ">{''.join(links)}</div>
    <style>
    #zw-switcher a {{
        color:#999;text-decoration:none;padding:4px 10px;border-radius:4px;
        transition:all .15s;
    }}
    #zw-switcher a:hover {{ color:#fff;background:#333; }}
    #zw-switcher a.active {{ color:#fff;background:#444; }}
    #zw-switcher a.cfg {{ color:#666;font-style:italic; }}
    #zw-switcher a.cfg:hover {{ color:#fff;background:#333; }}
    @media print {{ #zw-switcher {{ display:none !important; }} }}
    </style>
    <script>
    (function() {{
        var sw = document.getElementById('zw-switcher');
        if (window !== window.top) {{ sw.style.display = 'none'; return; }}
        sw.addEventListener('click', function(e) {{
            var a = e.target.closest('a');
            if (!a) return;
            e.preventDefault();
            if (a.dataset.mode === 'config') {{
                window.location = '/_config';
            }} else {{
                window.location = '/' + a.dataset.mode;
            }}
        }});
    }})();
    </script>"""


def _guess_content_type(suffix):
    return {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
        ".ico": "image/x-icon",
    }.get(suffix.lower(), "application/octet-stream")


# ---------------------------------------------------------------------------
# Config page HTML (self-contained with inline CSS + JS)
# ---------------------------------------------------------------------------

_CONFIG_CSS = """
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: #f0f0f0; color: #1a1a1a; font-size: 12px;
}
.layout { display: flex; height: 100vh; }

.panel {
    width: 300px; min-width: 300px; overflow-y: auto;
    background: #fafafa; border-right: 1px solid #e0e0e0;
    display: flex; flex-direction: column;
}
.panel-header {
    padding: 10px 16px; background: #1a1a1a; display: flex;
    align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 10;
}
.panel-header h1 {
    font-size: 13px; font-weight: 700; color: #fff;
    letter-spacing: .04em;
}

.preview { flex: 1; background: #e0e0e0; display: flex; flex-direction: column; overflow: hidden; }
.preview-frame { flex: 1; overflow: auto; position: relative; }
.preview-frame iframe { position: absolute; top: 0; left: 50%; border: none; transform-origin: top center; }

/* Sections */
fieldset { border: none; padding: 10px 16px 8px; }
fieldset:first-of-type { padding-top: 16px; }
fieldset + fieldset { border-top: 1px solid #e8e8e8; }
legend {
    font-size: 9px; text-transform: uppercase; letter-spacing: .08em;
    color: #888; font-weight: 600; margin-bottom: 8px; padding: 0;
    width: 100%;
}

/* Labels and inputs */
label { display: block; margin-bottom: 6px; }
label > span {
    display: block; font-size: 11px; color: #666;
    margin-bottom: 2px; font-weight: 500;
}
input[type="text"], select {
    display: block; width: 100%; padding: 5px 8px;
    background: #fff; border: 1px solid #d0d0d0; color: #1a1a1a;
    border-radius: 4px; font-size: 12px; font-family: inherit;
}
input[type="text"]:focus, select:focus {
    border-color: #666; outline: none;
    box-shadow: 0 0 0 2px rgba(0,0,0,.06);
}

/* Range */
.range-row { display: flex; align-items: center; gap: 6px; }
input[type="range"] { flex: 1; accent-color: #1a1a1a; height: 4px; }
output {
    font-size: 12px; font-weight: 700; color: #1a1a1a;
    min-width: 16px; text-align: right; font-variant-numeric: tabular-nums;
}

/* Colors */
.color-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
.color-grid label { margin-bottom: 2px; }
.color-grid label > span { font-size: 10px; }
.color-pair {
    display: flex; gap: 4px; align-items: stretch;
}
.color-pair input[type="color"] {
    width: 28px; min-width: 28px; height: 28px;
    border: 1px solid #d0d0d0; border-radius: 4px;
    cursor: pointer; background: none; padding: 1px; flex-shrink: 0;
}
.color-pair input[type="color"]:hover { border-color: #888; }
.color-pair input[type="text"] {
    flex: 1; min-width: 0; font-size: 10px; padding: 4px 5px;
    font-family: 'SF Mono', 'Menlo', monospace;
}

/* Size grid */
.size-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
.size-grid label { margin-bottom: 2px; }
.size-grid label > span { font-size: 10px; }
.size-grid input[type="text"] { font-size: 11px; padding: 4px 6px; }

/* Zoom bar */
.zoom-bar {
    display: flex; align-items: center; gap: 0;
    padding: 0; background: #1a1a1a;
    border-bottom: 1px solid #333; flex-shrink: 0;
}
.mode-tabs {
    display: flex; gap: 1px; padding: 3px 6px;
}
.mode-tab {
    background: transparent; border: none; color: #666;
    font: 600 10px -apple-system, system-ui, sans-serif;
    padding: 4px 8px; border-radius: 3px; cursor: pointer;
    transition: all .15s; text-transform: capitalize;
}
.mode-tab:hover { color: #ccc; background: #333; }
.mode-tab.active { color: #fff; background: #444; }
.zoom-controls {
    display: flex; align-items: center; gap: 6px;
    margin-left: auto; padding: 4px 8px;
}
.zoom-controls label { font-size: 10px; color: #999; margin: 0; font-weight: 600; }
.zoom-controls input[type="range"] { width: 100px; accent-color: #666; height: 3px; }
.zoom-controls output { font-size: 10px; color: #999; min-width: 32px; text-align: right; font-variant-numeric: tabular-nums; }

/* Radio */
.radio-group { display: flex; gap: 10px; }
.radio-group label {
    display: flex; align-items: center; gap: 3px;
    margin-bottom: 0; cursor: pointer; font-size: 12px;
    font-weight: 500; color: #333;
}
input[type="radio"] { accent-color: #1a1a1a; }

/* Checkbox */
.cb-label {
    display: flex; align-items: center; gap: 6px;
    cursor: pointer; font-size: 12px; color: #333;
}
input[type="checkbox"] { accent-color: #1a1a1a; }

/* Buttons */
.btn {
    padding: 5px 12px; border: none; border-radius: 4px;
    font-size: 10px; font-weight: 600; cursor: pointer;
}
.btn-preview { background: transparent; color: #999; border: 1px solid #555; }
.btn-preview:hover { color: #fff; border-color: #888; }
.btn-rebuild { background: #fff; color: #1a1a1a; border: 1px solid #ccc; }
.btn-rebuild:hover { background: #eee; }
/* Status */
.status {
    padding: 6px 16px; font-size: 10px; color: #999;
    background: #f0f0f0; text-align: center;
    position: sticky; bottom: 0; border-top: 1px solid #e8e8e8;
}
.status.error { color: #c0392b; background: #fef5f5; }
"""

_CONFIG_JS = """
let cfg = {};
let savedCfg = {};
let previewTimer = null;
var zoomSlider = document.getElementById('zoom');
var zoomOut = document.getElementById('zoom-out');
var previewFrame = document.getElementById('preview-frame');

function applyZoom(val) {
    var pf = document.getElementById('pf');
    if (!previewFrame || !pf) return;
    var pct = val / 100;
    var w = previewFrame.clientWidth / pct;
    var h = previewFrame.clientHeight / pct;
    pf.style.width = w + 'px';
    pf.style.height = h + 'px';
    pf.style.transform = 'translateX(-50%) scale(' + pct + ')';
    if (zoomOut) zoomOut.textContent = val + '%';
}

async function loadConfig() {
    const r = await fetch('/_api/config');
    cfg = await r.json();
    savedCfg = {...cfg};
    populate(cfg);
    updateStatus();
}

function populate(c) {
    const f = document.getElementById('cf');
    f.querySelectorAll('input[type="text"]').forEach(el => {
        const k = el.dataset.f;
        if (k && c[k] !== undefined) el.value = c[k];
    });
    // Selects with data-f (column_justify etc.)
    f.querySelectorAll('select[data-f]').forEach(el => {
        if (c[el.dataset.f] !== undefined) el.value = c[el.dataset.f];
    });
    const sel = f.querySelector('select[name="page_size"]');
    const known = c._page_sizes || [];
    if (known.includes(c.page_size)) {
        sel.value = c.page_size;
        document.getElementById('custom-sz').style.display = 'none';
    } else {
        sel.value = 'custom';
        document.getElementById('custom-sz').style.display = '';
        f.querySelector('input[name="page_size_custom"]').value = c.page_size;
    }
    f.querySelectorAll('input[type="checkbox"]').forEach(el => {
        if (el.dataset.f && c[el.dataset.f] !== undefined) el.checked = c[el.dataset.f];
    });
    const rng = f.querySelector('input[name="default_columns"]');
    if (rng && c.default_columns !== undefined) {
        rng.value = c.default_columns;
        f.querySelector('output[name="col_out"]').textContent = c.default_columns;
    }
    // Sync color swatches from text values
    syncColorsFromText();
}

function normalizeColor(v) {
    if (/^#[0-9a-fA-F]{3}$/.test(v)) return '#' + v[1]+v[1] + v[2]+v[2] + v[3]+v[3];
    return v;
}

function syncColorsFromText() {
    document.querySelectorAll('input[data-cp]').forEach(cp => {
        var tf = document.querySelector('input[data-f="' + cp.dataset.cp + '"]');
        if (tf && tf.value && /^#[0-9a-fA-F]{3,6}$/.test(tf.value)) {
            cp.value = normalizeColor(tf.value);
        }
    });
}

function collect() {
    const f = document.getElementById('cf');
    const d = {};
    f.querySelectorAll('input[type="text"]').forEach(el => { if (el.dataset.f) d[el.dataset.f] = el.value; });
    f.querySelectorAll('select[data-f]').forEach(el => { d[el.dataset.f] = el.value; });
    const sel = f.querySelector('select[name="page_size"]');
    d.page_size = sel.value === 'custom' ? f.querySelector('input[name="page_size_custom"]').value : sel.value;
    f.querySelectorAll('input[type="checkbox"]').forEach(el => { if (el.dataset.f) d[el.dataset.f] = el.checked; });
    const rng = f.querySelector('input[name="default_columns"]');
    if (rng) d.default_columns = parseInt(rng.value);
    return d;
}

function debouncedPreview() {
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(async function() {
        const d = collect();
        const r = await fetch('/_api/preview', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        cfg = await r.json();
        updateStatus('preview');
    }, 200);
}

async function saveConfig() {
    const d = collect();
    const r = await fetch('/_api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
    cfg = await r.json();
    savedCfg = {...cfg};
    updateStatus('saved');
}

async function resetConfig() {
    cfg = {...savedCfg};
    populate(savedCfg);
    const r = await fetch('/_api/preview', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(savedCfg)});
    cfg = await r.json();
    updateStatus();
}

function updateStatus(action) {
    const el = document.getElementById('status');
    if (cfg._last_error) {
        el.textContent = 'Error: ' + cfg._last_error;
        el.className = 'status error';
    } else if (action === 'preview') {
        el.textContent = 'Preview (unsaved)';
        el.className = 'status';
    } else if (action === 'saved') {
        el.textContent = 'Saved';
        el.className = 'status';
    } else {
        el.textContent = 'Ready';
        el.className = 'status';
    }
}

// Page size toggle
document.querySelector('select[name="page_size"]').addEventListener('change', function() {
    document.getElementById('custom-sz').style.display = this.value === 'custom' ? '' : 'none';
    debouncedPreview();
});

// Columns slider
document.querySelector('input[name="default_columns"]').addEventListener('input', function() {
    document.querySelector('output[name="col_out"]').textContent = this.value;
    debouncedPreview();
});

// Color picker <-> text input sync
document.querySelectorAll('input[data-cp]').forEach(function(cp) {
    var tf = document.querySelector('input[data-f="' + cp.dataset.cp + '"]');
    if (!tf) return;
    cp.addEventListener('input', function() {
        tf.value = cp.value;
        debouncedPreview();
    });
    tf.addEventListener('input', function() {
        if (/^#[0-9a-fA-F]{3,6}$/.test(tf.value)) cp.value = normalizeColor(tf.value);
    });
});

// Auto-preview on any form change
document.getElementById('cf').addEventListener('input', function(e) {
    if (e.target.name === 'default_columns') return; // handled above
    if (e.target.dataset && e.target.dataset.cp) return; // color picker handled above
    debouncedPreview();
});
document.getElementById('cf').addEventListener('change', function(e) {
    debouncedPreview();
    if (e.target.dataset.f === 'mini_zine' || e.target.dataset.f === 'booklet') {
        updatePreviewRoute();
    }
});

function setActiveMode(mode) {
    var pf = document.getElementById('pf');
    pf.src = '/' + mode;
    document.querySelectorAll('.mode-tab').forEach(function(t) {
        t.classList.toggle('active', t.dataset.mode === mode);
    });
    applyZoom(zoomSlider.value);
}

function updatePreviewRoute() {
    var mini = document.querySelector('[data-f="mini_zine"]');
    var booklet = document.querySelector('[data-f="booklet"]');
    if (mini && mini.checked) {
        setActiveMode('mini');
    } else if (booklet && booklet.checked) {
        setActiveMode('spread');
    } else {
        setActiveMode('print');
    }
}

// Mode tabs
document.getElementById('mode-tabs').addEventListener('click', function(e) {
    var tab = e.target.closest('.mode-tab');
    if (!tab) return;
    setActiveMode(tab.dataset.mode);
});

// Zoom control
zoomSlider.addEventListener('input', function() { applyZoom(this.value); });
window.addEventListener('resize', function() { applyZoom(zoomSlider.value); });
setTimeout(function() { applyZoom(zoomSlider.value); }, 0);

// SSE for iframe reload (cache-bust to ensure fresh content)
const es = new EventSource('/_events');
es.addEventListener('reload', function() {
    var pf = document.getElementById('pf');
    var base = pf.src.split('?')[0];
    pf.src = base + '?t=' + Date.now();
    loadConfig();
});

loadConfig();
"""


def _config_page_html(config):
    size_opts = "\n".join(
        f'<option value="{k}">{k}</option>' for k in PAGE_SIZES
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>zinewire config</title>
<style>{_CONFIG_CSS}</style>
</head>
<body>
<div class="layout">
<aside class="panel">
<header class="panel-header">
<h1>zinewire</h1>
<button class="btn btn-preview" onclick="resetConfig()">Reset</button>
<button class="btn btn-rebuild" onclick="saveConfig()">Save</button>
</header>
<form id="cf" onsubmit="return false">

<fieldset>
<legend>Document</legend>
<label><span>Title</span><input type="text" data-f="title"></label>
<label><span>Page size</span><select name="page_size">
{size_opts}
<option value="custom">Custom...</option>
</select></label>
<label id="custom-sz" style="display:none"><span>Custom (WxHmm)</span><input type="text" name="page_size_custom" placeholder="120x170mm"></label>
<label><span>Columns</span><div class="range-row"><input type="range" name="default_columns" data-f="default_columns" min="1" max="5" step="1"><output name="col_out">2</output></div></label>
<label class="cb-label"><input type="checkbox" data-f="compact"> Compact</label>
<label><span>Version</span><input type="text" data-f="version" placeholder="e.g. v1.0"></label>
</fieldset>

<fieldset>
<legend>Output</legend>
<label class="cb-label"><input type="checkbox" data-f="booklet"> Booklet (saddle-stitch)</label>
<label class="cb-label"><input type="checkbox" data-f="mini_zine"> Mini zine (fold &amp; cut)</label>
</fieldset>

<fieldset>
<legend>Fonts</legend>
<label><span>Heading</span><input type="text" data-f="font_heading"></label>
<label><span>Body</span><input type="text" data-f="font_body"></label>
<label><span>Mono</span><input type="text" data-f="font_mono"></label>
</fieldset>

<fieldset>
<legend>Font sizes</legend>
<div class="size-grid">
<label><span>Body</span><input type="text" data-f="font_size_body" placeholder="9.25pt"></label>
<label><span>H1</span><input type="text" data-f="font_size_h1" placeholder="13pt"></label>
<label><span>H2</span><input type="text" data-f="font_size_h2" placeholder="11pt"></label>
<label><span>H3</span><input type="text" data-f="font_size_h3" placeholder="10.5pt"></label>
<label><span>H4</span><input type="text" data-f="font_size_h4" placeholder="10pt"></label>
</div>
</fieldset>

<fieldset>
<legend>Colors</legend>
<div class="color-grid">
<label><span>Text</span><div class="color-pair"><input type="color" data-cp="color_text"><input type="text" data-f="color_text"></div></label>
<label><span>Border</span><div class="color-pair"><input type="color" data-cp="color_border"><input type="text" data-f="color_border"></div></label>
<label><span>Bg</span><div class="color-pair"><input type="color" data-cp="color_bg_muted"><input type="text" data-f="color_bg_muted"></div></label>
<label><span>Muted</span><div class="color-pair"><input type="color" data-cp="color_text_muted"><input type="text" data-f="color_text_muted"></div></label>
<label><span>Tbl head</span><div class="color-pair"><input type="color" data-cp="color_table_header_bg"><input type="text" data-f="color_table_header_bg"></div></label>
<label><span>Tbl text</span><div class="color-pair"><input type="color" data-cp="color_table_header_text"><input type="text" data-f="color_table_header_text"></div></label>
<label><span>Accent</span><div class="color-pair"><input type="color" data-cp="color_accent"><input type="text" data-f="color_accent"></div></label>
</div>
</fieldset>

<fieldset>
<legend>Page numbers</legend>
<div class="size-grid">
<label><span>Color</span><div class="color-pair"><input type="color" data-cp="page_number_color"><input type="text" data-f="page_number_color" placeholder="#666"></div></label>
<label><span>Size</span><input type="text" data-f="page_number_size" placeholder="9pt"></label>
<label><span>Font</span><input type="text" data-f="page_number_font" placeholder="heading font"></label>
</div>
</fieldset>

<fieldset>
<legend>Margins</legend>
<label><span>Vertical</span><input type="text" data-f="margin_vertical"></label>
<label><span>Horizontal</span><input type="text" data-f="margin_horizontal"></label>
<label><span>Spine</span><input type="text" data-f="margin_spine"></label>
</fieldset>

<fieldset>
<legend>Layout</legend>
<label><span>Column justify</span><select data-f="column_justify">
<option value="">Default (space-between)</option>
<option value="flex-start">Top (flex-start)</option>
<option value="flex-end">Bottom (flex-end)</option>
<option value="center">Center</option>
<option value="space-around">Space around</option>
<option value="space-evenly">Space evenly</option>
<option value="stretch">Stretch</option>
</select></label>
<label><span>Custom CSS file</span><input type="text" data-f="custom_css" placeholder="style.css"></label>
</fieldset>

</form>
<div id="status" class="status">Ready</div>
</aside>
<main class="preview">
<div class="zoom-bar">
<div class="mode-tabs" id="mode-tabs">
<button type="button" class="mode-tab active" data-mode="print">Print</button>
<button type="button" class="mode-tab" data-mode="spread">Spread</button>
<button type="button" class="mode-tab" data-mode="mini">Mini</button>
<button type="button" class="mode-tab" data-mode="manual">Manual</button>
<button type="button" class="mode-tab" data-mode="landing">Web</button>
</div>
<div class="zoom-controls">
<label>Zoom</label>
<input type="range" id="zoom" min="25" max="150" value="100" step="5">
<output id="zoom-out">100%</output>
</div>
</div>
<div class="preview-frame" id="preview-frame">
<iframe id="pf" src="/print"></iframe>
</div>
</main>
</div>
<script>{_CONFIG_JS}</script>
</body>
</html>"""
