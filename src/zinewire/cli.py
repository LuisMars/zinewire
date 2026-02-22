"""Command-line interface for zinewire."""

import argparse
import sys
from pathlib import Path


def _find_markdown_files(base_dir: Path | None = None) -> list[str]:
    """Find markdown files in a directory, sorted alphabetically.

    Returns list of file paths as strings, or empty list if none found.
    """
    base = base_dir or Path(".")
    files = sorted(base.glob("*.md"))
    return [str(f) for f in files]


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="zinewire",
        description="Markdown to paginated print HTML for zines",
    )
    subparsers = parser.add_subparsers(dest="command")

    # build
    build_parser = subparsers.add_parser("build", help="Build HTML from markdown")
    build_parser.add_argument(
        "source",
        nargs="?",
        help="Markdown file to convert (omit to auto-detect)",
    )
    build_parser.add_argument("-o", "--output", help="Output HTML file path")
    build_parser.add_argument(
        "-c", "--config",
        help="Path to zinewire.toml config file",
    )
    build_parser.add_argument(
        "--mode",
        choices=["print", "web", "manual"],
        help="Build only this mode (default: all three)",
    )
    build_parser.add_argument(
        "--page-size",
        help="Page size: a5, a6, a7, half-letter, quarter-letter, etc. or WxHmm (default: a5)",
    )
    build_parser.add_argument(
        "--columns",
        type=int,
        help="Default column count: 1-5 (default: 2)",
    )
    build_parser.add_argument(
        "--title",
        help="Override document title",
    )
    build_parser.add_argument(
        "--dev",
        action="store_true",
        default=None,
        help="Enable dev mode (file indicators)",
    )
    build_parser.add_argument(
        "--booklet",
        action="store_true",
        default=None,
        help="Generate booklet imposition for saddle-stitch printing",
    )
    build_parser.add_argument(
        "--mini-zine",
        action="store_true",
        default=None,
        help="Generate one-sheet fold-and-cut mini zine (8 pages on 1 sheet)",
    )
    build_parser.add_argument(
        "--trifold",
        action="store_true",
        default=None,
        help="Generate tri-fold letter fold (6 panels on 2 sides)",
    )
    build_parser.add_argument(
        "--french-fold",
        action="store_true",
        default=None,
        help="Generate French fold (4 pages, fold twice)",
    )
    build_parser.add_argument(
        "--micro-mini",
        action="store_true",
        default=None,
        help="Generate micro-mini zine (16 pages on 1 double-sided sheet)",
    )

    # serve
    serve_parser = subparsers.add_parser(
        "serve", help="Start dev server with live reload and config editor"
    )
    serve_parser.add_argument(
        "source",
        nargs="?",
        help="Markdown file to serve (omit to auto-detect)",
    )
    serve_parser.add_argument(
        "-p", "--port",
        type=int,
        default=5555,
        help="Server port (default: 5555)",
    )
    serve_parser.add_argument(
        "-c", "--config",
        help="Path to zinewire.toml config file",
    )
    serve_parser.add_argument(
        "--mode",
        choices=["print", "web", "manual"],
        help="Override output mode",
    )
    serve_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't auto-open browser",
    )

    # Default to build if no subcommand given
    if len(sys.argv) < 2 or sys.argv[1] not in ("build", "serve", "-h", "--help"):
        args = parser.parse_args(["build"] + sys.argv[1:])
    else:
        args = parser.parse_args()

    if args.command == "build":
        _cmd_build(args)

    if args.command == "serve":
        _cmd_serve(args)


def _resolve_source(args, config, config_path):
    """Resolve source file: CLI arg > TOML files list > auto-detect .md files.

    Returns a source path string, or calls sys.exit(1) on failure.
    """
    source = args.source

    # 1. Explicit CLI argument
    if source is not None:
        return source

    # 2. TOML files list
    if config.files:
        return _concatenate_files(config.files, config_path)

    # 3. Auto-detect markdown files in the working directory
    base_dir = Path(config_path).parent if config_path else None
    md_files = _find_markdown_files(base_dir)

    if len(md_files) == 1:
        return md_files[0]
    elif len(md_files) > 1:
        return _concatenate_files(md_files, config_path)

    # Nothing found
    print(
        "Error: No markdown files found.\n"
        "Usage: zinewire build <file.md> or create a zinewire.toml",
        file=sys.stderr,
    )
    sys.exit(1)


