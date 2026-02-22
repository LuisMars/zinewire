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
    if (window !== window.top) return;  // Skip in iframes (config page manages reload)
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
@media print {
    .spread { box-shadow: none; margin: 0; break-inside: avoid; }
    .spread .page:first-child { border-right: none; }
    .spread-blank { display: none; }
}
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
        self._mode_html = {}  # {"print": html, "manual": html, "web": html}
        self._imp_html = {}   # {"booklet": html, "mini": html, ...}
        self._current_html = None  # backward compat: points to default mode
        self._dirty_modes = set()  # modes needing rebuild

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
        print(f"  Web:      {url}/web")
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

    def _do_rebuild(self, modes=None, notify=True):
        import copy
        from . import build as do_build

        if modes is None:
            # Only build print; mark others as stale for lazy rebuild
            modes = ("print",)
            self._dirty_modes = {"manual", "web"}
            self._imp_html.clear()

        # Resolve base directory for relative paths (tables, custom CSS)
        base_dir = str(Path(self.config_path).parent) if self.config_path else None

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
                html = do_build(source, output=str(out), config=mode_config, base_dir=base_dir)
                self._mode_html[mode] = html
                self._dirty_modes.discard(mode)

            self._current_html = self._mode_html.get("print")
            self._build_count += 1
            self._last_error = None
            if notify:
                self._notify_sse()
        except Exception as e:
            self._last_error = str(e)
            print(f"  Build error: {e}")

    def get_mode_html(self, mode):
        """Get cached HTML for a mode, rebuilding lazily if stale."""
        if mode in self._dirty_modes or mode not in self._mode_html:
            self._do_rebuild(modes=(mode,), notify=False)
        return self._mode_html.get(mode)

    def get_imposition_html(self, imposition_type):
        """Get cached imposition HTML, building lazily if needed."""
        if imposition_type in self._imp_html:
            return self._imp_html[imposition_type]
        import copy
        from . import build as do_build
        field_map = {
            "booklet": "booklet", "mini": "mini_zine",
            "trifold": "trifold",
            "french-fold": "french_fold", "micro-mini": "micro_mini",
        }
        field = field_map.get(imposition_type)
        if not field:
            return None
        base_dir = str(Path(self.config_path).parent) if self.config_path else None
        try:
            source = str(self.source)
            if self.config.files and self.config_path:
                source = self._concatenate_sources()
            imp_config = copy.copy(self.config)
            imp_config.mode = "print"
            setattr(imp_config, field, True)
            imp_config.dev_mode = True
            stem = self.output_file.stem
            out = self.output_dir / f"{stem}-{imposition_type}.html"
            html = do_build(source, output=str(out), config=imp_config, base_dir=base_dir)
            self._imp_html[imposition_type] = html
            return html
        except Exception as e:
            return f"<html><body><h1>{imposition_type} build error</h1><pre>{e}</pre></body></html>"

    def get_singles_html(self):
        """Get singles preview: plain print at reading page size, no imposition."""
        if "singles" in self._imp_html:
            return self._imp_html["singles"]
        import copy
        from . import build as do_build
        base_dir = str(Path(self.config_path).parent) if self.config_path else None
        try:
            source = str(self.source)
            if self.config.files and self.config_path:
                source = self._concatenate_sources()
            s_config = copy.copy(self.config)
            s_config.mode = "print"
            s_config.dev_mode = True
            # Singles = reading page size, no imposition.
            # Calculate reading page BEFORE clearing imposition flags.
            has_imposition = (
                self.config.booklet or self.config.mini_zine
                or self.config.trifold or self.config.french_fold
                or self.config.micro_mini
            )
            if has_imposition:
                rw, rh = self.config.reading_page_dimensions
                rw_mm = float(rw.replace("mm", ""))
                rh_mm = float(rh.replace("mm", ""))
                s_config.page_size = f"{rw_mm}x{rh_mm}mm"
            s_config.booklet = False
            s_config.mini_zine = False
            s_config.trifold = False
            s_config.french_fold = False
            s_config.micro_mini = False
            stem = self.output_file.stem
            out = self.output_dir / f"{stem}-singles.html"
            html = do_build(source, output=str(out), config=s_config, base_dir=base_dir)
            self._imp_html["singles"] = html
            return html
        except Exception as e:
            return f"<html><body><h1>Singles build error</h1><pre>{e}</pre></body></html>"

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

        # Invalidate imposition cache on any config change
        self._imp_html.clear()

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
        elif path == "/singles":
            self._serve_singles_preview()
        elif path in ("/mini", "/booklet", "/trifold", "/french-fold", "/micro-mini"):
            self._serve_imposition_preview(path.lstrip("/"))
        elif path == "/manual":
            self._serve_preview("manual")
        elif path == "/web":
            self._serve_preview("web")
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

    def _serve_preview(self, mode="print", spread=False):
        if spread:
            html = self.dev.get_mode_html(mode)
            active = "spread"
        else:
            html = self.dev.get_mode_html(mode)
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

    def _serve_singles_preview(self):
        """Serve singles preview: plain print at reading page size."""
        html = self.dev.get_singles_html()
        if html is None:
            self._send_html("<html><body><h1>Building...</h1></body></html>")
            return
        extras = _mode_switcher_html("print") + "\n" + _LIVE_RELOAD_SCRIPT
        html = html.replace("</body>", f"{extras}\n</body>")
        self._send_html(html)

    def _serve_imposition_preview(self, imposition_type):
        """Build and serve an imposition preview (cached)."""
        html = self.dev.get_imposition_html(imposition_type)
        if html is None:
            self._send_html("<html><body><h1>Building...</h1></body></html>")
            return
        # Only inject live reload + switcher for standalone views, not iframes
        extras = _mode_switcher_html("print") + "\n" + _LIVE_RELOAD_SCRIPT
        html = html.replace("</body>", f"{extras}\n</body>")
        self._send_html(html)

    def _serve_config_page(self):
        self._send_html(_config_page_html(self.dev.config))

    def _get_config(self):
        data = self.dev.config.to_dict()
        data["_page_sizes"] = list(PAGE_SIZES.keys())
        data["_modes"] = ["print", "web", "manual"]
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
    for mode in ("print", "manual", "web"):
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
    margin-bottom: 12px;
}
.panel-header h1 {
    font-size: 13px; font-weight: 700; color: #fff;
    letter-spacing: .04em;
}

