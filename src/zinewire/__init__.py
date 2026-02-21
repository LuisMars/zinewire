"""zinewire: Markdown to paginated print HTML for zines."""

from pathlib import Path

from .config import ZineConfig
from .converter import convert, extract_title, slugify
from .directives import DirectiveRegistry, build_default_registry
from .paginator import paginate, strip_markers

__version__ = "0.1.0"


def build(
    source: str,
    output: str | None = None,
    config: ZineConfig | None = None,
    registry: DirectiveRegistry | None = None,
) -> str:
    """Build HTML from a markdown file.

    Args:
        source: Path to markdown file.
        output: Path for output HTML (default: same name with .html).
        config: Build configuration (default: sensible defaults).
        registry: Directive registry (default: all built-in directives).

    Returns:
        The generated HTML string.
    """
    from .imposition import impose, impose_mini_zine
    from .templates import render_booklet, render_landing, render_manual, render_mini_zine, render_print

    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    md_text = source_path.read_text(encoding="utf-8")

    if config is None:
        config = ZineConfig()

    if registry is None:
        registry = build_default_registry()

    # Extract title from markdown (explicit config title takes priority)
    title, md_text = extract_title(md_text, fallback=source_path.stem)
    if config.title == "Untitled Zine":
        config.title = title

    # Replace /version token with version string
    if config.version:
        md_text = md_text.replace("/version", config.version)
    else:
        # Try VERSION file next to source
        version_file = source_path.parent / "VERSION"
        if version_file.exists():
            ver = version_file.read_text(encoding="utf-8").strip()
            md_text = md_text.replace("/version", ver)

    # Process /table directives (JSON → markdown tables)
    from .tables import process_tables
    md_text = process_tables(md_text, base_dir=source_path.parent)

    # Load custom CSS if specified
    extra_css = ""
    if config.custom_css:
        css_path = source_path.parent / config.custom_css
        if css_path.exists():
            extra_css = css_path.read_text(encoding="utf-8")

    # Convert markdown to HTML
    html_body = convert(md_text, registry=registry)

    # Mode-specific processing
    if config.mode == "landing":
        html_body = strip_markers(html_body)
        html = render_landing(html_body, config, extra_css=extra_css)
    elif config.mode == "manual":
        html_body = strip_markers(html_body)
        html = render_manual(html_body, config, extra_css=extra_css)
    else:
        html_body = paginate(html_body, config=config)
        if config.mini_zine:
            html_body = impose_mini_zine(html_body, config)
            html = render_mini_zine(html_body, config, extra_css=extra_css)
        elif config.booklet:
            html_body = impose(html_body, config)
            html = render_booklet(html_body, config, extra_css=extra_css)
        else:
            html = render_print(html_body, config, extra_css=extra_css)

    # Write output
    if output is None:
        if config.mini_zine:
            output = str(source_path.with_suffix("")) + "-minizine.html"
        elif config.booklet:
            output = str(source_path.with_suffix("")) + "-booklet.html"
        else:
            output = str(source_path.with_suffix(".html"))

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    page_count = html_body.count('<div class="page')
    if config.mode == "landing":
        print(f"Built {output_path} (landing page)")
    elif config.mode == "manual":
        print(f"Built {output_path} (web manual)")
    elif config.mini_zine:
        print(f"Built {output_path} (mini zine, {page_count} pages on 1 sheet)")
    elif config.booklet:
        sheet_count = html_body.count('<div class="sheet"')
        print(f"Built {output_path} ({page_count} pages, {sheet_count} sheets)")
    else:
        print(f"Built {output_path} ({page_count} pages)")

    return html
