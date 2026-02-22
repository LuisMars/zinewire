"""HTML document templates for zinewire."""

from pathlib import Path

from .config import ZineConfig
from .manual import generate_toc, scrollspy_script

THEMES_DIR = Path(__file__).parent / "themes"


def _font_url(font_name: str) -> str:
    """Convert font name to Google Fonts URL format."""
    return font_name.replace(" ", "+")


def _page_scaling_script(config: ZineConfig) -> str:
    """JavaScript for mobile page scaling."""
    page_width_px = config.page_width_px
    return f"""<script>
    function updatePageScale() {{
        const content = document.querySelector('.content');
        if (!content) return;
        const pageWidth = {page_width_px};
        const viewportWidth = window.innerWidth;
        if (viewportWidth <= 980) {{
            const scale = Math.min(1, viewportWidth / pageWidth);
            content.style.setProperty('--page-scale', scale.toFixed(3));
            const scaledWidth = pageWidth * scale;
            const leftOffset = (viewportWidth - scaledWidth) / 2;
            content.style.setProperty('--page-offset', leftOffset + 'px');
        }} else {{
            content.style.removeProperty('--page-scale');
            content.style.removeProperty('--page-offset');
        }}
    }}
    window.addEventListener('resize', updatePageScale);
    document.addEventListener('DOMContentLoaded', updatePageScale);
    </script>"""


def _css_vars(config: ZineConfig) -> str:
    """Generate CSS variable overrides from config."""
    page_width, page_height = config.page_dimensions
    lines = [
        f"        --page-width: {page_width};",
        f"        --page-height: {page_height};",
        f"        --font-heading: '{config.font_heading}', sans-serif;",
        f"        --font-body: '{config.font_body}', serif;",
        f"        --font-mono: '{config.font_mono}', monospace;",
        f"        --color-text: {config.color_text};",
        f"        --color-border: {config.color_border};",
        f"        --color-bg-muted: {config.color_bg_muted};",
        f"        --color-text-muted: {config.color_text_muted};",
        f"        --color-table-header-bg: {config.color_table_header_bg};",
        f"        --color-table-header-text: {config.color_table_header_text};",
        f"        --color-accent: {config.color_accent};",
        f"        --page-margin-vertical: {config.margin_vertical};",
        f"        --page-margin-horizontal: {config.margin_horizontal};",
        f"        --page-margin-spine: {config.margin_spine};",
    ]
    # Optional overrides (only emit when set)
    _optional = [
        ("font_size_body", "--font-size-body"),
        ("font_size_h1", "--font-size-h1"),
        ("font_size_h2", "--font-size-h2"),
        ("font_size_h3", "--font-size-h3"),
        ("font_size_h4", "--font-size-h4"),
        ("font_size_cover_h1", "--font-size-cover-h1"),
        ("font_size_cover_h2", "--font-size-cover-h2"),
        ("font_size_small", "--font-size-small"),
        ("font_size_tiny", "--font-size-tiny"),
        ("color_row_alt", "--color-row-alt"),
        ("color_row_border", "--color-row-border"),
        ("line_height", "--line-height"),
        ("paragraph_spacing", "--paragraph-spacing"),
        ("letter_spacing_h1", "--letter-spacing-h1"),
        ("letter_spacing_h2", "--letter-spacing-h2"),
        ("letter_spacing_h3", "--letter-spacing-h3"),
        ("letter_spacing_h4", "--letter-spacing-h4"),
        ("page_number_color", "--page-number-color"),
        ("page_number_size", "--page-number-size"),
        ("page_number_font", "--page-number-font"),
        ("page_number_position", "--page-number-bottom"),
        ("column_justify", "--column-justify"),
        ("column_gap", "--column-gap"),
        ("table_padding", "--table-cell-padding"),
    ]
    for attr, var in _optional:
        val = getattr(config, attr, "")
        if val:
            lines.append(f"        {var}: {val};")
    return "    :root {\n" + "\n".join(lines) + "\n    }"


def _page_size_rule(config: ZineConfig) -> str:
    """Generate @page rule with literal size values (CSS vars don't work in @page)."""
    page_width, page_height = config.page_dimensions
    return f"    @page {{ size: {page_width} {page_height}; margin: 0; }}"


