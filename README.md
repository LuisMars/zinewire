# zinewire

Markdown to paginated print HTML for zines. Write in markdown, get print-ready HTML with automatic pagination, column layouts, booklet imposition, and more.

## Install

Requires [Python 3.10+](https://www.python.org/downloads/).

```bash
pip install zinewire
```

Or install from source:

```bash
git clone https://github.com/luismars/zinewire.git
cd zinewire
pip install -e .
```

## Quick start

```bash
# Build a zine from markdown
zinewire build my-zine.md

# Start the dev server with live reload + config editor
zinewire serve my-zine.md
```

## Output modes

zinewire produces three output formats from the same markdown source:

| Mode | Description | Output |
|------|-------------|--------|
| **print** | Paginated pages with columns, covers, page numbers | `stem-print.html` |
| **manual** | Scrollable web manual with sidebar table of contents | `stem-manual.html` |
| **web** | Single-page site with hero, cards, grid sections | `stem-web.html` |

### Imposition modes

Build print-ready folding layouts on top of print mode:

| Flag | Description | Output |
|------|-------------|--------|
| `--booklet` | Saddle-stitch booklet (pages on landscape sheets for folding + stapling) | `stem-booklet.html` |
| `--mini-zine` | 8 pages on 1 sheet, fold-and-cut | `stem-minizine.html` |
| `--trifold` | Tri-fold letter fold (6 panels on 2 sides) | `stem-trifold.html` |
| `--french-fold` | French fold (4 pages, 2 folds) | `stem-frenchfold.html` |
| `--micro-mini` | 16 pages on 1 double-sided sheet | `stem-micromini.html` |

## CLI reference

### `zinewire build [source]`

| Flag | Description |
|------|-------------|
| `-o, --output` | Output HTML file path |
| `-c, --config` | Path to `zinewire.toml` config file |
| `--mode` | Build mode: `print`, `web`, `manual` (default: all three) |
| `--page-size` | Page size preset or custom, e.g. `a5`, `letter`, `120x170mm` |
| `--columns` | Default column count 1-5 (default: 2) |
| `--title` | Override document title |
| `--dev` | Enable dev mode (page fill indicators) |
| `--booklet` | Booklet imposition |
| `--mini-zine` | Mini zine imposition |
| `--trifold` | Tri-fold imposition |
| `--french-fold` | French fold imposition |
| `--micro-mini` | Micro-mini imposition |

### `zinewire serve [source]`

| Flag | Description |
|------|-------------|
| `-p, --port` | Server port (default: 5555) |
| `-c, --config` | Path to `zinewire.toml` config file |
| `--mode` | Override output mode |
| `--no-open` | Don't auto-open browser |

### Source resolution

If no source file is given, zinewire looks for:

1. A `files` list in `zinewire.toml`
2. A single `.md` file in the current directory
3. Multiple `.md` files in the current directory (concatenated in order)

## Writing content

Content is written in standard markdown with zinewire directives — line-level commands starting with `/` that control page breaks, column layouts, covers, and more.

See [LANGUAGE.md](LANGUAGE.md) for the full directive reference, configuration options, and recipes.

### Quick example

```markdown
/title "Urban Foraging Field Guide"

/cover foraging-cover.jpg

# Introduction

/two-columns

Welcome to the field guide. This zine covers
the basics of identifying edible plants in
urban environments.

/col

**What you'll need:**
- A field guide (this one!)
- Paper bags
- A small knife

/page

/three-columns

## Dandelion

Every part is edible. Young leaves for salads,
roots for tea, flowers for fritters.

/col

## Nettle

Wear gloves! Once cooked or dried, the sting
disappears. Rich in iron and vitamins.

/col

## Clover

Both red and white clover are edible. Flowers
make a mild tea. Leaves work in salads.
```

## Configuration

Create a `zinewire.toml` next to your markdown files:

```toml
[zine]
title = "My Zine"
page-size = "a5"
columns = 2
files = ["intro.md", "chapter*.md"]

[theme]
font-heading = "Montserrat"
font-body = "PT Serif"
color-accent = "#2563EB"

[margins]
vertical = "10mm"
horizontal = "8mm"
spine = "12mm"

[output]
booklet = true
```

All fields are optional. See [LANGUAGE.md](LANGUAGE.md) for every available option.

## Dev server

```bash
zinewire serve my-zine.md
```

Opens a browser with:

- **Config editor** (`/_config`) — visual controls for fonts, colors, margins, page size, columns
- **Live preview** — auto-rebuilds on file changes via SSE
- **Mode tabs** — switch between Print, Spread, Mini, Manual, and Web views
- **Zoom control** — scale the preview

| URL | Description |
|-----|-------------|
| `/_config` | Config editor (default) |
| `/print` | Print mode preview |
| `/spread` | Two-page spread preview |
| `/mini` | Mini zine preview |
| `/manual` | Web manual preview |
| `/web` | Web page preview |

## Python API

```python
from zinewire import build
from zinewire.config import ZineConfig

config = ZineConfig(
    title="My Zine",
    page_size="a5",
    default_columns=2,
    booklet=True,
)
html = build("my-zine.md", output="my-zine-booklet.html", config=config)
```

## Web editor

A browser-based editor that runs zinewire entirely client-side via [Pyodide](https://pyodide.org/) (Python compiled to WebAssembly). No backend, no Python install required.

See [packages/web/README.md](packages/web/README.md) for details.

## VSCode extension

Live preview panel for markdown files. Uses the same Pyodide engine — no Python install required.

See [packages/vscode/README.md](packages/vscode/README.md) for details.

## Examples

| Example | Description |
|---------|-------------|
| [mini-zine/](examples/mini-zine/) | Single-file half-letter zine — "How to Make a Zine" |
| [field-guide/](examples/field-guide/) | Multi-file A4 landscape booklet with JSON tables |
| [workshop-manual/](examples/workshop-manual/) | Manual mode with sidebar ToC — "Screenprinting at Home" |
| [poetry-chapbook/](examples/poetry-chapbook/) | Single-column A6 poetry with Cormorant Garamond |
| [recipe-zine/](examples/recipe-zine/) | Two-column half-letter recipe layout |

## Dependencies

- [markdown](https://python-markdown.github.io/) — Markdown parsing
- [pymdown-extensions](https://facelessuser.github.io/pymdown-extensions/) — Extended markdown features

The dev server uses Python stdlib only (no Flask, no Node.js).

## License

MIT
