"""Configuration for zinewire builds."""

import tomllib
from dataclasses import dataclass, field, fields as dataclass_fields
from pathlib import Path
from typing import Optional


# Page size presets: (width, height) in mm
# ISO A-series: each size is the previous folded in half
# US sizes: letter and its folds
PAGE_SIZES = {
    # ISO A-series
    "a4": ("210mm", "297mm"),
    "a5": ("148mm", "210mm"),          # A4 folded in half
    "a6": ("105mm", "148mm"),          # A4 folded in quarters
    "a7": ("74mm", "105mm"),           # A4 folded in eighths — classic mini-zine
    # US sizes
    "letter": ("215.9mm", "279.4mm"),
    "half-letter": ("139.7mm", "215.9mm"),   # Letter folded in half
    "quarter-letter": ("107.95mm", "139.7mm"),  # Letter folded in quarters
    "eighth-letter": ("69.85mm", "107.95mm"),   # Letter folded in eighths
    # Aliases
    "digest": ("139.7mm", "215.9mm"),  # Same as half-letter
    # Landscape variants
    "a4-landscape": ("297mm", "210mm"),
    "a5-landscape": ("210mm", "148mm"),
    "a6-landscape": ("148mm", "105mm"),
}


@dataclass
class ZineConfig:
    """Configuration for a zinewire build."""

    # Document
    title: str = "Untitled Zine"
    version: str = ""
    page_size: str = "a5"
    default_columns: int = 2
    mode: str = "print"  # "print", "landing", or "manual"
    compact: bool = False

    # Theme - fonts
    font_heading: str = "Montserrat"
    font_body: str = "PT Serif"
    font_mono: str = "Ubuntu Mono"

    # Theme - font sizes (empty = use defaults from base.css)
    font_size_body: str = ""
    font_size_h1: str = ""
    font_size_h2: str = ""
    font_size_h3: str = ""
    font_size_h4: str = ""

    # Theme - colors
    color_text: str = "#1a1a1a"
    color_border: str = "#333"
    color_bg_muted: str = "#f5f5f5"
    color_text_muted: str = "#666"
    color_table_header_bg: str = "#000"
    color_table_header_text: str = "#fff"
    color_accent: str = "#2563EB"

    # Page numbers (empty = use defaults)
    page_number_color: str = ""
    page_number_size: str = ""
    page_number_font: str = ""

    # Layout
    column_justify: str = ""  # justify-content for 3-5 column layouts

    # Page margins
    margin_vertical: str = "10mm"
    margin_horizontal: str = "8mm"
    margin_spine: str = "12mm"

    # Source files (for multi-file builds via TOML config)
    files: list[str] = field(default_factory=list)

    # Custom CSS file (path relative to TOML config)
    custom_css: str = ""

    # Output
    output_path: Optional[str] = None
    booklet: bool = False
    mini_zine: bool = False

    # Dev
    dev_mode: bool = False

    @property
    def page_dimensions(self) -> tuple[str, str]:
        """Return (width, height) CSS values for the configured page size."""
        key = self.page_size.lower()
        if key in PAGE_SIZES:
            return PAGE_SIZES[key]
        # Custom: "WxHmm" format (e.g. "120x170mm" or "120mmx170mm")
        if "x" in key:
            w, h = key.split("x", 1)
            w = w.strip()
            h = h.strip()
            if not w.endswith("mm"):
                w += "mm"
            if not h.endswith("mm"):
                h += "mm"
            return (w, h)
        return PAGE_SIZES["a5"]

    @property
    def page_width_px(self) -> float:
        """Page width in pixels at 96dpi (for JS scaling)."""
        w, _ = self.page_dimensions
        mm = float(w.replace("mm", ""))
        return round(mm * 96 / 25.4)

    def to_dict(self) -> dict:
        """Convert config to a JSON-serializable dict."""
        return {f.name: getattr(self, f.name) for f in dataclass_fields(self)}

    def save_toml(self, path: str | Path) -> None:
        """Save config to a TOML file.

        Only writes fields that differ from defaults, grouped into sections.
        """
        path = Path(path)
        defaults = ZineConfig()
        sections: dict[str, list[str]] = {}

        for field_name, (section, toml_key) in _FIELD_TOML_MAP.items():
            value = getattr(self, field_name)
            default_value = getattr(defaults, field_name)
            if value != default_value:
                if section not in sections:
                    sections[section] = []
                sections[section].append(f"{toml_key} = {_toml_encode(value)}")

        lines = []
        for section_name in ["zine", "theme", "margins", "output", "dev"]:
            if section_name in sections:
                lines.append(f"[{section_name}]")
                lines.extend(sections[section_name])
                lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")