def _page_fill_script() -> str:
    """JavaScript for dev-mode page fill detection badges.

    Iterates child elements to find actual content bottom, handles
    two-column layouts by tracking left/right column fill separately.
    """
    return """<script>
    function detectPageFill() {
        document.querySelectorAll('.page').forEach(function(page, idx) {
            if (page.classList.contains('cover-page')) return;

            var pNum = idx + 1;
            var r = page.getBoundingClientRect();
            var cs = getComputedStyle(page);
            var padTop = parseFloat(cs.paddingTop);
            var padBot = parseFloat(cs.paddingBottom);
            var pageNumReserve = padBot * 0.6;
            var contentTop = r.top + padTop;
            var pageBottom = r.bottom - padBot;
            var availH = pageBottom - contentTop;
            if (availH <= 0) return;

            var contentLeft = r.left + parseFloat(cs.paddingLeft);
            var contentRight = r.right - parseFloat(cs.paddingRight);
            var halfWidth = (contentRight - contentLeft) / 2;

            // Find the column container
            var colDiv = page.querySelector('.two-column, .three-column, .four-column, .five-column');
            var isTwoCol = colDiv && colDiv.classList.contains('two-column');

            var maxBot = contentTop;
            var lMax = contentTop, rMax = contentTop;
            var overflow = false, lOvf = false, rOvf = false;

            // Iterate all descendant elements to find lowest content
            var elems = page.querySelectorAll('*');
            for (var i = 0; i < elems.length; i++) {
                var el = elems[i];
                if (el.classList.contains('page-fill-badge') ||
                    el.classList.contains('file-indicator')) continue;
                var er = el.getBoundingClientRect();
                if (er.height === 0 || er.width === 0) continue;

                if (er.bottom > maxBot) maxBot = er.bottom;
                if (er.bottom > pageBottom + 1) overflow = true;

                if (isTwoCol) {
                    var cMid = (er.left + er.right) / 2;
                    var isCol = er.width < halfWidth * 0.95;
                    if (isCol) {
                        var midPage = (contentLeft + contentRight) / 2;
                        if (cMid < midPage) {
                            if (er.bottom > lMax) lMax = er.bottom;
                            if (er.bottom > pageBottom + 1) lOvf = true;
                        } else {
                            if (er.bottom > rMax) rMax = er.bottom;
                            if (er.bottom > pageBottom + 1) rOvf = true;
                        }
                    }
                }
            }

            var fillPct = Math.min(Math.round(((maxBot - contentTop) / availH) * 100), 100);
            var lPct = isTwoCol ? Math.min(Math.round(((lMax - contentTop) / availH) * 100), 100) : 0;
            var rPct = isTwoCol ? Math.min(Math.round(((rMax - contentTop) / availH) * 100), 100) : 0;

            // Build badge
            var badge = document.createElement('div');
            badge.className = 'page-fill-badge';
            badge.style.cssText = 'position:absolute;top:2px;left:2px;z-index:999;' +
                'font:700 9px/1 -apple-system,system-ui,sans-serif;padding:2px 5px;' +
                'border-radius:3px;pointer-events:none;';

            var label = 'p' + pNum + ': ';
            if (overflow) {
                badge.style.background = '#e74c3c'; badge.style.color = '#fff';
                if (isTwoCol) {
                    label += 'OVERFLOW [L:' + (lOvf ? 'OVF' : lPct + '%') +
                             ' R:' + (rOvf ? 'OVF' : rPct + '%') + ']';
                } else {
                    label += 'OVERFLOW';
                }
            } else if (fillPct >= 90) {
                badge.style.background = '#2a7d2a'; badge.style.color = '#fff';
                if (isTwoCol) {
                    label += fillPct + '% [L:' + lPct + '% R:' + rPct + '%]';
                } else {
                    label += fillPct + '%';
                }
            } else if (fillPct >= 70) {
                badge.style.background = '#b8860b'; badge.style.color = '#fff';
                if (isTwoCol) {
                    label += fillPct + '% [L:' + lPct + '% R:' + rPct + '%]';
                } else {
                    label += fillPct + '% (room)';
                }
            } else {
                badge.style.background = '#666'; badge.style.color = '#fff';
                if (isTwoCol) {
                    label += fillPct + '% [L:' + lPct + '% R:' + rPct + '%]';
                } else {
                    label += fillPct + '% (sparse)';
                }
            }
            badge.textContent = label;
            page.style.position = page.style.position || 'relative';
            page.appendChild(badge);
        });
    }
    document.addEventListener('DOMContentLoaded', function() {
        // Wait for fonts to load before measuring
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(detectPageFill);
        } else {
            detectPageFill();
        }
    });
    </script>"""


