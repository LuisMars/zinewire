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
    base_dir: str | Path | None = None,
) -> str:
    """Build HTML from a markdown file.

    Args:
        source: Path to markdown file.
        output: Path for output HTML (default: same name with .html).
        config: Build configuration (default: sensible defaults).
        registry: Directive registry (default: all built-in directives).
        base_dir: Directory to resolve relative paths from (e.g. /table JSON,
                  custom CSS, VERSION file). Defaults to source file's parent.

    Returns:
        The generated HTML string.
    """
    from .imposition import (
        impose, impose_mini_zine,
        impose_trifold, impose_french_fold, impose_micro_mini,
    )
    from .templates import (
        render_booklet, render_manual, render_mini_zine, render_print, render_web,
        render_trifold, render_french_fold, render_micro_mini,
    )

    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    md_text = source_path.read_text(encoding="utf-8")

    if config is None:
        config = ZineConfig()

    if registry is None:
        registry = build_default_registry()

    # Resolve base directory for relative paths (tables, custom CSS, VERSION)
    resolve_dir = Path(base_dir) if base_dir else source_path.parent

    # Extract title from markdown (explicit config title takes priority)
    title, md_text = extract_title(md_text, fallback=source_path.stem)
    if config.title == "Untitled Zine":
        config.title = title

    # Replace /version token with version string
    if config.version:
        md_text = md_text.replace("/version", config.version)
    else:
        # Try VERSION file next to source
        version_file = resolve_dir / "VERSION"
        if version_file.exists():
            ver = version_file.read_text(encoding="utf-8").strip()
            md_text = md_text.replace("/version", ver)

    # Process /table directives (JSON → markdown tables)
    from .tables import process_tables
    md_text = process_tables(md_text, base_dir=resolve_dir)

    # Load custom CSS if specified
    extra_css = ""
    if config.custom_css:
        css_path = resolve_dir / config.custom_css
        if css_path.exists():
            extra_css = css_path.read_text(encoding="utf-8")

    # Convert markdown to HTML
    html_body = convert(md_text, registry=registry)

    # Mode-specific processing
    if config.mode == "web":
        html_body = strip_markers(html_body)
        html = render_web(html_body, config, extra_css=extra_css)
    elif config.mode == "manual":
        html_body = strip_markers(html_body)
        html = render_manual(html_body, config, extra_css=extra_css)
    else:
        # page_size = the sheet you print on. Paginate at reading page
        # size (derived from sheet dimensions by imposition layout).
        has_imposition = (
            config.booklet or config.mini_zine or config.trifold
            or config.french_fold or config.micro_mini
        )
        if has_imposition:
            import copy
            paginate_config = copy.copy(config)
            rw, rh = config.reading_page_dimensions
            rw_mm = float(rw.replace("mm", ""))
            rh_mm = float(rh.replace("mm", ""))
            paginate_config.page_size = f"{rw_mm}x{rh_mm}mm"
            html_body = paginate(html_body, config=paginate_config)
        else:
            html_body = paginate(html_body, config=config)

        if config.micro_mini:
            html_body = impose_micro_mini(html_body, config)
            html = render_micro_mini(html_body, config, extra_css=extra_css)
        elif config.mini_zine:
            html_body = impose_mini_zine(html_body, config)
            html = render_mini_zine(html_body, config, extra_css=extra_css)
        elif config.trifold:
            html_body = impose_trifold(html_body, config)
            html = render_trifold(html_body, config, extra_css=extra_css)
        elif config.french_fold:
            html_body = impose_french_fold(html_body, config)
            html = render_french_fold(html_body, config, extra_css=extra_css)
        elif config.booklet:
            html_body = impose(html_body, config)
            html = render_booklet(html_body, config, extra_css=extra_css)
        else:
            html = render_print(html_body, config, extra_css=extra_css)

    # Write output
    if output is None:
        # Determine suffix from imposition mode
        _IMPOSITION_SUFFIXES = {
            "mini_zine": "-minizine",
            "micro_mini": "-micromini",
            "trifold": "-trifold",
            "french_fold": "-frenchfold",
            "booklet": "-booklet",
        }
        suffix = ""
        for field, sfx in _IMPOSITION_SUFFIXES.items():
            if getattr(config, field, False):
                suffix = sfx
                break
        if suffix:
            output = str(source_path.with_suffix("")) + suffix + ".html"
        else:
            output = str(source_path.with_suffix(".html"))

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    page_count = html_body.count('<div class="page')
    if config.mode == "web":
        print(f"Built {output_path} (web page)")
    elif config.mode == "manual":
        print(f"Built {output_path} (web manual)")
    elif config.mini_zine:
        print(f"Built {output_path} (mini zine, {page_count} pages on 1 sheet)")
    elif config.micro_mini:
        print(f"Built {output_path} (micro mini, {page_count} pages on 1 sheet)")
    elif config.trifold:
        print(f"Built {output_path} (tri-fold, 6 panels)")
    elif config.french_fold:
        print(f"Built {output_path} (french fold, 4 pages)")
    elif config.booklet:
        sheet_count = html_body.count('<div class="sheet"')
        print(f"Built {output_path} ({page_count} pages, {sheet_count} sheets)")
    else:
        print(f"Built {output_path} ({page_count} pages)")

    return html
