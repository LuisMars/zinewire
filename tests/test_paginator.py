"""Tests for the paginator state machine."""

from zinewire.config import ZineConfig
from zinewire.paginator import paginate, strip_markers


def test_empty_input():
    result = paginate("")
    assert result == ""


def test_single_page_wrapping():
    """Content without markers gets wrapped in a single page."""
    result = paginate("<p>Hello world</p>")
    assert '<div class="page">' in result
    assert '<div class="two-column">' in result
    assert "<p>Hello world</p>" in result


def test_page_break_creates_separate_pages():
    html = "<p>Page 1</p><!--PAGEBREAK--><p>Page 2</p>"
    result = paginate(html)
    assert result.count('<div class="page">') == 2
    assert "<p>Page 1</p>" in result
    assert "<p>Page 2</p>" in result


def test_cover_page_no_image():
    html = "<!--COVERPAGE:--><h1>Title</h1>"
    result = paginate(html)
    assert 'class="page cover-page"' in result
    assert '<div class="cover-content">' in result


def test_cover_page_with_image():
    html = "<!--COVERPAGE:img/bg.jpg|auto--><h1>Title</h1>"
    result = paginate(html)
    assert "background-image: url(img/bg.jpg)" in result
    assert "background-size: auto" in result


def test_secondary_cover():
    html = "<!--COVERPAGE:--><h1>Cover 1</h1><!--PAGEBREAK--><!--COVERPAGE:--><h1>Cover 2</h1>"
    result = paginate(html)
    assert "secondary-cover" in result


def test_one_column_switch():
    html = "<p>Two col</p><!--ONECOLUMN--><p>One col</p>"
    result = paginate(html)
    assert '<div class="two-column">' in result
    assert '<div class="single-column">' in result


def test_two_column_switch_back():
    html = "<!--ONECOLUMN--><p>One</p><!--TWOCOLUMNS--><p>Two</p>"
    result = paginate(html)
    assert '<div class="single-column">' in result
    assert '<div class="two-column">' in result


def test_single_column_default():
    config = ZineConfig(default_columns=1)
    html = "<p>Content</p>"
    result = paginate(html, config=config)
    assert '<div class="single-column">' in result
    assert '<div class="two-column">' not in result


def test_column_break_css_mode():
    """1-2 column mode: column break becomes a CSS break div."""
    html = "<p>Col 1</p><!--COLUMNBREAK--><p>Col 2</p>"
    result = paginate(html)
    assert '<div class="column-break">' in result


def test_three_column_flexbox():
    """3+ column mode: content is wrapped in flexbox column divs."""
    config = ZineConfig(default_columns=3)
    html = "<p>Col 1</p><!--COLUMNBREAK--><p>Col 2</p><!--COLUMNBREAK--><p>Col 3</p>"
    result = paginate(html, config=config)
    assert '<div class="three-column">' in result
    assert result.count('<div class="column">') == 3


def test_four_column_flexbox():
    config = ZineConfig(default_columns=4)
    html = "<p>A</p><!--COLUMNBREAK--><p>B</p><!--COLUMNBREAK--><p>C</p><!--COLUMNBREAK--><p>D</p>"
    result = paginate(html, config=config)
    assert '<div class="four-column">' in result
    assert result.count('<div class="column">') == 4


def test_five_column_flexbox():
    config = ZineConfig(default_columns=5)
    html = "<p>1</p><!--COLUMNBREAK--><p>2</p><!--COLUMNBREAK--><p>3</p><!--COLUMNBREAK--><p>4</p><!--COLUMNBREAK--><p>5</p>"
    result = paginate(html, config=config)
    assert '<div class="five-column">' in result
    assert result.count('<div class="column">') == 5


def test_mid_page_column_switch_to_three():
    """Switch from 2-column to 3-column mid-page."""
    html = "<p>Two col</p><!--THREECOLUMNS--><p>A</p><!--COLUMNBREAK--><p>B</p><!--COLUMNBREAK--><p>C</p>"
    result = paginate(html)
    assert '<div class="two-column">' in result
    assert '<div class="three-column">' in result
    assert result.count('<div class="column">') == 3


def test_large_text_transform():
    html = "<!--LARGETEXT--><p>Big</p><!--NORMALTEXT-->"
    result = paginate(html)
    assert '<div class="large-text">' in result
    assert "</div>" in result


def test_space_transform():
    html = "<!--SPACE-->"
    result = paginate(html)
    assert '<div class="spacer"></div>' in result


def test_section_break_transform():
    html = "<p>Before</p><!--SECTIONBREAK--><p>After</p>"
    result = paginate(html)
    assert '<div class="page-break-marker">' in result


def test_column_break_visible():
    html = "<p>Before</p><!--COLUMNBREAKVISIBLE--><p>After</p>"
    result = paginate(html)
    assert '<div class="column-break-visible">' in result


def test_empty_column_divs_cleaned():
    """Empty column/cover divs should be removed."""
    html = "<!--COVERPAGE:--><!--PAGEBREAK--><p>Content</p>"
    result = paginate(html)
    # The cover page had no content, so cover-content div should be cleaned
    assert '<div class="cover-content">\n</div>' not in result


def test_file_indicators_dev_mode():
    config = ZineConfig(dev_mode=True)
    html = "<!--FILE:chapter1.md--><p>Content</p>"
    result = paginate(html, config=config)
    assert '<div class="file-indicator">chapter1.md</div>' in result


def test_file_indicators_hidden_by_default():
    html = "<!--FILE:chapter1.md--><p>Content</p>"
    result = paginate(html)
    assert "file-indicator" not in result
    assert "chapter1.md" not in result


def test_strip_markers():
    html = (
        "<!--PAGEBREAK--><p>Text</p><!--COLUMNBREAK-->"
        "<!--ONECOLUMN--><!--TWOCOLUMNS--><!--COVERPAGE:img.jpg|auto-->"
        "<!--LARGETEXT--><p>Big</p><!--NORMALTEXT-->"
        "<!--SPACE--><!--FILE:test.md-->"
    )
    result = strip_markers(html)
    assert "<!--" not in result
    assert '<div class="large-text">' in result
    assert '<div class="spacer"></div>' in result


def test_page_count():
    html = "<!--COVERPAGE:--><h1>Cover</h1><!--PAGEBREAK--><p>Page 2</p><!--PAGEBREAK--><p>Page 3</p>"
    result = paginate(html)
    assert result.count('<div class="page') == 3