def render_print(
    body_html: str,
    config: ZineConfig,
    extra_css: str = "",
    extra_head: str = "",
) -> str:
    """Render a complete print-mode HTML document."""
    base_css = (THEMES_DIR / "base.css").read_text(encoding="utf-8")
    print_css = (THEMES_DIR / "print.css").read_text(encoding="utf-8")

    css_vars = _css_vars(config)
    page_rule = _page_size_rule(config)
    scaling_script = _page_scaling_script(config)

    page_count = body_html.count('<div class="page')
    page_warning = ""
    if page_count > 0 and page_count % 4 != 0:
        remainder = page_count % 4
        needed = 4 - remainder
        page_warning = f"<!-- Warning: {page_count} pages is not a multiple of 4. Add {needed} page(s) for saddle-stitch printing. -->"

    dev_script = _page_fill_script() if config.dev_mode else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={_font_url(config.font_heading)}:wght@600;700;800;900&family={_font_url(config.font_body)}:wght@400;700&family={_font_url(config.font_mono)}&display=swap" rel="stylesheet">
    <style>
{base_css}
{print_css}
{css_vars}
{page_rule}
{extra_css}
    </style>
    {extra_head}
</head>
<body>
    <div class="content">
{body_html}
    </div>
    {page_warning}
    {scaling_script}
    {dev_script}
</body>
</html>"""


def render_web(
    body_html: str,
    config: ZineConfig,
    extra_css: str = "",
    extra_head: str = "",
) -> str:
    """Render a web page HTML document."""
    base_css = (THEMES_DIR / "base.css").read_text(encoding="utf-8")
    web_css = (THEMES_DIR / "web.css").read_text(encoding="utf-8")

    css_vars = _css_vars(config)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={_font_url(config.font_heading)}:wght@600;700;800;900&family={_font_url(config.font_body)}:wght@400;700&family={_font_url(config.font_mono)}&display=swap" rel="stylesheet">
    <style>
{base_css}
{web_css}
{css_vars}
{extra_css}
    </style>
    {extra_head}
</head>
<body>
    <div class="web-content">
{body_html}
    </div>
</body>
</html>"""


def render_manual(
    body_html: str,
    config: ZineConfig,
    extra_css: str = "",
    extra_head: str = "",
) -> str:
    """Render a scrollable web manual with sidebar ToC.

    Sidebar ToC generated from h1/h2/h3 headers in body HTML.
    Includes scroll spy JS for active section highlighting.
    """
    base_css = (THEMES_DIR / "base.css").read_text(encoding="utf-8")
    manual_css = (THEMES_DIR / "manual.css").read_text(encoding="utf-8")

    css_vars = _css_vars(config)
    sidebar_html = generate_toc(body_html)
    spy_script = scrollspy_script()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={_font_url(config.font_heading)}:wght@600;700;800;900&family={_font_url(config.font_body)}:wght@400;700&family={_font_url(config.font_mono)}&display=swap" rel="stylesheet">
    <style>
{base_css}
{manual_css}
{css_vars}
{extra_css}
    </style>
    {extra_head}
</head>
<body>
    <div class="manual-layout">
    {sidebar_html}
    <div class="sidebar-overlay" onclick="toggleSidebar()"></div>
    <button class="mobile-toc-btn" onclick="toggleSidebar()" aria-label="Contents"></button>
    <div class="content">
{body_html}
    </div>
</div>
    {spy_script}
