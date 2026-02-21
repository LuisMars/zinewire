"""Tests for configuration and TOML loading."""

import tempfile
from pathlib import Path

from zinewire.config import ZineConfig, load_config


def test_default_config():
    """Default config has sensible values."""
    config = ZineConfig()
    assert config.page_size == "a5"
    assert config.default_columns == 2
    assert config.mode == "print"
    assert config.compact is False
    assert config.files == []


def test_page_dimensions_preset():
    """Preset page sizes resolve correctly."""
    config = ZineConfig(page_size="a5")
    assert config.page_dimensions == ("148mm", "210mm")

    config = ZineConfig(page_size="a4-landscape")
    assert config.page_dimensions == ("297mm", "210mm")


def test_page_dimensions_custom():
    """Custom WxHmm page sizes resolve correctly."""
    config = ZineConfig(page_size="120x170mm")
    assert config.page_dimensions == ("120mm", "170mm")


def test_load_config_basic():
    """Load a basic TOML config."""
    toml_content = """
[zine]
title = "Test Zine"
page-size = "a4-landscape"
columns = 3
mode = "manual"
compact = true
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.title == "Test Zine"
    assert config.page_size == "a4-landscape"
    assert config.default_columns == 3
    assert config.mode == "manual"
    assert config.compact is True


def test_load_config_theme():
    """TOML theme section maps to config fields."""
    toml_content = """
[theme]
font-heading = "Roboto"
font-body = "Georgia"
color-accent = "#ff0000"
color-text = "#222"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.font_heading == "Roboto"
    assert config.font_body == "Georgia"
    assert config.color_accent == "#ff0000"
    assert config.color_text == "#222"


def test_load_config_margins():
    """TOML margins section maps correctly."""
    toml_content = """
[margins]
vertical = "15mm"
horizontal = "10mm"
spine = "14mm"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.margin_vertical == "15mm"
    assert config.margin_horizontal == "10mm"
    assert config.margin_spine == "14mm"


def test_load_config_output():
    """TOML output section maps correctly."""
    toml_content = """
[output]
path = "build/manual.html"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.output_path == "build/manual.html"


def test_load_config_files_list():
    """TOML files list is loaded into config."""
    toml_content = """
[zine]
title = "Multi-File Zine"
files = ["intro.md", "chapter*.md", "appendix.md"]
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.files == ["intro.md", "chapter*.md", "appendix.md"]


def test_load_config_not_found():
    """Loading a nonexistent config raises FileNotFoundError."""
    try:
        load_config("/nonexistent/path.toml")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_load_config_unknown_keys_ignored():
    """Unknown TOML keys are silently ignored."""
    toml_content = """
[zine]
title = "Test"
unknown-key = "value"

[custom-section]
foo = "bar"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.title == "Test"


def test_manual_mode_config():
    """Manual mode can be configured."""
    config = ZineConfig(mode="manual")
    assert config.mode == "manual"


def test_accent_color_default():
    """Accent color has a default."""
    config = ZineConfig()
    assert config.color_accent == "#2563EB"


def test_font_size_defaults_empty():
    """Font size fields default to empty (use CSS defaults)."""
    config = ZineConfig()
    assert config.font_size_body == ""
    assert config.font_size_h1 == ""
    assert config.font_size_h2 == ""
    assert config.font_size_h3 == ""
    assert config.font_size_h4 == ""


def test_page_number_defaults_empty():
    """Page number fields default to empty (use CSS defaults)."""
    config = ZineConfig()
    assert config.page_number_color == ""
    assert config.page_number_size == ""
    assert config.page_number_font == ""


def test_column_justify_default_empty():
    """Column justify defaults to empty (uses space-between in CSS)."""
    config = ZineConfig()
    assert config.column_justify == ""


def test_custom_css_default_empty():
    """Custom CSS defaults to empty."""
    config = ZineConfig()
    assert config.custom_css == ""


def test_load_config_font_sizes():
    """TOML font size fields load correctly."""
    toml_content = """
[theme]
font-size-body = "10pt"
font-size-h1 = "16pt"
font-size-h2 = "13pt"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.font_size_body == "10pt"
    assert config.font_size_h1 == "16pt"
    assert config.font_size_h2 == "13pt"
    assert config.font_size_h3 == ""  # not set


def test_load_config_page_numbers():
    """TOML page number fields load correctly."""
    toml_content = """
[theme]
page-number-color = "#999"
page-number-size = "8pt"
page-number-font = "Courier"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.page_number_color == "#999"
    assert config.page_number_size == "8pt"
    assert config.page_number_font == "Courier"


def test_load_config_column_justify():
    """TOML column-justify loads correctly."""
    toml_content = """
[theme]
column-justify = "flex-start"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.column_justify == "flex-start"


def test_load_config_custom_css():
    """TOML custom-css loads correctly."""
    toml_content = """
[theme]
custom-css = "my-style.css"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write(toml_content)
        f.flush()

        config = load_config(f.name)

    assert config.custom_css == "my-style.css"


def test_save_toml_font_sizes():
    """Font sizes are saved to TOML only when non-default."""
    config = ZineConfig(font_size_body="10pt", font_size_h1="16pt")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        config.save_toml(f.name)
        content = Path(f.name).read_text()

    assert 'font-size-body = "10pt"' in content
    assert 'font-size-h1 = "16pt"' in content
    assert "font-size-h2" not in content  # still default (empty)


def test_save_toml_page_numbers():
    """Page number config is saved to TOML."""
    config = ZineConfig(page_number_color="#abc")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        config.save_toml(f.name)
        content = Path(f.name).read_text()

    assert 'page-number-color = "#abc"' in content