.preview { flex: 1; background: #e0e0e0; display: flex; flex-direction: column; overflow: hidden; }
.preview-frame { flex: 1; overflow: auto; position: relative; }
.preview-frame iframe { position: absolute; top: 0; left: 50%; border: none; transform-origin: top center; }

/* Loading spinner */
.preview-frame .spinner {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    z-index: 5; pointer-events: none;
    display: flex; flex-direction: column; align-items: center; gap: 10px;
    transition: opacity .2s;
}
.preview-frame .spinner.hidden { opacity: 0; }
.spinner-ring {
    width: 28px; height: 28px;
    border: 3px solid #ccc; border-top-color: #666;
    border-radius: 50%;
    animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.spinner-text { font-size: 10px; color: #999; font-weight: 600; }

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

/* Size input: [number][unit] combo */
.size-input { display: flex; }
.size-input input[type="number"] {
    flex: 1; min-width: 0; width: 0;
    background: #fff; border: 1px solid #d0d0d0; color: #1a1a1a;
    border-right: none; border-radius: 4px 0 0 4px;
    padding: 3px 4px; font-size: 11px; font-family: inherit;
    -moz-appearance: textfield;
}
.size-input input[type="number"]::-webkit-inner-spin-button,
.size-input input[type="number"]::-webkit-outer-spin-button {
    -webkit-appearance: none; margin: 0;
}
.size-input input[type="number"]:focus {
    border-color: #666; outline: none;
    box-shadow: 0 0 0 2px rgba(0,0,0,.06);
}
.size-input select {
    width: auto; flex-shrink: 0;
    border: 1px solid #d0d0d0; border-radius: 0 4px 4px 0;
    padding: 3px 1px; font-size: 9px;
    background: #f5f5f5; color: #666;
    font-family: inherit; cursor: pointer;
}

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
.sub-tabs {
    display: none; align-items: center; gap: 1px;
    margin-left: 2px; padding-left: 4px;
    border-left: 1px solid #444;
}
.sub-tabs.visible { display: flex; }
.sub-tab {
    background: transparent; border: none; color: #555;
    font: 500 9px -apple-system, system-ui, sans-serif;
    padding: 3px 6px; border-radius: 3px; cursor: pointer;
    transition: all .15s;
}
.sub-tab:hover { color: #bbb; background: #333; }
.sub-tab.active { color: #ddd; background: #3a3a3a; }
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

/* Imposition description */
.imp-desc {
    margin-top: 6px; padding: 8px 10px;
    background: #f0f0f0; border-radius: 4px;
    font-size: 10px; line-height: 1.5; color: #555;
    display: none;
}
.imp-desc.visible { display: block; }
.imp-desc strong { color: #333; font-weight: 600; }
.imp-desc ol {
    margin: 4px 0 0 0; padding-left: 16px;
}
.imp-desc ol li { margin: 1px 0; }

/* Font rows */
.font-row { margin-bottom: 6px; }
.font-custom {
    margin-top: 4px; font-size: 12px;
}

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
var spinner = document.getElementById('spinner');

function showSpinner() { if (spinner) spinner.classList.remove('hidden'); }
function hideSpinner() { if (spinner) spinner.classList.add('hidden'); }

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

// Known page sizes in mm (width x height for portrait)
var _pageSizes = {
    'a4': [210, 297], 'a5': [148, 210], 'a6': [105, 148], 'a7': [74, 105],
    'letter': [216, 279], 'half-letter': [140, 216],
    'quarter-letter': [108, 140], 'eighth-letter': [70, 108],
    'digest': [140, 216]
};

// Parent print sheet for each page size (landscape: wider first)
var _parentSheets = {
    'a7': [297, 210], 'a6': [297, 210], 'a5': [297, 210], 'a4': [420, 297],
    'eighth-letter': [279, 216], 'quarter-letter': [279, 216],
    'half-letter': [279, 216], 'digest': [279, 216], 'letter': [432, 279]
};

function getContentWidthMm() {
    var ps = cfg.page_size || 'a5';
    var isLandscape = ps.endsWith('-landscape');
    var base = isLandscape ? ps.replace('-landscape', '') : ps;
    var imp = document.querySelector('[data-f="imposition"]');
    var impVal = imp ? imp.value : 'none';

    var activeTab = document.querySelector('.mode-tab.active');
    var activeMode = activeTab ? activeTab.dataset.mode : 'print';

    // Page dimensions
    var dims = _pageSizes[base] || [148, 210];
    var pw = isLandscape ? dims[1] : dims[0];
    var ph = isLandscape ? dims[0] : dims[1];

    if (activeMode !== 'print' || impVal === 'none') {
        return pw + 20;
    }

    // Singles: reading page width (page_size = sheet for all impositions)
    if (_currentSub === 'singles') {
        if (impVal === 'booklet') return pw / 2 + 20;
        if (impVal === 'mini_zine' || impVal === 'micro_mini') return pw / 4 + 20;
        if (impVal === 'trifold') return pw / 3 + 20;
        if (impVal === 'french_fold') return pw / 2 + 20;
        return pw + 20;
    }

    // Default (imposed) sub-tab: page_size IS the sheet
    return pw + 20;
}

function autoFitZoom() {
    var contentMm = getContentWidthMm();
    // Convert mm to px (96dpi: 1mm = 3.7795px)
    var contentPx = contentMm * 3.7795;
    var available = previewFrame.clientWidth;
    var fit = Math.min(100, Math.floor((available / contentPx) * 100));
    fit = Math.max(25, fit);
    zoomSlider.value = fit;
    applyZoom(fit);
}

async function loadConfig(updateRoute) {
    const r = await fetch('/_api/config');
    cfg = await r.json();
    savedCfg = {...cfg};
    populate(cfg);
    updateStatus();
    if (updateRoute) updatePreviewRoute();
}

function populate(c) {
    const f = document.getElementById('cf');
    f.querySelectorAll('input[type="text"]').forEach(el => {
        const k = el.dataset.f;
        if (k && c[k] !== undefined) el.value = c[k];
    });
    // Selects with data-f (column_justify, fonts, imposition etc.)
    f.querySelectorAll('select[data-f]').forEach(el => {
        var v = c[el.dataset.f];
        if (v === undefined) return;
        // Font selects: check if value is in preset options
        if (el.classList.contains('font-sel')) {
            var ci = el.closest('.font-row').querySelector('.font-custom');
            var hasPreset = Array.from(el.options).some(o => o.value === v && o.value !== '__custom');
            if (hasPreset) {
                el.value = v;
                if (ci) { ci.style.display = 'none'; ci.value = ''; }
            } else {
                el.value = '__custom';
                if (ci) { ci.style.display = ''; ci.value = v; }
            }
            return;
        }
        // Non-font selects: add unknown values dynamically
        if (!Array.from(el.options).some(o => o.value === v)) {
            var opt = document.createElement('option');
            opt.value = v; opt.text = v;
            el.insertBefore(opt, el.firstChild);
        }
        el.value = v;
    });
    const sel = f.querySelector('select[name="page_size"]');
    const known = c._page_sizes || [];
    var ps = c.page_size || 'a5';
    var isLandscape = ps.endsWith('-landscape');
    var baseSize = isLandscape ? ps.replace('-landscape', '') : ps;
    // Set orientation radio
    var oRadio = f.querySelector('input[name="orientation"][value="' + (isLandscape ? 'landscape' : 'portrait') + '"]');
    if (oRadio) oRadio.checked = true;
    // Set page size dropdown (without -landscape suffix)
    if (known.includes(ps) || known.includes(baseSize)) {
        sel.value = baseSize;
        document.getElementById('custom-sz').style.display = 'none';
    } else {
        sel.value = 'custom';
        document.getElementById('custom-sz').style.display = '';
        f.querySelector('input[name="page_size_custom"]').value = ps;
    }
    f.querySelectorAll('input[type="checkbox"]').forEach(el => {
        if (el.dataset.f && c[el.dataset.f] !== undefined) el.checked = c[el.dataset.f];
    });
    const rng = f.querySelector('input[name="default_columns"]');
    if (rng && c.default_columns !== undefined) {
        rng.value = c.default_columns;
        f.querySelector('output[name="col_out"]').textContent = c.default_columns;
    }
    // Map imposition booleans to imposition select
    var imp = f.querySelector('[data-f="imposition"]');
    if (imp) {
        if (c.micro_mini) imp.value = 'micro_mini';
        else if (c.mini_zine) imp.value = 'mini_zine';
        else if (c.trifold) imp.value = 'trifold';
        else if (c.french_fold) imp.value = 'french_fold';
        else if (c.booklet) imp.value = 'booklet';
        else imp.value = 'none';
    }
    // Standalone number inputs (not inside .size-input, e.g. line_height)
    f.querySelectorAll('input[type="number"][data-f]').forEach(function(inp) {
        if (inp.closest('.size-input')) return; // handled below
        var k = inp.dataset.f;
        var val = c[k];
        if (val !== undefined && val !== '') inp.value = val;
        else inp.value = '';
    });
    // Size inputs: parse "10mm" → number=10, unit="mm"
    f.querySelectorAll('.size-input').forEach(function(si) {
        var inp = si.querySelector('input[type="number"]');
        var sel = si.querySelector('select');
        var k = inp.dataset.f;
        var val = c[k];
        if (!val) { inp.value = ''; sel.value = sel.options[0].value; return; }
        var m = String(val).match(/^([0-9]*\\.?[0-9]+)\\s*(.+)$/);
        if (m) { inp.value = m[1]; sel.value = m[2]; }
        else { inp.value = val; }
    });
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
    f.querySelectorAll('select[data-f]').forEach(el => {
        if (el.dataset.f === 'imposition') return; // handled below
        var val = el.value;
        // Font selects: use custom input value when Custom... is selected
        if (el.classList.contains('font-sel') && val === '__custom') {
            var ci = el.closest('.font-row').querySelector('.font-custom');
            val = ci ? ci.value : '';
        }
        d[el.dataset.f] = val;
    });
    const sel = f.querySelector('select[name="page_size"]');
    var ps = sel.value === 'custom' ? f.querySelector('input[name="page_size_custom"]').value : sel.value;
    var orient = f.querySelector('input[name="orientation"]:checked');
    if (orient && orient.value === 'landscape' && !ps.endsWith('-landscape') && sel.value !== 'custom') {
        ps += '-landscape';
    }
    d.page_size = ps;
    f.querySelectorAll('input[type="checkbox"]').forEach(el => { if (el.dataset.f) d[el.dataset.f] = el.checked; });
    const rng = f.querySelector('input[name="default_columns"]');
    if (rng) d.default_columns = parseInt(rng.value);
    // Map imposition select to config booleans
    var imp = f.querySelector('[data-f="imposition"]');
    if (imp) {
        d.booklet = imp.value === 'booklet';
        d.mini_zine = imp.value === 'mini_zine';
        d.trifold = imp.value === 'trifold';
        d.french_fold = imp.value === 'french_fold';
        d.micro_mini = imp.value === 'micro_mini';
    }
    // Standalone number inputs (not inside .size-input)
    f.querySelectorAll('input[type="number"][data-f]').forEach(function(inp) {
        if (inp.closest('.size-input')) return;
        var k = inp.dataset.f;
        d[k] = inp.value || '';
    });
    // Size inputs: combine number + unit → "10mm"
    f.querySelectorAll('.size-input').forEach(function(si) {
        var inp = si.querySelector('input[type="number"]');
        var sel = si.querySelector('select');
        var k = inp.dataset.f;
        if (inp.value) d[k] = inp.value + sel.value;
        else d[k] = '';
    });
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
    if (e.target.dataset.f === 'imposition') {
        // Send config immediately then update route
        var d = collect();
        fetch('/_api/preview', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)})
        .then(function(r) { return r.json(); })
        .then(function(c) { cfg = c; updatePreviewRoute(); });
    } else {
        debouncedPreview();
    }
});

// Font select: toggle custom input visibility
document.querySelectorAll('.font-sel').forEach(function(sel) {
    sel.addEventListener('change', function() {
        var ci = sel.closest('.font-row').querySelector('.font-custom');
        if (!ci) return;
        if (sel.value === '__custom') {
            ci.style.display = '';
            ci.focus();
        } else {
            ci.style.display = 'none';
            ci.value = '';
        }
        debouncedPreview();
    });
});
// Custom font text inputs: trigger preview on typing
document.querySelectorAll('.font-custom').forEach(function(inp) {
    inp.addEventListener('input', function() { debouncedPreview(); });
});

// Imposition descriptions with orientation-aware folding instructions
function getImpDesc(impVal) {
    if (impVal === 'none') return '';
    // Get current page size info
    var ps = cfg.page_size || 'a5';
    var isLandscape = ps.endsWith('-landscape');
    var orient = isLandscape ? 'landscape' : 'portrait';
    // Sheet orientation is opposite of page: portrait pages → landscape sheet
    var sheetOrient = isLandscape ? 'portrait' : 'landscape';
    var flipEdge = isLandscape ? 'long' : 'short';

    if (impVal === 'booklet') {
        return '<strong>Saddle-stitch booklet</strong> &mdash; ' +
            '2 ' + orient + ' pages side-by-side on each ' + sheetOrient + ' sheet.' +
            '<ol>' +
            '<li>Print on <strong>' + sheetOrient + '</strong> paper, double-sided (flip on ' + flipEdge + ' edge)</li>' +
            '<li>Stack all sheets in order</li>' +
            '<li>Fold the stack in half</li>' +
            '<li>Staple twice along the fold (spine)</li>' +
            '</ol>';
    }
    if (impVal === 'mini_zine') {
        return '<strong>Mini zine</strong> &mdash; ' +
            '8 pages from one ' + orient + ' sheet using one cut and a series of folds.' +
            '<ol>' +
            '<li>Print <strong>single-sided</strong> on ' + orient + ' paper</li>' +
            '<li>Fold in half lengthwise (hot-dog fold)</li>' +
            '<li>Unfold, then fold in half widthwise (hamburger fold)</li>' +
            '<li>Fold in half widthwise again (into quarters)</li>' +
            '<li>Open to hamburger fold. Cut along the center crease from the fold to the middle only</li>' +
            '<li>Open flat, fold lengthwise again</li>' +
            '<li>Push ends inward so the cut opens into a diamond, flatten into a booklet</li>' +
            '</ol>';
    }
    if (impVal === 'trifold') {
        return '<strong>Tri-fold brochure</strong> &mdash; ' +
            '6 panels (3 per side) on one ' + orient + ' sheet.' +
            '<ol>' +
            '<li>Print <strong>double-sided</strong> on ' + orient + ' paper (flip on long edge)</li>' +
            '<li>Fold the right third inward</li>' +
            '<li>Fold the left third over the top</li>' +
            '</ol>';
    }
    if (impVal === 'french_fold') {
        return '<strong>French fold</strong> &mdash; ' +
            '4 pages from one ' + orient + ' sheet, folded twice.' +
            '<ol>' +
            '<li>Print <strong>single-sided</strong> on ' + orient + ' paper</li>' +
            '<li>Fold in half horizontally</li>' +
            '<li>Fold in half again vertically</li>' +
            '<li>The printed side faces inward; cover is on front</li>' +
            '</ol>';
    }
    if (impVal === 'micro_mini') {
        return '<strong>Micro-mini</strong> &mdash; ' +
            '16 pages from one ' + orient + ' sheet (8 per side), same fold-and-cut as mini zine but double-sided.' +
            '<ol>' +
            '<li>Print <strong>double-sided</strong> on ' + orient + ' paper (flip on ' + flipEdge + ' edge)</li>' +
            '<li>Follow the same fold-and-cut steps as a mini zine</li>' +
            '<li>Result: a tiny 16-page booklet</li>' +
            '</ol>';
    }
    return '';
}

function updateImpDesc() {
    var imp = document.querySelector('[data-f="imposition"]');
    var desc = document.getElementById('imp-desc');
    if (!imp || !desc) return;
    var html = getImpDesc(imp.value);
    desc.innerHTML = html;
    desc.classList.toggle('visible', html !== '');
}
updateImpDesc();
document.querySelector('[data-f="imposition"]').addEventListener('change', updateImpDesc);
// Also update when page size or orientation changes
document.querySelectorAll('select[name="page_size"], input[name="orientation"]').forEach(function(el) {
    el.addEventListener('change', updateImpDesc);
});

var _impositionRoutes = {
    'mini_zine': 'mini', 'booklet': 'booklet',
    'trifold': 'trifold',
    'french_fold': 'french-fold', 'micro_mini': 'micro-mini'
};

var _currentSub = 'default';  // 'default' or 'singles'

function _getImpositionValue() {
    var imp = document.querySelector('[data-f="imposition"]');
    return imp ? imp.value : 'none';
}

function _updateSubTabs() {
    var hasImp = _getImpositionValue() !== 'none';
    var subTabs = document.getElementById('sub-tabs');
    if (subTabs) subTabs.classList.toggle('visible', hasImp);
}

function _getPrintRoute() {
    var impVal = _getImpositionValue();
    if (impVal === 'none') return 'print';
    if (_currentSub === 'default') return _impositionRoutes[impVal] || 'print';
    // Singles: plain print at reading page size (no imposition)
    return 'singles';
}

function _setSubTab(sub) {
    _currentSub = sub;
    document.querySelectorAll('.sub-tab').forEach(function(t) {
        t.classList.toggle('active', t.dataset.sub === sub);
    });
}

function loadIframe(url) {
    var pf = document.getElementById('pf');
    showSpinner();
    pf.src = url;
    applyZoom(zoomSlider.value);
}

function setActiveMode(mode) {
    var route = (mode === 'print') ? _getPrintRoute() : mode;
    document.querySelectorAll('.mode-tab').forEach(function(t) {
        t.classList.toggle('active', t.dataset.mode === mode);
    });
    _updateSubTabs();
    var subTabs = document.getElementById('sub-tabs');
    if (mode !== 'print' && subTabs) subTabs.classList.remove('visible');
    loadIframe('/' + route);
}

function updatePreviewRoute() {
    _updateSubTabs();
    var activeTab = document.querySelector('.mode-tab.active');
    var activeMode = activeTab ? activeTab.dataset.mode : 'print';

    // If on print tab, reload with correct route (default vs singles)
    if (activeMode === 'print') {
        setActiveMode('print');
    }
    // manual/web tabs: no route change needed from imposition
}

// Mode tabs
document.getElementById('mode-tabs').addEventListener('click', function(e) {
    var tab = e.target.closest('.mode-tab');
    if (!tab) return;
    // When switching to Print, reset sub-tab to default if imposition exists
    if (tab.dataset.mode === 'print' && _getImpositionValue() !== 'none') {
        _setSubTab('default');
    }
    setActiveMode(tab.dataset.mode);
});

// Sub-tabs (Default / Singles)
document.getElementById('sub-tabs').addEventListener('click', function(e) {
    var tab = e.target.closest('.sub-tab');
    if (!tab) return;
    e.stopPropagation();
    _setSubTab(tab.dataset.sub);
    loadIframe('/' + _getPrintRoute());
});

// Zoom control
zoomSlider.addEventListener('input', function() { applyZoom(this.value); });
window.addEventListener('resize', function() { autoFitZoom(); });

// Single permanent iframe load handler — never overwritten
document.getElementById('pf').addEventListener('load', function() {
    hideSpinner();
    autoFitZoom();
    syncGuides();
});

// Fold/cut guides toggle
function syncGuides() {
    try {
        var pf = document.getElementById('pf');
        var show = document.getElementById('show-guides').checked;
        var body = pf.contentDocument && pf.contentDocument.body;
        if (body) body.classList.toggle('hide-guides', !show);
    } catch(e) {}
}
document.getElementById('show-guides').addEventListener('change', syncGuides);
// Safety: hide spinner after 15s regardless (prevents stuck state)
var _spinnerTimeout = null;
var _origShowSpinner = showSpinner;
showSpinner = function() {
    _origShowSpinner();
    clearTimeout(_spinnerTimeout);
    _spinnerTimeout = setTimeout(hideSpinner, 15000);
};
var _origHideSpinner = hideSpinner;
hideSpinner = function() {
    _origHideSpinner();
    clearTimeout(_spinnerTimeout);
};

// SSE for iframe reload (cache-bust to ensure fresh content)
const es = new EventSource('/_events');
es.addEventListener('reload', function() {
    var pf = document.getElementById('pf');
    var base = pf.src.split('?')[0];
    loadIframe(base + '?t=' + Date.now());
    loadConfig();
});

// Ctrl+P prints the preview iframe content, not the config page
window.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        var pf = document.getElementById('pf');
        if (pf && pf.contentWindow) pf.contentWindow.print();
    }
});

