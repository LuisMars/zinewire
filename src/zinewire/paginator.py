"""Page-wrapping state machine for zinewire.

The paginator takes HTML with marker comments (produced by directive
preprocessing + markdown conversion) and wraps content in page divs
with column layout containers.

Unified approach for 1-5 columns:
- 1-2 columns: CSS column-count with column-break divs (content flows naturally)
- 3-5 columns: flexbox with explicit <div class="column"> elements
"""

import re

from .config import ZineConfig


# CSS class names for column layouts
COLUMN_CLASSES = {
    1: "single-column",
    2: "two-column",
    3: "three-column",
    4: "four-column",
    5: "five-column",
}

# Column counts that use flexbox (explicit column divs) vs CSS columns
FLEXBOX_THRESHOLD = 3


def _column_class(count: int) -> str:
    """Get CSS class for a column count."""
    return COLUMN_CLASSES.get(count, f"{count}-column")


def _open_page(
    result: list,
    col_count: int,
    compact: bool = False,
    page_classes: str = "page",
) -> None:
    """Append the opening tags for a new page + column container."""
    classes = page_classes
    if compact:
        classes += " compact"
    result.append(f'<div class="{classes}">\n<div class="{_column_class(col_count)}">\n')


def _close_page(result: list) -> None:
    """Append the closing tags for a page (column div + page div)."""
    result.append("</div>\n</div>\n\n")


def _flush_flexbox_columns(result: list, column_buffers: list[list[str]], expected_count: int = 0) -> None:
    """Flush accumulated column buffers as flexbox <div class="column"> elements.

    Pads with empty columns if fewer buffers exist than expected_count,
    so flexbox layouts always get the right number of children.
    """
    # Pad to expected column count
    while expected_count and len(column_buffers) < expected_count:
        column_buffers.append([])

    for buf in column_buffers:
        content = "".join(buf)
        if content.strip():
            result.append(f'<div class="column">\n{content}\n</div>\n')
        else:
            result.append('<div class="column"></div>\n')