def _cmd_build(args):
    """Handle the 'build' command."""
    import copy
    from . import build
    from .config import ZineConfig, load_config

    # Determine config source: TOML file or CLI defaults
    config = None
    config_path = args.config
    if config_path is None and args.source is None:
        # No source file, no --config: look for zinewire.toml
        if Path("zinewire.toml").exists():
            config_path = "zinewire.toml"

    if config_path and Path(config_path).exists():
        try:
            config = load_config(config_path)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        config = ZineConfig()

    # CLI flags override TOML config
    if args.page_size is not None:
        config.page_size = args.page_size
    if args.columns is not None:
        config.default_columns = args.columns
    if args.dev is True:
        config.dev_mode = True
    if args.booklet is True:
        config.booklet = True
    if args.mini_zine is True:
        config.mini_zine = True
    if args.trifold is True:
        config.trifold = True
    if args.french_fold is True:
        config.french_fold = True
    if args.micro_mini is True:
        config.micro_mini = True
    if args.title:
        config.title = args.title

    # Resolve source
    source = _resolve_source(args, config, config_path)

    # Derive output stem: use original source name, not temp file
    if args.source:
        source_stem = Path(args.source).stem
    elif config_path:
        parent = Path(config_path).resolve().parent.name
        source_stem = parent if parent else "zine"
    else:
        source_stem = Path(source).stem

    # Which modes to build
    if args.mode is not None:
        modes = [args.mode]
    else:
        modes = ["print", "manual", "web"]

    # Resolve base directory for relative paths (tables, custom CSS, VERSION)
    base_dir = str(Path(config_path).parent) if config_path else None

    # Build each mode
    for mode in modes:
        mode_config = copy.copy(config)
        mode_config.mode = mode
        # In multi-mode builds, standard outputs are non-imposed
        if len(modes) > 1:
            mode_config.booklet = False
            mode_config.mini_zine = False
            mode_config.trifold = False
            mode_config.french_fold = False
            mode_config.micro_mini = False

        # Output path: explicit -o > single mode (stem.html) > multi-mode (stem-mode.html)
        if args.output:
            output = args.output
        elif config.output_path and len(modes) == 1:
            output = config.output_path
        elif len(modes) == 1:
            output = f"{source_stem}.html"
        else:
            output = f"{source_stem}-{mode}.html"

        try:
            build(source, output=output, config=mode_config, base_dir=base_dir)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # In multi-mode builds, also build booklet/mini-zine as separate outputs
    # (In single-mode builds, the imposition is already applied in the loop)
    if len(modes) > 1:
        if config.booklet and "print" in modes:
            booklet_config = copy.copy(config)
            booklet_config.mode = "print"
            booklet_config.booklet = True
            output = f"{source_stem}-booklet.html"
            try:
                build(source, output=output, config=booklet_config, base_dir=base_dir)
            except Exception as e:
                print(f"Error building booklet: {e}", file=sys.stderr)

        if config.mini_zine and "print" in modes:
            mini_config = copy.copy(config)
            mini_config.mode = "print"
            mini_config.mini_zine = True
            output = f"{source_stem}-minizine.html"
            try:
                build(source, output=output, config=mini_config, base_dir=base_dir)
            except Exception as e:
                print(f"Error building mini zine: {e}", file=sys.stderr)

        # Other imposition modes
        _EXTRA_IMPOSITIONS = [
            ("trifold", "trifold"),
            ("french_fold", "frenchfold"),
            ("micro_mini", "micromini"),
        ]
        for field, suffix in _EXTRA_IMPOSITIONS:
            if getattr(config, field, False) and "print" in modes:
                imp_config = copy.copy(config)
                imp_config.mode = "print"
                setattr(imp_config, field, True)
                output = f"{source_stem}-{suffix}.html"
                try:
                    build(source, output=output, config=imp_config, base_dir=base_dir)
                except Exception as e:
                    print(f"Error building {suffix}: {e}", file=sys.stderr)


def _cmd_serve(args):
    """Handle the 'serve' command."""
    from .server import DevServer
    from .config import ZineConfig, load_config

    config = None
    config_path = args.config
    source = args.source

    if config_path is None and source is None:
        if Path("zinewire.toml").exists():
            config_path = "zinewire.toml"

    if config_path and Path(config_path).exists():
        try:
            config = load_config(config_path)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        config = ZineConfig()

    if args.mode:
        config.mode = args.mode

    # Resolve source
    if source is None and config.files:
        source = config_path or "."
    elif source is None:
        # Auto-detect markdown files
        base_dir = Path(config_path).parent if config_path else None
        md_files = _find_markdown_files(base_dir)
        if len(md_files) == 1:
            source = md_files[0]
        elif len(md_files) > 1:
            # Multi-file: pass config_path so server can rebuild
            source = config_path or "."
            config.files = md_files
        else:
            print(
                "Error: No markdown files found.\n"
                "Usage: zinewire serve <file.md> or create a zinewire.toml",
                file=sys.stderr,
            )
            sys.exit(1)

    server = DevServer(
        source=source,
        port=args.port,
        config_path=config_path if config_path and Path(config_path).exists() else None,
        config=config,
        auto_open=not args.no_open,
    )
    server.start()


def _concatenate_files(files: list[str], config_path: str | None) -> str:
    """Concatenate multiple markdown files into a temp file.

    File paths are resolved relative to the config file's directory.
    Returns the path to the concatenated temp file.
    """
    import glob
    import tempfile

    if config_path:
        base_dir = Path(config_path).parent
    else:
        base_dir = Path(".")

    parts = []
    for pattern in files:
        # Support glob patterns
        matches = sorted(glob.glob(str(base_dir / pattern)))
        if not matches:
            print(f"Warning: no files match '{pattern}'", file=sys.stderr)
            continue
        for match in matches:
            content = Path(match).read_text(encoding="utf-8")
            parts.append(content)

    if not parts:
        print("Error: No source files found from config.", file=sys.stderr)
        sys.exit(1)

    # Write concatenated content to temp file
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    )
    tmp.write("\n\n".join(parts))
    tmp.close()
    return tmp.name


if __name__ == "__main__":
    main()