loadConfig(true);
"""


def _config_page_html(config):
    # Filter out landscape variants — we use an orientation toggle instead
    size_opts = "\n".join(
        f'<option value="{k}">{k}</option>'
        for k in PAGE_SIZES if not k.endswith("-landscape")
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
<label><span>Orientation</span><div class="radio-group">
<label><input type="radio" name="orientation" value="portrait" checked> Portrait</label>
<label><input type="radio" name="orientation" value="landscape"> Landscape</label>
</div></label>
<label><span>Default columns</span><div class="range-row"><input type="range" name="default_columns" data-f="default_columns" min="1" max="5" step="1"><output name="col_out">2</output></div></label>
<label><span>Version</span><input type="text" data-f="version" placeholder="e.g. v1.0"></label>
</fieldset>

<fieldset>
<legend>Output</legend>
<label><span>Imposition</span>
<select data-f="imposition">
<option value="none">None (single pages)</option>
<option value="booklet">Booklet (saddle-stitch)</option>
<option value="mini_zine">Mini zine (8pp, fold &amp; cut)</option>
<option value="trifold">Tri-fold (6 panels)</option>
<option value="french_fold">French fold (4pp)</option>
<option value="micro_mini">Micro-mini (16pp, double-sided)</option>
</select>
</label>
<div class="imp-desc" id="imp-desc"></div>
<label class="cb-label"><input type="checkbox" id="show-guides" checked> Show fold/cut guides</label>
</fieldset>

<fieldset>
<legend>Fonts</legend>
<div class="font-row">
<label><span>Heading</span><select class="font-sel" data-f="font_heading">
<optgroup label="Display">
<option>Montserrat</option>
<option>Saira Condensed</option>
<option>Oswald</option>
<option>Bebas Neue</option>
<option>Anton</option>
<option>Archivo Black</option>
<option>Barlow Condensed</option>
</optgroup>
<optgroup label="Sans-serif">
<option>Raleway</option>
<option>Poppins</option>
<option>Inter</option>
<option>Work Sans</option>
<option>DM Sans</option>
<option>Outfit</option>
<option>Plus Jakarta Sans</option>
<option>Rubik</option>
<option>Nunito</option>
</optgroup>
<optgroup label="Serif">
<option>Playfair Display</option>
<option>Bitter</option>
<option>Lora</option>
</optgroup>
<option value="__custom">Custom...</option>
</select></label>
<input type="text" class="font-custom" placeholder="Google Font name" style="display:none">
</div>
<div class="font-row">
<label><span>Body</span><select class="font-sel" data-f="font_body">
<optgroup label="Serif">
<option>PT Serif</option>
<option>Merriweather</option>
<option>Lora</option>
<option>Source Serif 4</option>
<option>Crimson Text</option>
<option>EB Garamond</option>
<option>Libre Baskerville</option>
<option>Cormorant Garamond</option>
<option>Noto Serif</option>
<option>Bitter</option>
</optgroup>
<optgroup label="Sans-serif">
<option>Inter</option>
<option>Open Sans</option>
<option>Roboto</option>
<option>Lato</option>
<option>Work Sans</option>
<option>DM Sans</option>
<option>Nunito</option>
<option>Source Sans 3</option>
</optgroup>
<option value="__custom">Custom...</option>
</select></label>
<input type="text" class="font-custom" placeholder="Google Font name" style="display:none">
</div>
<div class="font-row">
<label><span>Mono</span><select class="font-sel" data-f="font_mono">
<option>Ubuntu Mono</option>
<option>JetBrains Mono</option>
<option>Fira Code</option>
<option>Source Code Pro</option>
<option>IBM Plex Mono</option>
<option>Roboto Mono</option>
<option>Space Mono</option>
<option>Inconsolata</option>
<option>DM Mono</option>
<option>Courier Prime</option>
<option value="__custom">Custom...</option>
</select></label>
<input type="text" class="font-custom" placeholder="Google Font name" style="display:none">
</div>
</fieldset>

<fieldset>
<legend>Font sizes</legend>
<div class="size-grid">
<label><span>Body</span><div class="size-input"><input type="number" data-f="font_size_body" step="0.25" placeholder="9.25"><select data-u="font_size_body"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>H1</span><div class="size-input"><input type="number" data-f="font_size_h1" step="0.5" placeholder="13"><select data-u="font_size_h1"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>H2</span><div class="size-input"><input type="number" data-f="font_size_h2" step="0.5" placeholder="11"><select data-u="font_size_h2"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>H3</span><div class="size-input"><input type="number" data-f="font_size_h3" step="0.5" placeholder="10.5"><select data-u="font_size_h3"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>H4</span><div class="size-input"><input type="number" data-f="font_size_h4" step="0.5" placeholder="10"><select data-u="font_size_h4"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>Cover H1</span><div class="size-input"><input type="number" data-f="font_size_cover_h1" step="1" placeholder="38"><select data-u="font_size_cover_h1"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>Cover H2</span><div class="size-input"><input type="number" data-f="font_size_cover_h2" step="1" placeholder="24"><select data-u="font_size_cover_h2"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>Small</span><div class="size-input"><input type="number" data-f="font_size_small" step="0.25" placeholder="9"><select data-u="font_size_small"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>Tiny</span><div class="size-input"><input type="number" data-f="font_size_tiny" step="0.25" placeholder="7.75"><select data-u="font_size_tiny"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>Micro</span><div class="size-input"><input type="number" data-f="font_size_micro" step="0.25" placeholder="7"><select data-u="font_size_micro"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
</div>
</fieldset>

<fieldset>
<legend>Typography</legend>
<div class="size-grid">
<label><span>Line height</span><input type="number" data-f="line_height" step="0.05" placeholder="1.45" style="width:100%"></label>
<label><span>Para spacing</span><div class="size-input"><input type="number" data-f="paragraph_spacing" step="0.5" placeholder="2"><select data-u="paragraph_spacing"><option>mm</option><option>cm</option><option>in</option><option>pt</option></select></div></label>
<label><span>H1 spacing</span><div class="size-input"><input type="number" data-f="letter_spacing_h1" step="0.1" placeholder="1"><select data-u="letter_spacing_h1"><option>pt</option><option>px</option><option>em</option></select></div></label>
<label><span>H2 spacing</span><div class="size-input"><input type="number" data-f="letter_spacing_h2" step="0.1" placeholder="0.8"><select data-u="letter_spacing_h2"><option>pt</option><option>px</option><option>em</option></select></div></label>
<label><span>H3 spacing</span><div class="size-input"><input type="number" data-f="letter_spacing_h3" step="0.1" placeholder="0.5"><select data-u="letter_spacing_h3"><option>pt</option><option>px</option><option>em</option></select></div></label>
<label><span>H4 spacing</span><div class="size-input"><input type="number" data-f="letter_spacing_h4" step="0.1" placeholder="0.3"><select data-u="letter_spacing_h4"><option>pt</option><option>px</option><option>em</option></select></div></label>
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
<label><span>Row alt</span><div class="color-pair"><input type="color" data-cp="color_row_alt"><input type="text" data-f="color_row_alt" placeholder="#f8f9fa"></div></label>
<label><span>Row border</span><div class="color-pair"><input type="color" data-cp="color_row_border"><input type="text" data-f="color_row_border" placeholder="#e2e8f0"></div></label>
</div>
</fieldset>

<fieldset>
<legend>Margins</legend>
<div class="size-grid">
<label><span>Vertical</span><div class="size-input"><input type="number" data-f="margin_vertical" step="0.5" placeholder="10"><select data-u="margin_vertical"><option>mm</option><option>cm</option><option>in</option><option>pt</option></select></div></label>
<label><span>Horizontal</span><div class="size-input"><input type="number" data-f="margin_horizontal" step="0.5" placeholder="8"><select data-u="margin_horizontal"><option>mm</option><option>cm</option><option>in</option><option>pt</option></select></div></label>
<label><span>Spine</span><div class="size-input"><input type="number" data-f="margin_spine" step="0.5" placeholder="12"><select data-u="margin_spine"><option>mm</option><option>cm</option><option>in</option><option>pt</option></select></div></label>
</div>
</fieldset>

<fieldset>
<legend>Page numbers</legend>
<div class="size-grid">
<label><span>Color</span><div class="color-pair"><input type="color" data-cp="page_number_color"><input type="text" data-f="page_number_color" placeholder="#666"></div></label>
<label><span>Size</span><div class="size-input"><input type="number" data-f="page_number_size" step="0.5" placeholder="9"><select data-u="page_number_size"><option>pt</option><option>px</option><option>em</option><option>rem</option></select></div></label>
<label><span>Position</span><div class="size-input"><input type="number" data-f="page_number_position" step="0.5" placeholder="5"><select data-u="page_number_position"><option>mm</option><option>cm</option><option>in</option><option>pt</option></select></div></label>
</div>
<div class="font-row">
<label><span>Font</span><select class="font-sel" data-f="page_number_font">
<option value="">(heading font)</option>
<optgroup label="Display">
<option>Montserrat</option>
<option>Saira Condensed</option>
<option>Oswald</option>
<option>Bebas Neue</option>
<option>Anton</option>
</optgroup>
<optgroup label="Sans-serif">
<option>Inter</option>
<option>Poppins</option>
<option>Work Sans</option>
<option>DM Sans</option>
<option>Outfit</option>
<option>Rubik</option>
</optgroup>
<optgroup label="Serif">
<option>Playfair Display</option>
<option>Lora</option>
<option>Bitter</option>
</optgroup>
<optgroup label="Mono">
<option>JetBrains Mono</option>
<option>Fira Code</option>
<option>Source Code Pro</option>
<option>IBM Plex Mono</option>
</optgroup>
<option value="__custom">Custom...</option>
</select></label>
<input type="text" class="font-custom" placeholder="Google Font name" style="display:none">
</div>
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
<label><span>Column gap</span><div class="size-input"><input type="number" data-f="column_gap" step="0.5" placeholder="4"><select data-u="column_gap"><option>mm</option><option>cm</option><option>in</option><option>pt</option></select></div></label>
<label><span>Table padding</span><input type="text" data-f="table_padding" placeholder="0.2em 0.3em"></label>
<label><span>Table font size</span><div class="size-input"><input type="number" data-f="table_font_size" step="0.25" placeholder="tiny"><select data-u="table_font_size"><option>pt</option><option>mm</option><option>em</option></select></div></label>
<label><span>List padding</span><div class="size-input"><input type="number" data-f="list_padding" step="0.5" placeholder="2.5"><select data-u="list_padding"><option>mm</option><option>cm</option><option>in</option><option>pt</option></select></div></label>
<label><span>Custom CSS file</span><input type="text" data-f="custom_css" placeholder="style.css"></label>
</fieldset>

</form>
<div id="status" class="status">Ready</div>
</aside>
<main class="preview">
<div class="zoom-bar">
<div class="mode-tabs" id="mode-tabs">
<button type="button" class="mode-tab active" data-mode="print">Print</button>
<div class="sub-tabs" id="sub-tabs">
<button type="button" class="sub-tab active" data-sub="default">Default</button>
<button type="button" class="sub-tab" data-sub="singles">Singles</button>
</div>
<button type="button" class="mode-tab" data-mode="manual">Manual</button>
<button type="button" class="mode-tab" data-mode="web">Web</button>
</div>
<div class="zoom-controls">
<label>Zoom</label>
<input type="range" id="zoom" min="25" max="150" value="100" step="5">
<output id="zoom-out">100%</output>
</div>
</div>
<div class="preview-frame" id="preview-frame">
<div class="spinner" id="spinner"><div class="spinner-ring"></div><div class="spinner-text">Building…</div></div>
<iframe id="pf" src="/print"></iframe>
</div>
</main>
</div>
<script>{_CONFIG_JS}</script>
</body>
</html>"""
