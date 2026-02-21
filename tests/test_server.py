"""Tests for the dev server and TOML write support."""

import json
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from zinewire.config import ZineConfig, _toml_encode, load_config
from zinewire.server import DevServer, FileWatcher


# ---------------------------------------------------------------------------
# _toml_encode tests
# ---------------------------------------------------------------------------

def test_toml_encode_string():
    assert _toml_encode("hello") == '"hello"'


def test_toml_encode_string_with_quotes():
    assert _toml_encode('say "hi"') == '"say \\"hi\\""'


def test_toml_encode_int():
    assert _toml_encode(3) == "3"


def test_toml_encode_bool():
    assert _toml_encode(True) == "true"
    assert _toml_encode(False) == "false"


def test_toml_encode_list():
    assert _toml_encode(["a", "b"]) == '["a", "b"]'


def test_toml_encode_empty_list():
    assert _toml_encode([]) == "[]"


# ---------------------------------------------------------------------------
# ZineConfig.to_dict / save_toml tests
# ---------------------------------------------------------------------------

def test_config_to_dict():
    config = ZineConfig(title="Test", mode="landing")
    d = config.to_dict()
    assert d["title"] == "Test"
    assert d["mode"] == "landing"
    assert d["page_size"] == "a5"
    assert isinstance(d["files"], list)


def test_config_save_toml_only_non_defaults():
    """save_toml only writes fields that differ from defaults."""
    config = ZineConfig(title="My Zine", color_accent="#ff0000")
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        path = f.name
    config.save_toml(path)
    content = Path(path).read_text()
    assert 'title = "My Zine"' in content
    assert 'color-accent = "#ff0000"' in content
    # Default values should not appear
    assert "page-size" not in content
    assert "font-heading" not in content


def test_config_save_load_roundtrip():
    """Save config to TOML and load it back — values should match."""
    config = ZineConfig(
        title="Roundtrip Test",
        page_size="a4-landscape",
        default_columns=3,
        mode="manual",
        compact=True,
        color_accent="#ff0000",
        margin_vertical="15mm",
    )
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        path = f.name
    config.save_toml(path)
    loaded = load_config(path)
    assert loaded.title == "Roundtrip Test"
    assert loaded.page_size == "a4-landscape"
    assert loaded.default_columns == 3
    assert loaded.mode == "manual"
    assert loaded.compact is True
    assert loaded.color_accent == "#ff0000"
    assert loaded.margin_vertical == "15mm"


# ---------------------------------------------------------------------------
# FileWatcher tests
# ---------------------------------------------------------------------------

def test_file_watcher_detects_change():
    """FileWatcher calls callback when file mtime changes."""
    changed = threading.Event()
    changed_path = [None]

    def on_change(path):
        changed_path[0] = path
        changed.set()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Test\n")
        path = Path(f.name)

    watcher = FileWatcher(paths=[path], callback=on_change, interval=0.1)
    watcher.start()

    time.sleep(0.3)  # Let watcher take initial snapshot
    path.write_text("# Updated\n")

    assert changed.wait(timeout=3), "FileWatcher did not detect change"
    assert changed_path[0] == path.resolve()

    watcher.stop()


def test_file_watcher_no_false_triggers():
    """FileWatcher does not trigger when files are unchanged."""
    triggered = threading.Event()

    def on_change(path):
        triggered.set()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Static\n")
        path = Path(f.name)

    watcher = FileWatcher(paths=[path], callback=on_change, interval=0.1)
    watcher.start()

    time.sleep(0.5)
    assert not triggered.is_set(), "FileWatcher triggered without changes"

    watcher.stop()


# ---------------------------------------------------------------------------
# DevServer integration tests
# ---------------------------------------------------------------------------

def _start_server_background(source_path, port=0):
    """Start a DevServer in a background thread, return (server, thread)."""
    server = DevServer(
        source=str(source_path),
        port=port,
        auto_open=False,
    )
    # Run initial build synchronously
    server._do_rebuild()

    # Start HTTP server in background
    from zinewire.server import _ThreadingHTTPServer, _DevHandler
    http_server = _ThreadingHTTPServer(("", 0), _DevHandler)
    http_server.dev_server = server
    server.port = http_server.server_address[1]

    thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)  # Let server bind

    return server, http_server, thread


def test_server_serves_preview():
    """Server serves built HTML at /."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("# Hello Server\n\nTest content.\n")

        server, http_server, thread = _start_server_background(source)
        try:
            resp = urllib.request.urlopen(f"http://localhost:{server.port}/")
            html = resp.read().decode()

            assert "Hello Server" in html
            assert "/_events" in html  # Live reload script injected
        finally:
            http_server.shutdown()


def test_server_config_api_get():
    """GET /_api/config returns current config as JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("# API Test\n\nContent.\n")

        server, http_server, thread = _start_server_background(source)
        try:
            resp = urllib.request.urlopen(f"http://localhost:{server.port}/_api/config")
            data = json.loads(resp.read())

            assert data["page_size"] == "a5"
            assert "_page_sizes" in data
            assert "_modes" in data
            assert "print" in data["_modes"]
            assert "manual" in data["_modes"]
        finally:
            http_server.shutdown()


def test_server_config_api_post():
    """POST /_api/config updates config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("# Post Test\n\nContent.\n")

        server, http_server, thread = _start_server_background(source)
        try:
            body = json.dumps({"page_size": "a4-landscape"}).encode()
            req = urllib.request.Request(
                f"http://localhost:{server.port}/_api/config",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())

            assert data["page_size"] == "a4-landscape"
            assert server.config.page_size == "a4-landscape"
        finally:
            http_server.shutdown()


def test_server_config_page():
    """GET /_config serves the config editor page."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("# Config Page Test\n\nContent.\n")

        server, http_server, thread = _start_server_background(source)
        try:
            resp = urllib.request.urlopen(f"http://localhost:{server.port}/_config")
            html = resp.read().decode()

            assert "zinewire" in html
            assert "config" in html.lower()
            assert "Save" in html
            assert "iframe" in html
        finally:
            http_server.shutdown()


def test_server_rebuild_api():
    """POST /_api/rebuild triggers a rebuild."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("# Rebuild Test\n\nContent.\n")

        server, http_server, thread = _start_server_background(source)
        try:
            initial_count = server._build_count
            req = urllib.request.Request(
                f"http://localhost:{server.port}/_api/rebuild",
                data=b"",
                method="POST",
            )
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())

            assert data["status"] == "rebuilding"
            time.sleep(0.5)  # Wait for debounced rebuild
            assert server._build_count > initial_count
        finally:
            http_server.shutdown()