</body>
</html>"""


def render_mini_zine(
    body_html: str,
    config: ZineConfig,
    extra_css: str = "",
    extra_head: str = "",
) -> str:
    """Render a one-sheet fold-and-cut mini zine HTML document.

    Pages are arranged in an 8-panel grid by imposition.impose_mini_zine().
    The sheet is landscape-oriented with each panel at 1/4 width × 1/2 height.
    """
    base_css = (THEMES_DIR / "base.css").read_text(encoding="utf-8")
    print_css = (THEMES_DIR / "print.css").read_text(encoding="utf-8")
    minizine_css = (THEMES_DIR / "minizine.css").read_text(encoding="utf-8")

    css_vars = _css_vars(config)

    # page_size = the sheet you print on. Reading page = width/4 × height/2.
    sheet_width, sheet_height = config.page_dimensions
    reading_w, reading_h = config.reading_page_dimensions
    css_vars = css_vars.replace(
        f"--page-width: {sheet_width};",
        f"--page-width: {reading_w};",
    )
    css_vars = css_vars.replace(
        f"--page-height: {sheet_height};",
        f"--page-height: {reading_h};",
    )

    sheet_vars = f"""    :root {{
        --sheet-width: {sheet_width};
        --sheet-height: {sheet_height};
    }}"""

    page_rule = f"    @page {{ size: {sheet_width} {sheet_height}; margin: 0; }}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title} (Mini Zine)</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={_font_url(config.font_heading)}:wght@600;700;800;900&family={_font_url(config.font_body)}:wght@400;700&family={_font_url(config.font_mono)}&display=swap" rel="stylesheet">
    <style>
{base_css}
{print_css}
{minizine_css}
{css_vars}
{sheet_vars}
{page_rule}
{extra_css}
    </style>
    {extra_head}
</head>
<body>
    <div class="content">
{body_html}
    </div>
</body>
</html>"""


def render_trifold(
    body_html: str,
    config: ZineConfig,
    extra_css: str = "",
    extra_head: str = "",
) -> str:
    """Render a tri-fold (letter fold) HTML document."""
    base_css = (THEMES_DIR / "base.css").read_text(encoding="utf-8")
    print_css = (THEMES_DIR / "print.css").read_text(encoding="utf-8")
    trifold_css = (THEMES_DIR / "trifold.css").read_text(encoding="utf-8")

    css_vars = _css_vars(config)

    # page_size = the sheet you print on. Reading page = width/3 × height.
    sheet_width, sheet_height = config.page_dimensions
    reading_w, reading_h = config.reading_page_dimensions
    css_vars = css_vars.replace(
        f"--page-width: {sheet_width};",
        f"--page-width: {reading_w};",
    )

    sheet_vars = f"""    :root {{
        --sheet-width: {sheet_width};
        --sheet-height: {sheet_height};
    }}"""

    page_rule = f"    @page {{ size: {sheet_width} {sheet_height}; margin: 0; }}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title} (Tri-fold)</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={_font_url(config.font_heading)}:wght@600;700;800;900&family={_font_url(config.font_body)}:wght@400;700&family={_font_url(config.font_mono)}&display=swap" rel="stylesheet">
    <style>
{base_css}
{print_css}
{trifold_css}
{css_vars}
{sheet_vars}
{page_rule}
{extra_css}
    </style>
    {extra_head}
</head>
<body>
    <div class="content">
{body_html}
    </div>
</body>
</html>"""


def render_french_fold(
    body_html: str,
    config: ZineConfig,
    extra_css: str = "",
    extra_head: str = "",
) -> str:
    """Render a French fold (4pp on one sheet) HTML document."""
    base_css = (THEMES_DIR / "base.css").read_text(encoding="utf-8")
    print_css = (THEMES_DIR / "print.css").read_text(encoding="utf-8")
    frenchfold_css = (THEMES_DIR / "frenchfold.css").read_text(encoding="utf-8")

    css_vars = _css_vars(config)

    # page_size = the sheet you print on. Reading page = width/2 × height/2.
    sheet_width, sheet_height = config.page_dimensions
    reading_w, reading_h = config.reading_page_dimensions
    css_vars = css_vars.replace(
        f"--page-width: {sheet_width};",
        f"--page-width: {reading_w};",
    )
    css_vars = css_vars.replace(
        f"--page-height: {sheet_height};",
        f"--page-height: {reading_h};",
    )

    sheet_vars = f"""    :root {{
        --sheet-width: {sheet_width};
        --sheet-height: {sheet_height};
    }}"""

    page_rule = f"    @page {{ size: {sheet_width} {sheet_height}; margin: 0; }}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title} (French Fold)</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={_font_url(config.font_heading)}:wght@600;700;800;900&family={_font_url(config.font_body)}:wght@400;700&family={_font_url(config.font_mono)}&display=swap" rel="stylesheet">
    <style>
{base_css}
{print_css}
{frenchfold_css}
{css_vars}
{sheet_vars}
{page_rule}
{extra_css}
    </style>
    {extra_head}
</head>
<body>
    <div class="content">
{body_html}
    </div>
</body>
</html>"""


