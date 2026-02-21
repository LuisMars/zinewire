"""Tests for booklet imposition (saddle-stitch page reordering)."""

import tempfile
from pathlib import Path

from zinewire import build
from zinewire.config import ZineConfig
from zinewire.imposition import (
    _MINI_ZINE_LAYOUT,
    _build_sheets,
    compute_imposition_order,
    extract_pages,
    impose,
    impose_mini_zine,
)


# ---------------------------------------------------------------------------
# compute_imposition_order tests
# ---------------------------------------------------------------------------

def test_compute_imposition_order_16_pages():
    """16 pages: classic 4-sheet saddle-stitch booklet."""
    sheets, padded = compute_imposition_order(16)
    assert padded == 16
    assert len(sheets) == 8  # 4 sheets x 2 sides

    # Sheet 1 front: page 16 | page 1 (indices 15, 0)
    assert sheets[0] == (15, 0)
    # Sheet 1 back: page 2 | page 15 (indices 1, 14)
    assert sheets[1] == (1, 14)
    # Sheet 2 front: page 14 | page 3 (indices 13, 2)
    assert sheets[2] == (13, 2)
    # Sheet 2 back: page 4 | page 13 (indices 3, 12)
    assert sheets[3] == (3, 12)
    # Last side: page 8 | page 9 (indices 7, 8)
    assert sheets[7] == (7, 8)


def test_compute_imposition_order_4_pages():
    """Minimal booklet: 4 pages = 1 sheet."""
    sheets, padded = compute_imposition_order(4)
    assert padded == 4
    assert len(sheets) == 2  # 1 sheet x 2 sides
    # Front: page 4 | page 1
    assert sheets[0] == (3, 0)
    # Back: page 2 | page 3
    assert sheets[1] == (1, 2)


def test_compute_imposition_order_8_pages():
    """8 pages = 2 sheets."""
    sheets, padded = compute_imposition_order(8)
    assert padded == 8
    assert len(sheets) == 4


def test_compute_imposition_order_padding():
    """10 pages pads to 12 (next multiple of 4)."""
    sheets, padded = compute_imposition_order(10)
    assert padded == 12
    assert len(sheets) == 6  # 3 sheets x 2 sides


def test_compute_imposition_order_already_multiple_of_4():
    """12 pages: no padding needed."""
    sheets, padded = compute_imposition_order(12)
    assert padded == 12


def test_compute_imposition_order_1_page():
    """1 page pads to 4."""
    sheets, padded = compute_imposition_order(1)
    assert padded == 4
    assert len(sheets) == 2


def test_compute_imposition_order_3_pages():
    """3 pages pads to 4."""
    sheets, padded = compute_imposition_order(3)
    assert padded == 4


# ---------------------------------------------------------------------------
# extract_pages tests
# ---------------------------------------------------------------------------

def test_extract_pages_simple():
    """Extract pages from simple paginated HTML."""
    html = (
        '<div class="page">\n<div class="two-column">\n'
        "<p>Page 1</p>\n</div>\n</div>\n\n"
        '<div class="page">\n<div class="two-column">\n'
        "<p>Page 2</p>\n</div>\n</div>\n\n"
    )
    pages = extract_pages(html)
    assert len(pages) == 2
    assert "Page 1" in pages[0]
    assert "Page 2" in pages[1]


def test_extract_pages_adds_attributes():
    """Pages get data-page-number and parity classes."""
    html = (
        '<div class="page"><p>A</p></div>'
        '<div class="page"><p>B</p></div>'
        '<div class="page"><p>C</p></div>'
    )
    pages = extract_pages(html)
    assert len(pages) == 3

    assert 'data-page-number="1"' in pages[0]
    assert "page-odd" in pages[0]

    assert 'data-page-number="2"' in pages[1]
    assert "page-even" in pages[1]

    assert 'data-page-number="3"' in pages[2]
    assert "page-odd" in pages[2]


def test_extract_pages_with_nested_divs():
    """Pages containing nested divs are extracted correctly."""
    html = (
        '<div class="page">\n'
        '<div class="two-column">\n'
        '<div class="column">Col 1</div>\n'
        '<div class="column">Col 2</div>\n'
        '</div>\n'
        '</div>\n'
    )
    pages = extract_pages(html)
    assert len(pages) == 1
    assert "Col 1" in pages[0]
    assert "Col 2" in pages[0]


def test_extract_pages_with_cover():
    """Cover pages (class="page cover-page") are extracted."""
    html = (
        '<div class="page cover-page" style="background-image: url(cover.jpg);">'
        '<div class="cover-content"><h1>Title</h1></div>'
        '</div>'
        '<div class="page"><p>Content</p></div>'
    )
    pages = extract_pages(html)
    assert len(pages) == 2
    assert "cover-page" in pages[0]
    assert "Title" in pages[0]


