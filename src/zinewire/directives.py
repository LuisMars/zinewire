"""Directive preprocessing for zinewire.

Directives are line-level commands starting with / that get preprocessed
before markdown conversion. They produce either HTML comment markers
(consumed by the paginator) or markdown="1" div containers (processed
by the md_in_html extension).
"""

import re
from typing import Callable


# Internal HTML comment markers used between preprocessing and pagination
MARKERS = {
    "PAGEBREAK": "<!--PAGEBREAK-->",
    "SECTIONBREAK": "<!--SECTIONBREAK-->",
    "COLUMNBREAK": "<!--COLUMNBREAK-->",
    "COLUMNBREAKVISIBLE": "<!--COLUMNBREAKVISIBLE-->",
    "ONECOLUMN": "<!--ONECOLUMN-->",
    "TWOCOLUMNS": "<!--TWOCOLUMNS-->",
    "THREECOLUMNS": "<!--THREECOLUMNS-->",
    "FOURCOLUMNS": "<!--FOURCOLUMNS-->",
    "FIVECOLUMNS": "<!--FIVECOLUMNS-->",

    "LARGETEXT": "<!--LARGETEXT-->",
    "NORMALTEXT": "<!--NORMALTEXT-->",
    "SPACE": "<!--SPACE-->",
}


class DirectiveRegistry:
    """Registry for markdown directives.

    Directives are line-level commands starting with / that get
    preprocessed before markdown conversion. Each directive is a
    regex pattern + handler function.
    """

    def __init__(self):
        self._directives: list[tuple[re.Pattern, Callable]] = []

    def register(self, pattern: str, handler: Callable, flags: int = re.MULTILINE):
        """Register a directive with a regex pattern and handler.

        Args:
            pattern: Regex pattern to match. Should be line-anchored (^...$)
                     to avoid substring collisions.
            handler: Callable that receives a re.Match and returns replacement string.
            flags: Regex flags (default: re.MULTILINE for ^ and $ to match line boundaries).
        """
        self._directives.append((re.compile(pattern, flags), handler))

    def process(self, text: str) -> str:
        """Apply all registered directives to the text in registration order."""
        for pattern, handler in self._directives:
            text = pattern.sub(handler, text)
        return text


def build_default_registry() -> DirectiveRegistry:
    """Create registry with all built-in zinewire directives.

    Directives are registered longest-first to prevent substring collisions.
    All patterns are line-anchored with ^...$ and re.MULTILINE.
    """
    registry = DirectiveRegistry()

    # --- Structural directives (produce HTML comment markers) ---

    # /cover with image and optional size: /cover img/bg.jpg auto
    # Must be before /page to avoid /cover being missed
    registry.register(
        r"^/cover\s+(\S+)\s+(\S+)\s*$",
        lambda m: f'\n<!--COVERPAGE:{m.group(1)}|{m.group(2)}-->\n',
    )
    # /cover with image only: /cover img/bg.jpg
    registry.register(
        r"^/cover\s+(\S+)\s*$",
        lambda m: f'\n<!--COVERPAGE:{m.group(1)}|-->\n',
    )
    # /cover alone (no image)
    registry.register(
        r"^/cover\s*$",
        lambda m: "\n<!--COVERPAGE:-->\n",
    )

    # /page-break (MUST be before /page)
    registry.register(
        r"^/page-break\s*$",
        lambda m: f'\n{MARKERS["SECTIONBREAK"]}\n',
    )
    # /page
    registry.register(
        r"^/page\s*$",
        lambda m: f'\n{MARKERS["PAGEBREAK"]}\n',
    )

    # /column-visible (MUST be before /column)
    registry.register(
        r"^/column-visible\s*$",
        lambda m: f'\n{MARKERS["COLUMNBREAKVISIBLE"]}\n',
    )
    # /one-column (MUST be before /column)
    registry.register(
        r"^/one-column\s*$",
        lambda m: f'\n{MARKERS["ONECOLUMN"]}\n',
    )
    # /two-columns
    registry.register(
        r"^/two-columns\s*$",
        lambda m: f'\n{MARKERS["TWOCOLUMNS"]}\n',
    )
    # /three-columns
    registry.register(
        r"^/three-columns\s*$",
        lambda m: f'\n{MARKERS["THREECOLUMNS"]}\n',
    )
    # /four-columns
    registry.register(
        r"^/four-columns\s*$",
        lambda m: f'\n{MARKERS["FOURCOLUMNS"]}\n',
    )
    # /five-columns
    registry.register(
        r"^/five-columns\s*$",
        lambda m: f'\n{MARKERS["FIVECOLUMNS"]}\n',
    )
    # /column and /col (after longer patterns)
    registry.register(
        r"^/col(?:umn)?\s*$",
        lambda m: f'\n{MARKERS["COLUMNBREAK"]}\n',
    )

    # /large, /normal, /space
    registry.register(
        r"^/large\s*$",
        lambda m: f'\n{MARKERS["LARGETEXT"]}\n',
    )
    registry.register(
        r"^/normal\s*$",
        lambda m: f'\n{MARKERS["NORMALTEXT"]}\n',
    )
    registry.register(
        r"^/space\s*$",
        lambda m: f'\n{MARKERS["SPACE"]}\n',
    )

    # --- Section-wrapping directives (produce markdown="1" divs for web mode) ---

    # /hero [image] — wraps content until next ## heading or end of file
    registry.register(
        r'^/hero\s+(\S+)\s*\n(.*?)(?=^## |\Z)',
        lambda m: (
            f'<div class="hero" style="background-image: url({m.group(1)});" '
            f'markdown="1">\n\n{m.group(2)}\n\n</div>\n\n'
        ),
        flags=re.MULTILINE | re.DOTALL,
    )

    # /cards — wraps content until next ## heading or end of file
    registry.register(
        r'^/cards\s*\n(.*?)(?=^## |\Z)',
        lambda m: f'<div class="cards" markdown="1">\n\n{m.group(1)}\n\n</div>\n\n',
        flags=re.MULTILINE | re.DOTALL,
    )

    # /grid [N] — wraps content until next ## heading, blockquote, or end of file
    registry.register(
        r'^/grid(?:\s+(\d+))?\s*\n(.*?)(?=^## |^> |\Z)',
        lambda m: (
            f'<div class="grid grid-cols-{m.group(1)}" markdown="1">\n\n{m.group(2)}\n\n</div>\n\n'
            if m.group(1)
            else f'<div class="grid" markdown="1">\n\n{m.group(2)}\n\n</div>\n\n'
        ),
        flags=re.MULTILINE | re.DOTALL,
    )

    # /link-card "url" — wraps content until next /link-card, ## heading, blockquote, or EOF
    registry.register(
        r'^/link-card\s+"([^"]+)"\s*\n(.*?)(?=^/link-card |^## |^> |\Z)',
        lambda m: (
            '<div class="link-card" markdown="1">\n\n'
            + re.sub(
                r'^\*\*([^*]+)\*\*',
                rf'[**\1**]({m.group(1)})',
                m.group(2).strip(),
                count=1,
                flags=re.MULTILINE,
            )
            + '\n\n</div>\n\n'
        ),
        flags=re.MULTILINE | re.DOTALL,
    )

    return registry