def _toml_encode(value) -> str:
    """Encode a Python value as a TOML value string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        items = ", ".join(_toml_encode(v) for v in value)
        return f"[{items}]"
    return f'"{value}"'


# Reverse map: field_name → (section, toml_key)
_FIELD_TOML_MAP = {
    "title": ("zine", "title"),
    "version": ("zine", "version"),
    "page_size": ("zine", "page-size"),
    "default_columns": ("zine", "columns"),
    "mode": ("zine", "mode"),
    "compact": ("zine", "compact"),
    "files": ("zine", "files"),
    "font_heading": ("theme", "font-heading"),
    "font_body": ("theme", "font-body"),
    "font_mono": ("theme", "font-mono"),
    "color_text": ("theme", "color-text"),
    "color_border": ("theme", "color-border"),
    "color_bg_muted": ("theme", "color-bg-muted"),
    "color_text_muted": ("theme", "color-text-muted"),
    "color_table_header_bg": ("theme", "color-table-header-bg"),
    "color_table_header_text": ("theme", "color-table-header-text"),
    "color_accent": ("theme", "color-accent"),
    "font_size_body": ("theme", "font-size-body"),
    "font_size_h1": ("theme", "font-size-h1"),
    "font_size_h2": ("theme", "font-size-h2"),
    "font_size_h3": ("theme", "font-size-h3"),
    "font_size_h4": ("theme", "font-size-h4"),
    "page_number_color": ("theme", "page-number-color"),
    "page_number_size": ("theme", "page-number-size"),
    "page_number_font": ("theme", "page-number-font"),
    "column_justify": ("theme", "column-justify"),
    "custom_css": ("theme", "custom-css"),
    "margin_vertical": ("margins", "vertical"),
    "margin_horizontal": ("margins", "horizontal"),
    "margin_spine": ("margins", "spine"),
    "output_path": ("output", "path"),
    "booklet": ("output", "booklet"),
    "mini_zine": ("output", "mini-zine"),
    "dev_mode": ("dev", "dev"),
}


# TOML key → ZineConfig field mapping (for loading)
_TOML_LOAD_MAP = {
    # [zine] section
    "title": "title",
    "version": "version",
    "page-size": "page_size",
    "columns": "default_columns",
    "mode": "mode",
    "compact": "compact",
    "files": "files",
    # [theme] section
    "font-heading": "font_heading",
    "font-body": "font_body",
    "font-mono": "font_mono",
    "color-text": "color_text",
    "color-border": "color_border",
    "color-bg-muted": "color_bg_muted",
    "color-text-muted": "color_text_muted",
    "color-table-header-bg": "color_table_header_bg",
    "color-table-header-text": "color_table_header_text",
    "color-accent": "color_accent",
    "font-size-body": "font_size_body",
    "font-size-h1": "font_size_h1",
    "font-size-h2": "font_size_h2",
    "font-size-h3": "font_size_h3",
    "font-size-h4": "font_size_h4",
    "page-number-color": "page_number_color",
    "page-number-size": "page_number_size",
    "page-number-font": "page_number_font",
    "column-justify": "column_justify",
    "custom-css": "custom_css",
    # [margins] section
    "vertical": "margin_vertical",
    "horizontal": "margin_horizontal",
    "spine": "margin_spine",
    # [output] section
    "path": "output_path",
    "booklet": "booklet",
    "mini-zine": "mini_zine",
    # [dev] section
    "dev": "dev_mode",
}


def load_config(path: str | Path | None = None) -> ZineConfig:
    """Load configuration from a TOML file.

    If no path is given, looks for zinewire.toml in the current directory.

    TOML format:
        [zine]
        title = "My Zine"
        page-size = "a5"
        columns = 2
        mode = "print"
        compact = false
        files = ["intro.md", "chapter1.md", "chapter2.md"]

        [theme]
        font-heading = "Montserrat"
        font-body = "PT Serif"
        color-accent = "#c9a227"

        [margins]
        vertical = "10mm"
        horizontal = "8mm"
        spine = "12mm"

        [output]
        path = "build/output.html"
    """
    if path is None:
        path = Path("zinewire.toml")
    else:
        path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        data = tomllib.load(f)

    config = ZineConfig()

    # Flatten sections into config fields
    for section_key, section_data in data.items():
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                field_name = _TOML_LOAD_MAP.get(key)
                if field_name and hasattr(config, field_name):
                    setattr(config, field_name, value)
        else:
            # Top-level keys
            field_name = _TOML_LOAD_MAP.get(section_key)
            if field_name and hasattr(config, field_name):
                setattr(config, field_name, section_data)

    return config