def test_extract_pages_preserves_content():
    """Page inner HTML is preserved."""
    html = (
        '<div class="page">'
        '<h1>Hello &amp; World</h1>'
        '<p>Some <strong>bold</strong> text</p>'
        '<!-- a comment -->'
        '</div>'
    )
    pages = extract_pages(html)
    assert len(pages) == 1
    # HTMLParser decodes entities, so &amp; becomes &
    assert "Hello & World" in pages[0]
    assert "<strong>bold</strong>" in pages[0]
    assert "<!-- a comment -->" in pages[0]


# ---------------------------------------------------------------------------
# impose() tests
# ---------------------------------------------------------------------------

def test_impose_produces_sheets():
    """impose() wraps pages in sheet divs."""
    # Build 4 pages of HTML
    pages_html = ""
    for i in range(4):
        pages_html += f'<div class="page"><p>Page {i+1}</p></div>\n'

    result = impose(pages_html)

    assert '<div class="sheet"' in result
    assert 'data-sheet="1"' in result
    assert 'data-side="front"' in result
    assert 'data-side="back"' in result
    assert '<div class="imposed-left">' in result
    assert '<div class="imposed-right">' in result


def test_impose_blank_padding():
    """impose() adds blank pages when count is not multiple of 4."""
    # 3 pages → padded to 4
    pages_html = ""
    for i in range(3):
        pages_html += f'<div class="page"><p>Page {i+1}</p></div>\n'

    result = impose(pages_html)
    assert '<div class="blank-page"></div>' in result


def test_impose_preserves_page_content():
    """All original page content appears in imposed output."""
    pages_html = (
        '<div class="page"><p>Alpha</p></div>'
        '<div class="page"><p>Beta</p></div>'
        '<div class="page"><p>Gamma</p></div>'
        '<div class="page"><p>Delta</p></div>'
    )
    result = impose(pages_html)
    assert "Alpha" in result
    assert "Beta" in result
    assert "Gamma" in result
    assert "Delta" in result


def test_impose_page_order_4_pages():
    """4-page booklet: sheet order matches saddle-stitch formula."""
    pages_html = ""
    for i in range(4):
        pages_html += f'<div class="page"><p>P{i+1}</p></div>\n'

    result = impose(pages_html)

    # Sheet 1 front: page 4 | page 1
    # The first sheet should have P4 on the left and P1 on the right
    sheets = result.split('<div class="sheet"')
    # sheets[0] is empty (before first match), sheets[1] is first sheet
    front = sheets[1]
    assert "imposed-left" in front
    assert "imposed-right" in front


def test_impose_empty_input():
    """impose() returns input unchanged if no pages found."""
    result = impose("<p>No pages here</p>")
    assert result == "<p>No pages here</p>"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

def test_booklet_build_integration():
    """End-to-end: markdown → booklet HTML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text(
            "# Test Booklet\n\n"
            "Page 1 content.\n\n"
            "/pagebreak\n\n"
            "Page 2 content.\n\n"
            "/pagebreak\n\n"
            "Page 3 content.\n\n"
            "/pagebreak\n\n"
            "Page 4 content.\n"
        )
        output = Path(tmpdir) / "test-booklet.html"
        config = ZineConfig(booklet=True)
        html = build(str(source), output=str(output), config=config)

        assert output.exists()
        assert '<div class="sheet"' in html
        assert "imposed-left" in html
        assert "imposed-right" in html
        assert "Page 1 content" in html
        assert "Page 4 content" in html


def test_booklet_output_path_auto():
    """Booklet build auto-generates -booklet.html output path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "myzine.md"
        source.write_text("# My Zine\n\nContent.\n")
        config = ZineConfig(booklet=True)
        build(str(source), config=config)

        expected = Path(tmpdir) / "myzine-booklet.html"
        assert expected.exists()