def render_micro_mini(
    body_html: str,
    config: ZineConfig,
    extra_css: str = "",
    extra_head: str = "",
) -> str:
    """Render a micro-mini zine (16pp on one double-sided sheet)."""
    base_css = (THEMES_DIR / "base.css").read_text(encoding="utf-8")
    print_css = (THEMES_DIR / "print.css").read_text(encoding="utf-8")
    micromini_css = (THEMES_DIR / "micromini.css").read_text(encoding="utf-8")

    css_vars = _css_vars(config)

    # page_size = the sheet you print on. Reading page = width/4 × height/2.
    sheet_width, sheet_height = config.page_dimensions
    reading_w, reading_h = config.reading_page_dimensions
    css_vars = css_vars.replace(
        f"--page-width: {sheet_width};",
        f"--page-width: {reading_w};",
    )
    css_vars = css_vars.replace(
        f"--page-height: {sheet_height};",
        f"--page-height: {reading_h};",
    )

    sheet_vars = f"""    :root {{
        --sheet-width: {sheet_width};
        --sheet-height: {sheet_height};
    }}"""

    page_rule = f"    @page {{ size: {sheet_width} {sheet_height}; margin: 0; }}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title} (Micro Mini)</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={_font_url(config.font_heading)}:wght@600;700;800;900&family={_font_url(config.font_body)}:wght@400;700&family={_font_url(config.font_mono)}&display=swap" rel="stylesheet">
    <style>
{base_css}
{print_css}
{micromini_css}
{css_vars}
{sheet_vars}
{page_rule}
{extra_css}
    </style>
    {extra_head}
</head>
<body>
    <div class="content">
{body_html}
    </div>
</body>
</html>"""


def render_booklet(
    body_html: str,
    config: ZineConfig,
    extra_css: str = "",
    extra_head: str = "",
) -> str:
    """Render an imposed booklet HTML document for saddle-stitch printing.

    Pages are already arranged in sheet pairs by imposition.impose().
    This wraps them in a full HTML document with landscape @page rule.
    """
    base_css = (THEMES_DIR / "base.css").read_text(encoding="utf-8")
    print_css = (THEMES_DIR / "print.css").read_text(encoding="utf-8")
    booklet_css = (THEMES_DIR / "booklet.css").read_text(encoding="utf-8")

    css_vars = _css_vars(config)

    # Booklet: page_size IS the sheet you print on.
    # Reading page = half the width (two pages side by side, fold vertical).
    # User controls fold direction via portrait/landscape orientation.
    sheet_width, sheet_height = config.page_dimensions
    sw_mm = float(sheet_width.replace("mm", ""))
    reading_w = f"{sw_mm / 2}mm"
    # Override --page-width inside :root block to reading page width
    css_vars = css_vars.replace(
        f"--page-width: {sheet_width};",
        f"--page-width: {reading_w};",
    )
    page_rule = f"    @page {{ size: {sheet_width} {sheet_height}; margin: 0; }}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title} (Booklet)</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={_font_url(config.font_heading)}:wght@600;700;800;900&family={_font_url(config.font_body)}:wght@400;700&family={_font_url(config.font_mono)}&display=swap" rel="stylesheet">
    <style>
{base_css}
{print_css}
{booklet_css}
{css_vars}
{page_rule}
{extra_css}
    </style>
    {extra_head}
</head>
<body>
    <div class="content">
{body_html}
    </div>
</body>
</html>"""
