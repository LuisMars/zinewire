"""Markdown to HTML conversion with directive preprocessing."""

import re

import markdown
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension

from .directives import DirectiveRegistry, build_default_registry


def slugify(text, sep="-"):
    """Convert text to URL-friendly slug."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", sep, slug)
    slug = slug.strip(sep)
    return slug


def _make_extensions():
    """Create fresh markdown extension instances.

    Extensions carry state between calls, so we create new instances each time.
    """
    return [
        TableExtension(),
        FencedCodeExtension(),
        AttrListExtension(),
        TocExtension(slugify=slugify),
        "pymdownx.superfences",
        "pymdownx.magiclink",
        "pymdownx.tilde",
        "markdown.extensions.nl2br",
        "markdown.extensions.md_in_html",
    ]


DEFAULT_EXTENSION_CONFIGS = {
    "pymdownx.superfences": {"custom_fences": []},
}


def extract_title(md_text: str, fallback: str = "Untitled") -> tuple[str, str]:
    """Extract /title directive from markdown, return (title, cleaned_text)."""
    # Quoted form: /title "My Title"
    title_match = re.search(r'^/title\s+"([^"]+)"', md_text, re.MULTILINE)
    if title_match:
        title = title_match.group(1)
        cleaned = re.sub(
            r'^/title\s+"[^"]+"\s*\n?', "", md_text, count=1, flags=re.MULTILINE
        )
        return title, cleaned

    # Unquoted form: /title My Title
    title_match = re.search(r'^/title\s+(.+)$', md_text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        cleaned = re.sub(
            r'^/title\s+.+\n?', "", md_text, count=1, flags=re.MULTILINE
        )
        return title, cleaned

    # Fall back to first H1
    h1_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip(), md_text

    return fallback, md_text


def convert(
    md_text: str,
    registry: DirectiveRegistry | None = None,
    extensions: list | None = None,
    extension_configs: dict | None = None,
) -> str:
    """Convert markdown text to HTML with directive preprocessing.

    1. Run directive preprocessing (registry)
    2. Run markdown conversion with extensions

    Returns raw HTML body (not wrapped in a document).
    """
    if registry is None:
        registry = build_default_registry()

    # Preprocess directives
    processed = registry.process(md_text)

    # Convert markdown to HTML
    exts = extensions if extensions is not None else _make_extensions()
    ext_configs = (
        extension_configs if extension_configs is not None else DEFAULT_EXTENSION_CONFIGS
    )

    html_body = markdown.markdown(
        processed,
        extensions=exts,
        extension_configs=ext_configs,
    )

    return html_body