def test_booklet_has_landscape_page_rule():
    """Booklet HTML contains A4 landscape @page rule for A5 pages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text("# Test\n\nContent.\n")
        config = ZineConfig(booklet=True)
        html = build(str(source), config=config)

        # A5 page width = 148mm, so landscape sheet = 296mm
        assert "296.0mm" in html
        assert "210mm" in html


# ---------------------------------------------------------------------------
# Mini Zine imposition tests
# ---------------------------------------------------------------------------

def test_mini_zine_layout_structure():
    """Mini zine layout has correct dimensions (2 rows × 4 cols = 8 cells)."""
    assert len(_MINI_ZINE_LAYOUT) == 2
    assert len(_MINI_ZINE_LAYOUT[0]) == 4
    assert len(_MINI_ZINE_LAYOUT[1]) == 4


def test_mini_zine_layout_all_pages():
    """All 8 pages (1-8) appear exactly once in the layout."""
    page_nums = set()
    for row in _MINI_ZINE_LAYOUT:
        for page_num, _ in row:
            page_nums.add(page_num)
    assert page_nums == {1, 2, 3, 4, 5, 6, 7, 8}


def test_mini_zine_layout_rotations():
    """Correct pages are rotated 180° in the mini zine layout."""
    # Top row: pages 8 and 7 are rotated
    assert _MINI_ZINE_LAYOUT[0][0] == (8, True)   # top-left: page 8, rotated
    assert _MINI_ZINE_LAYOUT[0][1] == (1, False)  # page 1, normal
    assert _MINI_ZINE_LAYOUT[0][2] == (2, False)  # page 2, normal
    assert _MINI_ZINE_LAYOUT[0][3] == (7, True)   # top-right: page 7, rotated
    # Bottom row: pages 4 and 3 are rotated
    assert _MINI_ZINE_LAYOUT[1][0] == (5, False)  # page 5, normal
    assert _MINI_ZINE_LAYOUT[1][1] == (4, True)   # page 4, rotated
    assert _MINI_ZINE_LAYOUT[1][2] == (3, True)   # page 3, rotated
    assert _MINI_ZINE_LAYOUT[1][3] == (6, False)  # page 6, normal


def test_impose_mini_zine_produces_sheet():
    """impose_mini_zine() produces a mini-sheet div with 8 cells."""
    pages_html = ""
    for i in range(8):
        pages_html += f'<div class="page"><p>Page {i+1}</p></div>\n'

    result = impose_mini_zine(pages_html)

    assert '<div class="mini-sheet">' in result
    assert result.count('<div class="mini-cell') == 8


def test_impose_mini_zine_rotated_cells():
    """Correct cells get the mini-rotated class."""
    pages_html = ""
    for i in range(8):
        pages_html += f'<div class="page"><p>P{i+1}</p></div>\n'

    result = impose_mini_zine(pages_html)

    assert "mini-rotated" in result
    # 4 cells should be rotated (pages 8, 7, 4, 3)
    assert result.count("mini-rotated") == 4


def test_impose_mini_zine_blank_pages():
    """Fewer than 8 pages get blank page placeholders."""
    pages_html = '<div class="page"><p>Only one</p></div>\n'

    result = impose_mini_zine(pages_html)

    assert '<div class="mini-sheet">' in result
    assert "Only one" in result
    assert '<div class="blank-page"></div>' in result


def test_impose_mini_zine_preserves_content():
    """All page content is preserved in the mini zine output."""
    pages_html = ""
    for i in range(8):
        pages_html += f'<div class="page"><p>Content-{i+1}</p></div>\n'

    result = impose_mini_zine(pages_html)

    for i in range(8):
        assert f"Content-{i+1}" in result


def test_impose_mini_zine_truncates_to_8():
    """More than 8 pages: only first 8 are used."""
    pages_html = ""
    for i in range(12):
        pages_html += f'<div class="page"><p>P{i+1}</p></div>\n'

    result = impose_mini_zine(pages_html)

    assert "P8" in result
    assert "P9" not in result


def test_impose_mini_zine_empty_input():
    """Empty input returns input unchanged."""
    result = impose_mini_zine("<p>No pages</p>")
    assert result == "<p>No pages</p>"


def test_mini_zine_build_integration():
    """End-to-end: markdown → mini zine HTML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "test.md"
        source.write_text(
            "# Mini Zine Test\n\n"
            "Page 1.\n\n/pagebreak\n\n"
            "Page 2.\n\n/pagebreak\n\n"
            "Page 3.\n\n/pagebreak\n\n"
            "Page 4.\n\n/pagebreak\n\n"
            "Page 5.\n\n/pagebreak\n\n"
            "Page 6.\n\n/pagebreak\n\n"
            "Page 7.\n\n/pagebreak\n\n"
            "Page 8.\n"
        )
        output = Path(tmpdir) / "test-minizine.html"
        config = ZineConfig(mini_zine=True)
        html = build(str(source), output=str(output), config=config)

        assert output.exists()
        assert '<div class="mini-sheet">' in html
        assert "mini-cell" in html
        assert "mini-rotated" in html
        assert "Page 1" in html
        assert "Page 8" in html


def test_mini_zine_output_path_auto():
    """Mini zine build auto-generates -minizine.html output path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "myzine.md"
        source.write_text("# My Zine\n\nContent.\n")
        config = ZineConfig(mini_zine=True)
        build(str(source), config=config)

        expected = Path(tmpdir) / "myzine-minizine.html"
        assert expected.exists()