def paginate(html_body: str, config: ZineConfig | None = None) -> str:
    """Wrap HTML content in page divs based on marker comments.

    State machine ported from html_builder.py:500-619,
    unified with QR column logic from html_builder.py:1053-1138.

    Markers consumed (structural):
    - <!--COVERPAGE:image|size-->
    - <!--PAGEBREAK-->
    - <!--ONECOLUMN--> through <!--FIVECOLUMNS-->
    - <!--COMPACT-->

    Markers transformed (post-processing):
    - <!--LARGETEXT-->     -> <div class="large-text">
    - <!--NORMALTEXT-->    -> </div>
    - <!--SPACE-->         -> <div class="spacer"></div>
    - <!--SECTIONBREAK-->  -> <div class="page-break-marker"></div>
    - <!--COLUMNBREAK-->   -> <div class="column-break"> (1-2 col) or column div flush (3-5 col)
    - <!--COLUMNBREAKVISIBLE--> -> <div class="column-break-visible"></div>
    """
    if config is None:
        config = ZineConfig()

    default_col = config.default_columns

    # Pre-paginator text wrapper transforms (apply to both modes)
    html_body = html_body.replace("<!--LARGETEXT-->", '<div class="large-text">')
    html_body = html_body.replace("<!--NORMALTEXT-->", "</div>")
    html_body = html_body.replace("<!--SPACE-->", '<div class="spacer"></div>')

    # Split HTML by structural markers while keeping them
    parts = re.split(
        r"(<!--(?:COVERPAGE:[^>]*|PAGEBREAK|ONECOLUMN|TWOCOLUMNS|THREECOLUMNS|FOURCOLUMNS|FIVECOLUMNS|COMPACT|COLUMNBREAK|COLUMNBREAKVISIBLE)-->)",
        html_body,
    )

    # State machine
    result: list[str] = []
    current_col_count = default_col
    page_opened = False
    current_is_cover = False
    pending_content: list[str] = []
    page_count = 0
    compact_mode = config.compact

    # For 3+ column flexbox mode: buffer content per column
    column_buffers: list[list[str]] = [[]]
    in_flexbox_mode = default_col >= FLEXBOX_THRESHOLD

    def _ensure_page_open():
        """Open a page if not already open, flushing pending content."""
        nonlocal page_opened, in_flexbox_mode, column_buffers
        if not page_opened:
            _open_page(result, current_col_count, compact=compact_mode)
            result.extend(pending_content)
            pending_content.clear()
            page_opened = True
            in_flexbox_mode = current_col_count >= FLEXBOX_THRESHOLD
            if in_flexbox_mode:
                column_buffers = [[]]

    def _close_current_page():
        """Close the current page, flushing flexbox columns if needed."""
        nonlocal page_opened, current_is_cover, page_count, compact_mode
        if page_opened:
            if in_flexbox_mode and column_buffers:
                _flush_flexbox_columns(result, column_buffers, current_col_count)
                column_buffers.clear()
            _close_page(result)
            page_count += 1
        page_opened = False
        current_is_cover = False
        compact_mode = config.compact  # reset to config default

    for part in parts:
        # --- Cover page ---
        cover_match = re.match(r"<!--COVERPAGE:([^|]*)\|?(.*)-->", part)
        if cover_match:
            cover_image = cover_match.group(1)
            cover_size = cover_match.group(2)

            _close_current_page()

            classes = "page cover-page"
            if page_count > 0:
                classes += " secondary-cover"
            if compact_mode:
                classes += " compact"

            if cover_image:
                style_parts = [f"background-image: url({cover_image});"]
                if cover_size:
                    style_parts.append(f"background-size: {cover_size};")
                style = f' style="{" ".join(style_parts)}"'
            else:
                style = ""

            result.append(
                f'<div class="{classes}"{style}>\n<div class="cover-content">\n'
            )
            result.extend(pending_content)
            pending_content.clear()
            page_opened = True
            current_is_cover = True
            in_flexbox_mode = False
            column_buffers = [[]]
            continue

        # --- Page break ---
        if part == "<!--PAGEBREAK-->":
            _close_current_page()
            current_col_count = default_col
            in_flexbox_mode = default_col >= FLEXBOX_THRESHOLD
            column_buffers = [[]]
            continue

        # --- Column count switches ---
        col_switch = {
            "<!--ONECOLUMN-->": 1,
            "<!--TWOCOLUMNS-->": 2,
            "<!--THREECOLUMNS-->": 3,
            "<!--FOURCOLUMNS-->": 4,
            "<!--FIVECOLUMNS-->": 5,
        }.get(part)

        if col_switch is not None:
            _ensure_page_open()

            if current_col_count != col_switch:
                # Flush flexbox columns if leaving 3+ mode
                if in_flexbox_mode and column_buffers:
                    _flush_flexbox_columns(result, column_buffers, current_col_count)

                # Close old column div, open new
                result.append(
                    f'</div>\n<div class="{_column_class(col_switch)}">\n'
                )

                current_col_count = col_switch
                in_flexbox_mode = col_switch >= FLEXBOX_THRESHOLD
                column_buffers = [[]]
            continue

        # --- Compact mode ---
        if part == "<!--COMPACT-->":
            compact_mode = True
            continue

        # --- Column break ---
        if part == "<!--COLUMNBREAK-->":
            if page_opened:
                if in_flexbox_mode:
                    # 3+ columns: start a new column buffer
                    column_buffers.append([])
                else:
                    # 1-2 columns: emit CSS column break
                    result.append('<div class="column-break"></div>\n')
            continue

        # --- Visible column break ---
        if part == "<!--COLUMNBREAKVISIBLE-->":
            if page_opened:
                if in_flexbox_mode:
                    column_buffers.append([])
                else:
                    result.append('<div class="column-break-visible"></div>\n')
            continue

        # --- Regular content ---
        content_stripped = re.sub(r"<!--FILE:[^>]+-->", "", part)
        if not page_opened:
            if content_stripped.strip():
                _open_page(result, current_col_count, compact=compact_mode)
                result.extend(pending_content)
                pending_content.clear()
                page_opened = True
                in_flexbox_mode = current_col_count >= FLEXBOX_THRESHOLD
                if in_flexbox_mode:
                    column_buffers = [[]]
                    column_buffers[0].append(part)
                else:
                    result.append(part)
            else:
                pending_content.append(part)
        else:
            if in_flexbox_mode:
                column_buffers[-1].append(part)
            else:
                result.append(part)

    # Close final page
    if page_opened:
        if in_flexbox_mode and column_buffers:
            _flush_flexbox_columns(result, column_buffers, current_col_count)
        result.append("\n</div>\n</div>")

    html_body = "".join(result)

    # Post-processing: clean empty column/cover divs
    html_body = re.sub(
        r'<div class="(?:(?:single|two|three|four|five)-column|cover-content)">\s*</div>\s*',
        "",
        html_body,
    )

    # Transform remaining markers
    html_body = html_body.replace(
        "<!--SECTIONBREAK-->", '<div class="page-break-marker"></div>'
    )

    # File indicators
    if config.dev_mode:
        html_body = re.sub(
            r"<!--FILE:([^>]+)-->",
            r'<div class="file-indicator">\1</div>',
            html_body,
        )
    else:
        html_body = re.sub(r"<!--FILE:[^>]+-->", "", html_body)

    return html_body


def strip_markers(html_body: str) -> str:
    """Remove all page/column markers for non-paginated modes (landing, manual).

    Keeps text wrappers (large/normal/space) since those are content-level.
    Port from html_builder.py:494-499.
    """
    # Apply text wrappers (same as paginate)
    html_body = html_body.replace("<!--LARGETEXT-->", '<div class="large-text">')
    html_body = html_body.replace("<!--NORMALTEXT-->", "</div>")
    html_body = html_body.replace("<!--SPACE-->", '<div class="spacer"></div>')

    # Remove all structural markers
    html_body = re.sub(
        r"<!--(?:COVERPAGE:[^>]*|PAGEBREAK|SECTIONBREAK|COLUMNBREAK|COLUMNBREAKVISIBLE|ONECOLUMN|TWOCOLUMNS|THREECOLUMNS|FOURCOLUMNS|FIVECOLUMNS|COMPACT)-->",
        "",
        html_body,
    )
    html_body = re.sub(r"<!--FILE:[^>]+-->", "", html_body)

    return html_body
