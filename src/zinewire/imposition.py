"""Imposition layouts for zine printing.

Rearranges paginated HTML pages onto sheets in the correct order
for various folding and binding methods.
"""

import re
from html.parser import HTMLParser

from .config import ZineConfig


def compute_imposition_order(total_pages: int) -> tuple[list[tuple[int, int]], int]:
    """Compute saddle-stitch page pairing for N pages.

    Returns (sheets, padded_count) where sheets is a list of
    (left_idx, right_idx) tuples (0-indexed page indices).

    For 16 pages:
        Sheet 1 front: (15, 0)  -> page 16 | page 1
        Sheet 1 back:  (1, 14)  -> page 2  | page 15
        Sheet 2 front: (13, 2)  -> page 14 | page 3
        Sheet 2 back:  (3, 12)  -> page 4  | page 13
        ...
    """
    # Pad to multiple of 4
    padded = total_pages
    if padded % 4 != 0:
        padded += 4 - (padded % 4)

    sheets = []
    for i in range(padded // 4):
        front_left = padded - 1 - (2 * i)
        front_right = 2 * i
        back_left = 2 * i + 1
        back_right = padded - 2 - (2 * i)

        sheets.append((front_left, front_right))
        sheets.append((back_left, back_right))

    return sheets, padded


class _PageExtractor(HTMLParser):
    """Extract top-level <div class="page ..."> elements from HTML.

    Tracks div nesting depth to correctly capture pages that contain
    nested divs (column layouts, cover content, etc.).
    """

    def __init__(self):
        super().__init__()
        self.pages: list[str] = []
        self._in_page = False
        self._depth = 0
        self._current_page: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            if not self._in_page:
                attr_dict = dict(attrs)
                classes = attr_dict.get("class", "")
                if re.search(r'\bpage\b', classes):
                    self._in_page = True
                    self._depth = 1
                    self._current_page = [self.get_starttag_text()]
                    return
            else:
                self._depth += 1
        if self._in_page:
            self._current_page.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self._in_page:
            self._current_page.append(f"</{tag}>")
            if tag == "div":
                self._depth -= 1
                if self._depth == 0:
                    self.pages.append("".join(self._current_page))
                    self._in_page = False
                    self._current_page = []

    def handle_data(self, data):
        if self._in_page:
            self._current_page.append(data)

    def handle_comment(self, data):
        if self._in_page:
            self._current_page.append(f"<!--{data}-->")

    def handle_entityref(self, name):
        if self._in_page:
            self._current_page.append(f"&{name};")

    def handle_charref(self, name):
        if self._in_page:
            self._current_page.append(f"&#{name};")


def extract_pages(html_body: str) -> list[str]:
    """Extract page div HTML strings from paginated body HTML.

    Each returned string is a complete <div class="page ...">...</div>.
    Adds data-page-number attribute and page-odd/page-even class.
    """
    parser = _PageExtractor()
    parser.feed(html_body)

    result = []
    for i, page_html in enumerate(parser.pages):
        page_num = i + 1
        parity = "page-odd" if page_num % 2 == 1 else "page-even"

        # Add data-page-number and parity class to the opening tag
        def _add_attrs(match):
            classes = match.group(1)
            # Add parity class
            new_classes = f"{classes} {parity}"
            return f'<div class="{new_classes}" data-page-number="{page_num}"'

        page_html = re.sub(
            r'<div class="([^"]*)"',
            _add_attrs,
            page_html,
            count=1,
        )
        result.append(page_html)

    return result


def _get_page_html(pages: list[str], index: int) -> str:
    """Get page HTML by index, or a blank placeholder if beyond actual pages."""
    if index < len(pages):
        return pages[index]
    return '<div class="blank-page"></div>'


def _build_sheets(pages: list[str], order: list[tuple[int, int]]) -> str:
    """Build sheet HTML from pages and imposition order."""
    total_physical = len(order) // 2
    sheets = []

    # Print instructions (hidden in print, shown on screen)
    s = "s" if total_physical != 1 else ""
    instructions = (
        '<div class="booklet-instructions">'
        f'<strong>Saddle-stitch booklet &mdash; {total_physical} physical sheet{s}, '
        f'printed double-sided</strong>'
        '<ol>'
        '<li>Print with <strong>landscape</strong> orientation</li>'
        '<li>Enable <strong>double-sided / duplex</strong> printing</li>'
        '<li>Select <strong>&ldquo;Flip on short edge&rdquo;</strong></li>'
        '<li>Stack all sheets, fold in half, staple at spine</li>'
        '</ol></div>'
    )
    sheets.append(instructions)

    for i, (left_idx, right_idx) in enumerate(order):
        left_page = _get_page_html(pages, left_idx)
        right_page = _get_page_html(pages, right_idx)
        sheet_num = i // 2 + 1
        side = "front" if i % 2 == 0 else "back"

        label = f'<div class="sheet-label">Sheet {sheet_num} &mdash; {side}</div>'

        sheet = (
            f'<div class="sheet" data-sheet="{sheet_num}" data-side="{side}">\n'
            f'    {label}\n'
            f'    <div class="imposed-left">{left_page}</div>\n'
            f'    <div class="imposed-right">{right_page}</div>\n'
            f'</div>'
        )
        sheets.append(sheet)

    return "\n\n".join(sheets)


def impose(html_body: str, config: ZineConfig | None = None) -> str:
    """Impose paginated HTML for saddle-stitch booklet printing.

    Takes paginated HTML body (containing <div class="page"> elements)
    and returns HTML body with <div class="sheet"> elements containing
    page pairs in saddle-stitch order.
    """
    pages = extract_pages(html_body)
    if not pages:
        return html_body

    order, padded = compute_imposition_order(len(pages))
    return _build_sheets(pages, order)


# ---------------------------------------------------------------------------
# Mini Zine Imposition (8-page fold-and-cut on one sheet)
# ---------------------------------------------------------------------------

# The classic one-sheet zine layout on a landscape sheet:
#
#   +--------+--------+--------+--------+
#   | (8) ↕  |  (1)   |  (2)   | (7) ↕  |
#   +--------+--------+--------+--------+
#   |  (5)   | (4) ↕  | (3) ↕  |  (6)   |
#   +--------+--------+--------+--------+
#
# ↕ = rotated 180°. Each cell is 1/4 sheet width × 1/2 sheet height.
# After printing: fold, cut center slit, fold into 8-page booklet.

# (row, col) → (page_number_1indexed, rotated_180)
_MINI_ZINE_LAYOUT = [
    # Top row: left to right
    [(8, True), (1, False), (2, False), (7, True)],
    # Bottom row: left to right
    [(5, False), (4, True), (3, True), (6, False)],
]


def impose_mini_zine(html_body: str, config: ZineConfig | None = None) -> str:
    """Impose paginated HTML as a one-sheet fold-and-cut mini zine.

    Takes up to 8 pages and arranges them in the classic mini zine layout
    on a single landscape sheet. Pages 1 and 8 are front/back covers.

    If fewer than 8 pages, blank pages fill remaining slots.
    If more than 8 pages, only the first 8 are used.
    """
    pages = extract_pages(html_body)
    if not pages:
        return html_body

    # Limit to 8 pages
    pages = pages[:8]

    cells = []
    for row_idx, row in enumerate(_MINI_ZINE_LAYOUT):
        for col_idx, (page_num, rotated) in enumerate(row):
            page_idx = page_num - 1  # 0-indexed
            page_html = _get_page_html(pages, page_idx)

            rotate_class = " mini-rotated" if rotated else ""
            cells.append(
                f'<div class="mini-cell mini-r{row_idx} mini-c{col_idx}{rotate_class}">'
                f'{page_html}'
                f'</div>'
            )

    sheet_html = (
        '<div class="mini-sheet">\n'
        + "\n".join(cells)
        + "\n</div>"
    )

    return sheet_html


# ---------------------------------------------------------------------------
# Tri-fold (letter fold, 6 panels on 2 sides)
# ---------------------------------------------------------------------------

# Classic tri-fold / letter fold layout:
#
#   Front (printed side up):
#   +----------+-----------+----------+
#   |  (6)     |   (1)     |  (2)     |
#   | back flap| front     | back     |
#   +----------+-----------+----------+
#
#   Back (flip on long edge):
#   +----------+-----------+----------+
#   |  (3)     |   (4)     |  (5)     |
#   | inside-L | inside-C  | inside-R |
#   +----------+-----------+----------+
#
# The left panel on front (page 6) tucks inside, so it's slightly narrower.

_TRIFOLD_LAYOUT = [
    # Front: left, center, right
    [(6, False), (1, False), (2, False)],
    # Back: left, center, right
    [(3, False), (4, False), (5, False)],
]


def impose_trifold(html_body: str, config: ZineConfig | None = None) -> str:
    """Impose paginated HTML as a tri-fold (letter fold) layout.

    Arranges 6 pages across 2 sides of one sheet (3 panels per side).
    Front: back-flap | front-cover | back-cover
    Back:  inside-left | inside-center | inside-right
    """
    pages = extract_pages(html_body)
    if not pages:
        return html_body

    pages = pages[:6]

    sides = []
    for side_idx, (row, side_name) in enumerate(
        zip(_TRIFOLD_LAYOUT, ["front", "back"])
    ):
        cells = []
        for col_idx, (page_num, _rotated) in enumerate(row):
            page_idx = page_num - 1
            page_html = _get_page_html(pages, page_idx)
            tuck = " trifold-tuck" if side_name == "front" and col_idx == 0 else ""
            cells.append(
                f'<div class="trifold-panel trifold-c{col_idx}{tuck}">'
                f'{page_html}'
                f'</div>'
            )
        label = f'<div class="trifold-label">{side_name.title()} side</div>'
        sides.append(
            f'<div class="trifold-sheet" data-side="{side_name}">\n'
            f'    {label}\n'
            + "\n".join(f"    {c}" for c in cells)
            + "\n</div>"
        )

    return "\n\n".join(sides)


# ---------------------------------------------------------------------------
# French Fold (4 pages, fold in half then perpendicular)
# ---------------------------------------------------------------------------

# French fold layout on a single sheet:
#
#   Printed side (face up):
#   +----------+----------+
#   |  (4) ↕   |  (1)     |   ← fold horizontally first
#   +----------+----------+
#   |  (2)     |  (3) ↕   |   ← then fold vertically
#   +----------+----------+
#
# ↕ = rotated 180°. After folding: page 1 is front, 2-3 inside, 4 back.

_FRENCH_FOLD_LAYOUT = [
    # Top row: left, right
    [(4, True), (1, False)],
    # Bottom row: left, right
    [(2, False), (3, True)],
]


def impose_french_fold(html_body: str, config: ZineConfig | None = None) -> str:
    """Impose paginated HTML as a French fold (4 pages on one sheet).

    Arranges 4 pages in a 2×2 grid. Pages 4 and 3 are rotated 180°.
    After printing: fold in half horizontally, then vertically.
    """
    pages = extract_pages(html_body)
    if not pages:
        return html_body

    pages = pages[:4]

    cells = []
    for row_idx, row in enumerate(_FRENCH_FOLD_LAYOUT):
        for col_idx, (page_num, rotated) in enumerate(row):
            page_idx = page_num - 1
            page_html = _get_page_html(pages, page_idx)
            rotate_class = " frenchfold-rotated" if rotated else ""
            cells.append(
                f'<div class="frenchfold-cell frenchfold-r{row_idx} '
                f'frenchfold-c{col_idx}{rotate_class}">'
                f'{page_html}'
                f'</div>'
            )

    sheet_html = (
        '<div class="frenchfold-sheet">\n'
        + "\n".join(cells)
        + "\n</div>"
    )

    return sheet_html


# ---------------------------------------------------------------------------
# Micro-mini (16 pages on one double-sided sheet)
# ---------------------------------------------------------------------------

# Extends the mini-zine concept to 16 pages. Printed double-sided.
#
# Front:
#   +------+------+------+------+
#   |16 ↕  |  1   |  2   |15 ↕  |
#   +------+------+------+------+
#   | 13   |  4 ↕ |  3 ↕ | 14   |
#   +------+------+------+------+
#
# Back:
#   +------+------+------+------+
#   |10 ↕  |  7   |  8   | 9 ↕  |
#   +------+------+------+------+
#   | 11   | 12 ↕ |11 ↕  | 10   |    (pages 10,11 appear twice — correction below)
#   +------+------+------+------+
#
# Actually for 16pp, the back side mirrors the front with pages 5-12:

_MICRO_MINI_FRONT = [
    [(16, True), (1, False), (2, False), (15, True)],
    [(13, False), (4, True), (3, True), (14, False)],
]

_MICRO_MINI_BACK = [
    [(10, True), (7, False), (8, False), (9, True)],
    [(5, False), (12, True), (11, True), (6, False)],
]


def impose_micro_mini(html_body: str, config: ZineConfig | None = None) -> str:
    """Impose paginated HTML as a micro-mini zine (16pp on one sheet).

    Arranges 16 pages in a 4×2 grid on each side of a double-sided sheet.
    Extension of the mini-zine concept with two 8-panel grids.
    """
    pages = extract_pages(html_body)
    if not pages:
        return html_body

    pages = pages[:16]

    sheets = []
    for layout, side_name in [
        (_MICRO_MINI_FRONT, "front"),
        (_MICRO_MINI_BACK, "back"),
    ]:
        cells = []
        for row_idx, row in enumerate(layout):
            for col_idx, (page_num, rotated) in enumerate(row):
                page_idx = page_num - 1
                page_html = _get_page_html(pages, page_idx)
                rotate_class = " micro-rotated" if rotated else ""
                cells.append(
                    f'<div class="micro-cell micro-r{row_idx} '
                    f'micro-c{col_idx}{rotate_class}">'
                    f'{page_html}'
                    f'</div>'
                )

        label = f'<div class="micro-label">{side_name.title()} side</div>'
        sheets.append(
            f'<div class="micro-sheet" data-side="{side_name}">\n'
            f'    {label}\n'
            + "\n".join(cells)
            + "\n</div>"
        )

    return "\n\n".join(sheets)
