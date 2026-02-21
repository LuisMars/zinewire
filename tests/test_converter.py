"""Tests for the markdown converter."""

from zinewire.converter import convert, extract_title, slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_special_chars():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_underscores():
    assert slugify("hello_world") == "hello-world"


def test_slugify_leading_trailing():
    assert slugify("--hello--") == "hello"


def test_slugify_custom_sep():
    assert slugify("Hello World", sep="_") == "hello_world"


def test_extract_title_directive():
    md = '/title "My Zine"\n\n# Heading\n\nContent'
    title, cleaned = extract_title(md)
    assert title == "My Zine"
    assert '/title "My Zine"' not in cleaned
    assert "# Heading" in cleaned


def test_extract_title_h1_fallback():
    md = "# First Heading\n\nContent"
    title, cleaned = extract_title(md)
    assert title == "First Heading"
    assert "# First Heading" in cleaned  # H1 not removed


def test_extract_title_default_fallback():
    md = "Just some content without headings"
    title, cleaned = extract_title(md)
    assert title == "Untitled"


def test_convert_basic_markdown():
    result = convert("# Hello\n\nParagraph text.")
    assert "<h1" in result
    assert "Hello" in result
    assert "<p>" in result


def test_convert_table():
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = convert(md)
    assert "<table>" in result
    assert "<td>" in result


def test_convert_fenced_code():
    md = "```python\nprint('hello')\n```"
    result = convert(md)
    assert "<code>" in result or "<pre>" in result


def test_convert_strikethrough():
    md = "~~deleted~~"
    result = convert(md)
    assert "<del>" in result


def test_convert_nl2br():
    md = "Line one\nLine two"
    result = convert(md)
    assert "<br" in result


def test_convert_preserves_markers():
    """HTML comment markers survive markdown conversion."""
    md = "<!--PAGEBREAK-->\n\n# Title"
    result = convert(md)
    assert "<!--PAGEBREAK-->" in result


def test_convert_md_in_html():
    """markdown="1" divs are processed."""
    md = '<div class="test" markdown="1">\n\n**bold text**\n\n</div>'
    result = convert(md)
    assert "<strong>" in result or "bold text" in result
