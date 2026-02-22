"""Tests for directive preprocessing."""

from zinewire.directives import MARKERS, DirectiveRegistry, build_default_registry


def test_page_directive():
    registry = build_default_registry()
    result = registry.process("/page\n")
    assert MARKERS["PAGEBREAK"] in result


def test_page_break_not_mangled_by_page():
    """Ensure /page-break is not partially replaced by /page."""
    registry = build_default_registry()
    result = registry.process("/page-break\n")
    assert MARKERS["SECTIONBREAK"] in result
    assert MARKERS["PAGEBREAK"] not in result


def test_column_directive():
    registry = build_default_registry()
    result = registry.process("/column\n")
    assert MARKERS["COLUMNBREAK"] in result


def test_col_alias():
    registry = build_default_registry()
    result = registry.process("/col\n")
    assert MARKERS["COLUMNBREAK"] in result


def test_column_visible_not_mangled():
    """Ensure /column-visible is not partially replaced by /column."""
    registry = build_default_registry()
    result = registry.process("/column-visible\n")
    assert MARKERS["COLUMNBREAKVISIBLE"] in result
    assert result.count(MARKERS["COLUMNBREAK"]) == 0 or MARKERS["COLUMNBREAKVISIBLE"] in result


def test_one_column_not_mangled():
    """Ensure /one-column is not partially replaced by /column."""
    registry = build_default_registry()
    result = registry.process("/one-column\n")
    assert MARKERS["ONECOLUMN"] in result


def test_two_columns():
    registry = build_default_registry()
    result = registry.process("/two-columns\n")
    assert MARKERS["TWOCOLUMNS"] in result


def test_three_columns():
    registry = build_default_registry()
    result = registry.process("/three-columns\n")
    assert MARKERS["THREECOLUMNS"] in result


def test_four_columns():
    registry = build_default_registry()
    result = registry.process("/four-columns\n")
    assert MARKERS["FOURCOLUMNS"] in result


def test_five_columns():
    registry = build_default_registry()
    result = registry.process("/five-columns\n")
    assert MARKERS["FIVECOLUMNS"] in result


def test_large_normal_space():
    registry = build_default_registry()
    result = registry.process("/large\n/normal\n/space\n")
    assert MARKERS["LARGETEXT"] in result
    assert MARKERS["NORMALTEXT"] in result
    assert MARKERS["SPACE"] in result


def test_cover_no_image():
    registry = build_default_registry()
    result = registry.process("/cover\n")
    assert "<!--COVERPAGE:-->" in result


def test_cover_with_image():
    registry = build_default_registry()
    result = registry.process("/cover img/bg.jpg\n")
    assert "<!--COVERPAGE:img/bg.jpg|-->" in result


def test_cover_with_image_and_size():
    registry = build_default_registry()
    result = registry.process("/cover img/bg.jpg auto\n")
    assert "<!--COVERPAGE:img/bg.jpg|auto-->" in result


def test_directive_must_be_on_own_line():
    """Directives inline in text should NOT be replaced."""
    registry = build_default_registry()
    result = registry.process("Use the /page command to break pages.\n")
    assert MARKERS["PAGEBREAK"] not in result
    assert "/page" in result


def test_custom_directive_registration():
    registry = DirectiveRegistry()
    registry.register(r"^/custom\s+(.+)$", lambda m: f"CUSTOM:{m.group(1)}")
    result = registry.process("/custom hello world\n")
    assert "CUSTOM:hello world" in result


def test_hero_directive():
    registry = build_default_registry()
    text = "/hero img/banner.jpg\n# Title\n\nSome text\n\n## Next Section\n"
    result = registry.process(text)
    assert 'class="hero"' in result
    assert "background-image: url(img/banner.jpg)" in result
    assert 'markdown="1"' in result


def test_cards_directive():
    registry = build_default_registry()
    text = "/cards\nSome card content\n\n## Next Section\n"
    result = registry.process(text)
    assert 'class="cards"' in result
    assert 'markdown="1"' in result


def test_grid_directive():
    registry = build_default_registry()
    text = "/grid 3\nGrid content\n\n## Next Section\n"
    result = registry.process(text)
    assert 'class="grid grid-cols-3"' in result


def test_grid_directive_no_count():
    registry = build_default_registry()
    text = "/grid\nGrid content\n\n## Next Section\n"
    result = registry.process(text)
    assert 'class="grid"' in result
    assert "grid-cols" not in result


def test_link_card_directive():
    registry = build_default_registry()
    text = '/link-card "https://example.com"\n**Title**\n\nDescription text\n\n## Next\n'
    result = registry.process(text)
    assert 'class="link-card"' in result
    assert "[**Title**](https://example.com)" in result
