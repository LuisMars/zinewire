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
    mode: str = "print"  # "print", "web", or "manual"

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
    page_numbers: bool = True
    page_number_color: str = ""
    page_number_size: str = ""
    page_number_font: str = ""

    # Font sizes - cover & utility (empty = use defaults from base.css)
    font_size_cover_h1: str = ""
    font_size_cover_h2: str = ""
    font_size_small: str = ""
    font_size_tiny: str = ""
    font_size_micro: str = ""

    # Colors - table rows
    color_row_alt: str = ""
    color_row_border: str = ""

    # Typography
    line_height: str = ""
    paragraph_spacing: str = ""
    letter_spacing_h1: str = ""
    letter_spacing_h2: str = ""
    letter_spacing_h3: str = ""
    letter_spacing_h4: str = ""

    # Layout
    column_justify: str = ""  # justify-content for 3-5 column layouts
    column_gap: str = ""
    table_padding: str = ""
    table_font_size: str = ""
    list_padding: str = ""
    page_number_position: str = ""

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
    trifold: bool = False
    french_fold: bool = False
    micro_mini: bool = False

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
    def print_sheet(self) -> tuple[str, str]:
        """Return the parent print sheet size (width, height) in mm strings.

        For standard sizes, returns one size up (e.g. A5 → A4).
        Orientation-aware: portrait pages → landscape sheet, landscape → portrait.
        For custom sizes, doubles the page width.
        """
        # Parent sheets for portrait pages (landscape orientation: wider first)
        _parent_sheets = {
            "a7": (297, 210),       # A7 → A4 landscape
            "a6": (297, 210),       # A6 → A4 landscape
            "a5": (297, 210),       # A5 → A4 landscape
            "a4": (420, 297),       # A4 → A3 landscape
            "eighth-letter": (279.4, 215.9),  # → Letter landscape
            "quarter-letter": (279.4, 215.9),
            "half-letter": (279.4, 215.9),
            "digest": (279.4, 215.9),
            "letter": (431.8, 279.4),  # → Tabloid landscape
        }
        ps = self.page_size.lower()
        is_landscape = ps.endswith("-landscape")
        key = ps.replace("-landscape", "")
        if key in _parent_sheets:
            w, h = _parent_sheets[key]
            if is_landscape:
                # Landscape pages → portrait sheet (swap dimensions)
                return (f"{h}mm", f"{w}mm")
            return (f"{w}mm", f"{h}mm")
        # Custom or unknown: double the page width
        pw, ph = self.page_dimensions
        pw_mm = float(pw.replace("mm", ""))
        return (f"{pw_mm * 2}mm", ph)

    @property
    def reading_page_dimensions(self) -> tuple[str, str]:
        """Return the reading page size for impositions.

        page_size = the sheet you print on. The reading page is derived
        from the sheet dimensions based on the imposition layout:
          booklet:     width/2 × height      (2 pages side by side)
          mini_zine:   width/4 × height/2    (2 rows × 4 cols)
          micro_mini:  width/4 × height/2    (4×2 grid per side)
          trifold:     width/3 × height      (3 panels per side)
          french_fold: width/2 × height/2    (2×2 grid)
          none:        page_size as-is
        """
        pw, ph = self.page_dimensions
        pw_mm = float(pw.replace("mm", ""))
        ph_mm = float(ph.replace("mm", ""))
        if self.booklet:
            return (f"{pw_mm / 2}mm", f"{ph_mm}mm")
        elif self.mini_zine or self.micro_mini:
            return (f"{pw_mm / 4}mm", f"{ph_mm / 2}mm")
        elif self.trifold:
            return (f"{round(pw_mm / 3, 4)}mm", f"{ph_mm}mm")
        elif self.french_fold:
            return (f"{pw_mm / 2}mm", f"{ph_mm / 2}mm")
        return (pw, ph)

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
    "page_numbers": ("theme", "page-numbers"),
    "page_number_color": ("theme", "page-number-color"),
    "page_number_size": ("theme", "page-number-size"),
    "page_number_font": ("theme", "page-number-font"),
    "font_size_cover_h1": ("theme", "font-size-cover-h1"),
    "font_size_cover_h2": ("theme", "font-size-cover-h2"),
    "font_size_small": ("theme", "font-size-small"),
    "font_size_tiny": ("theme", "font-size-tiny"),
    "font_size_micro": ("theme", "font-size-micro"),
    "color_row_alt": ("theme", "color-row-alt"),
    "color_row_border": ("theme", "color-row-border"),
    "line_height": ("theme", "line-height"),
    "paragraph_spacing": ("theme", "paragraph-spacing"),
    "letter_spacing_h1": ("theme", "letter-spacing-h1"),
    "letter_spacing_h2": ("theme", "letter-spacing-h2"),
    "letter_spacing_h3": ("theme", "letter-spacing-h3"),
    "letter_spacing_h4": ("theme", "letter-spacing-h4"),
    "column_justify": ("theme", "column-justify"),
    "column_gap": ("theme", "column-gap"),
    "table_padding": ("theme", "table-padding"),
    "table_font_size": ("theme", "table-font-size"),
    "list_padding": ("theme", "list-padding"),
    "page_number_position": ("theme", "page-number-position"),
    "custom_css": ("theme", "custom-css"),
    "margin_vertical": ("margins", "vertical"),
    "margin_horizontal": ("margins", "horizontal"),
    "margin_spine": ("margins", "spine"),
    "output_path": ("output", "path"),
    "booklet": ("output", "booklet"),
    "mini_zine": ("output", "mini-zine"),
    "trifold": ("output", "trifold"),
    "french_fold": ("output", "french-fold"),
    "micro_mini": ("output", "micro-mini"),
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
    "page-numbers": "page_numbers",
    "page-number-color": "page_number_color",
    "page-number-size": "page_number_size",
    "page-number-font": "page_number_font",
    "font-size-cover-h1": "font_size_cover_h1",
    "font-size-cover-h2": "font_size_cover_h2",
    "font-size-small": "font_size_small",
    "font-size-tiny": "font_size_tiny",
    "font-size-micro": "font_size_micro",
    "color-row-alt": "color_row_alt",
    "color-row-border": "color_row_border",
    "line-height": "line_height",
    "paragraph-spacing": "paragraph_spacing",
    "letter-spacing-h1": "letter_spacing_h1",
    "letter-spacing-h2": "letter_spacing_h2",
    "letter-spacing-h3": "letter_spacing_h3",
    "letter-spacing-h4": "letter_spacing_h4",
    "column-justify": "column_justify",
    "column-gap": "column_gap",
    "table-padding": "table_padding",
    "table-font-size": "table_font_size",
    "list-padding": "list_padding",
    "page-number-position": "page_number_position",
    "custom-css": "custom_css",
    # [margins] section
    "vertical": "margin_vertical",
    "horizontal": "margin_horizontal",
    "spine": "margin_spine",
    # [output] section
    "path": "output_path",
    "booklet": "booklet",
    "mini-zine": "mini_zine",
    "trifold": "trifold",
    "french-fold": "french_fold",
    "micro-mini": "micro_mini",
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
