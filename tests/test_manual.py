"""Tests for manual mode: ToC generation and scroll spy."""

from zinewire.manual import generate_toc, scrollspy_script


def test_generate_toc_basic():
    """ToC extracts h1, h2, h3 headers with IDs."""
    html = '''
    <h1 id="intro">Introduction</h1>
    <p>Some content</p>
    <h2 id="getting-started">Getting Started</h2>
    <p>More content</p>
    <h3 id="prereqs">Prerequisites</h3>
    '''
    toc = generate_toc(html)

    assert '<nav class="sidebar">' in toc
    assert 'class="sidebar-nav"' in toc
    assert '<a href="#intro">Introduction</a>' in toc
    assert '<a href="#getting-started">Getting Started</a>' in toc
    assert '<a href="#prereqs">Prerequisites</a>' in toc


def test_generate_toc_levels():
    """ToC items have correct CSS classes for their heading level."""
    html = '''
    <h1 id="h1">Level One</h1>
    <h2 id="h2">Level Two</h2>
    <h3 id="h3">Level Three</h3>
    '''
    toc = generate_toc(html)

    assert 'class="toc-h1"' in toc
    assert 'class="toc-h2"' in toc
    assert 'class="toc-h3"' in toc


def test_generate_toc_strips_inner_html():
    """ToC strips HTML tags from header content (e.g. anchor links)."""
    html = '<h1 id="test">Title <a href="#test" class="toc-link">link</a></h1>'
    toc = generate_toc(html)

    assert "Title link" in toc
    assert "<a href" not in toc or 'href="#test"' in toc


def test_generate_toc_empty():
    """ToC returns empty string if no headers found."""
    html = "<p>No headers here</p>"
    toc = generate_toc(html)

    assert toc == ""


def test_generate_toc_no_id():
    """Headers without IDs are not included in ToC."""
    html = '<h1>No ID</h1><h1 id="with-id">With ID</h1>'
    toc = generate_toc(html)

    assert "No ID" not in toc
    assert "With ID" in toc


def test_generate_toc_empty_text_skipped():
    """Headers with empty text after stripping are skipped."""
    html = '<h1 id="empty"><a href="#empty"></a></h1><h1 id="real">Real</h1>'
    toc = generate_toc(html)

    # Should only have the "Real" entry, not the empty one
    assert 'href="#real"' in toc
    assert toc.count("<li") == 1


def test_scrollspy_script_content():
    """Scroll spy script contains expected functions."""
    script = scrollspy_script()

    assert "updateActiveLink" in script
    assert "toggleSidebar" in script
    assert "window.addEventListener" in script
    assert "DOMContentLoaded" in script


def test_scrollspy_script_is_html():
    """Scroll spy script is wrapped in script tags."""
    script = scrollspy_script()

    assert script.strip().startswith("<script>")
    assert script.strip().endswith("</script>")
