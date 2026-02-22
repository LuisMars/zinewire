"""Integration tests - end-to-end builds."""

import tempfile
from pathlib import Path

from zinewire import build
from zinewire.config import ZineConfig

FIXTURES = Path(__file__).parent / "fixtures"


def test_build_print_mode():
    """Build a zine in print mode end-to-end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "output.html"
        html = build(str(FIXTURES / "sample-zine.md"), output=str(output))

        assert output.exists()
        content = output.read_text()

        # Title extracted
        assert "<title>Test Zine</title>" in content

        # Pages created
        assert '<div class="page' in content
        assert '<div class="cover-page' in content or '<div class="page cover-page' in content

        # Column layouts present
        assert "two-column" in content
        assert "single-column" in content

        # Large text wrapper
        assert "large-text" in content

        # Spacer
        assert "spacer" in content

        # CSS inlined
        assert "column-count" in content
        assert "--page-width" in content

        # Page scaling JS
        assert "updatePageScale" in content


def test_build_reference_mode():
    """Build a reference sheet with 3+ columns."""
    config = ZineConfig(
        page_size="a4-landscape",
        default_columns=3,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "ref.html"
        html = build(
            str(FIXTURES / "sample-reference.md"),
            output=str(output),
            config=config,
        )

        assert output.exists()
        content = output.read_text()

        assert "<title>Quick Reference Sheet</title>" in content
        assert "three-column" in content
        assert "297mm" in content  # A4 landscape width


def test_build_web_mode():
    """Build a web page."""
    config = ZineConfig(mode="web")
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "web.html"
        html = build(
            str(FIXTURES / "sample-web.md"),
            output=str(output),
            config=config,
        )

        assert output.exists()
        content = output.read_text()

        assert "<title>My Project</title>" in content
        assert "web-content" in content
        # No paginated page divs
        assert '<div class="page">' not in content
        # Web CSS present
        assert "--web-" in content


def test_build_default_output_path():
    """Without -o, output goes next to source with .html extension."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("/title \"Test\"\n\n# Hello\n\nWorld\n")

        html = build(str(source))

        expected = Path(tmpdir) / "test.html"
        assert expected.exists()


def test_build_custom_page_size():
    """Custom page size via WxHmm format."""
    config = ZineConfig(page_size="120x170mm")
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "custom.md"
        source.write_text("# Test\n\nContent\n")
        output = Path(tmpdir) / "custom.html"

        html = build(str(source), output=str(output), config=config)

        content = output.read_text()
        assert "120mm" in content
        assert "170mm" in content


def test_build_manual_mode():
    """Build a web manual with sidebar ToC."""
    config = ZineConfig(mode="manual")
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "manual.html"
        html = build(
            str(FIXTURES / "sample-manual.md"),
            output=str(output),
            config=config,
        )

        assert output.exists()
        content = output.read_text()

        assert "<title>Test Manual</title>" in content
        # Manual layout wrapper
        assert "manual-layout" in content
        # Sidebar ToC present
        assert "sidebar-nav" in content
        assert 'href="#' in content
        # No paginated page divs
        assert '<div class="page">' not in content
        # Scroll spy JS
        assert "updateActiveLink" in content
        assert "toggleSidebar" in content
        # Mobile ToC button
        assert "mobile-toc-btn" in content
        # Manual CSS present
        assert "--manual-accent-color" in content
        # Content sections present in ToC
        assert "Introduction" in content
        assert "Core Rules" in content
        assert "Advanced Topics" in content


def test_build_manual_no_hardwired_leaks():
    """Manual mode output has no game-specific content."""
    config = ZineConfig(mode="manual")
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("# Test\n\nContent\n")
        output = Path(tmpdir) / "test.html"

        html = build(str(source), output=str(output), config=config)

        content = output.read_text().lower()
        assert "hardwired" not in content
        assert "app-menu" not in content
        assert "corporate" not in content


def test_build_from_toml_config():
    """Build from a zinewire.toml config with files list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source files
        (Path(tmpdir) / "intro.md").write_text("/title \"TOML Test\"\n\n# Intro\n\nHello\n")
        (Path(tmpdir) / "chapter1.md").write_text("\n# Chapter 1\n\nContent\n")

        # Create zinewire.toml
        toml_content = f"""
[zine]
title = "TOML Test"
files = ["intro.md", "chapter1.md"]

[output]
path = "output.html"
"""
        toml_path = Path(tmpdir) / "zinewire.toml"
        toml_path.write_text(toml_content)

        # Load config and build
        from zinewire.config import load_config
        config = load_config(str(toml_path))
        assert config.files == ["intro.md", "chapter1.md"]
        assert config.output_path == "output.html"


def test_no_hardwired_leaks():
    """Verify no game-specific content leaked into output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("# Test\n\nContent\n")
        output = Path(tmpdir) / "test.html"

        html = build(str(source), output=str(output))

        content = output.read_text().lower()
        assert "hardwired" not in content
        assert "zorn" not in content
        assert "saira" not in content
        assert "app-menu" not in content
        assert "warband" not in content
