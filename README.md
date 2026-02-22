# zinewire

Markdown to paginated print HTML for zines. Write in markdown, get print-ready HTML with automatic pagination, column layouts, booklet imposition, and more.

**Prerequisites:** [Python 3.10+](https://www.python.org/downloads/) with pip.

```bash
git clone https://github.com/yourusername/zinewire.git
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

The dev server opens a browser with a visual config editor, live preview across all output modes, and zoom controls.

## Output modes

zinewire produces three output formats from the same markdown source:

| Mode | Description | Output |
|------|-------------|--------|
| **print** | Paginated A5 pages with columns, covers, page numbers | `my-zine.html` |
| **manual** | Responsive web manual, no pagination | `my-zine-manual.html` |
| **web** | Single-page site with hero, cards, grid sections | `my-zine-web.html` |

```bash
# Build a specific mode
zinewire build my-zine.md --mode print

# Build all three modes (default)
zinewire build my-zine.md
```

## CLI reference

### `zinewire build [source]`

| Flag | Description |
|------|-------------|
| `-o, --output` | Output HTML file path |
| `-c, --config` | Path to `zinewire.toml` config file |
| `--mode` | Build mode: `print`, `web`, `manual` (default: all three) |
| `--page-size` | Page size preset or custom, e.g. `a5`, `letter`, `120x170mm` |
| `--columns` | Default column count 1-5 (default: 2) |
| `--compact` | Enable compact/dense layout |
| `--title` | Override document title |
| `--booklet` | Generate booklet imposition for saddle-stitch printing |
| `--mini-zine` | Generate one-sheet fold-and-cut mini zine (8 pages) |

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

### Directives

Directives are lines starting with `/` that control layout and structure.

#### Page structure

| Directive | Description |
|-----------|-------------|
| `/title "My Zine"` | Set the document title |
| `/cover` | Cover page (optionally `/cover image.jpg` or `/cover image.jpg large`) |
| `/page` | Hard page break |
| `/column` or `/col` | Column break |
| `/column-visible` | Column break with visible separator |
| `/space` | Vertical spacer |

#### Column layouts

| Directive | Description |
|-----------|-------------|
| `/one-column` | Switch to single column |
| `/two-columns` | Switch to two columns (default) |
| `/three-columns` | 3-column flexbox layout |
| `/four-columns` | 4-column layout |
| `/five-columns` | 5-column layout |

#### Text styling

| Directive | Description |
|-----------|-------------|
| `/compact` | Enable compact/dense layout |
| `/large` | Start large text section |
| `/normal` | End large text, return to normal |

#### Web/manual mode

| Directive | Description |
|-----------|-------------|
| `/hero image.jpg` | Hero section with background image |
| `/cards` | Card container (wraps content until next `##`) |
| `/grid 3` | Responsive grid layout (wraps until next `##`) |
| `/link-card "https://..."` | Clickable card with URL |

#### Data

| Directive | Description |
|-----------|-------------|
| `/table data.json` | Render a JSON file as a markdown table |
| `/version` | Replaced with version string from config or `VERSION` file |

### Markdown features

zinewire supports standard markdown plus:

- Tables
- Fenced code blocks
- Strikethrough (`~text~`)
- Auto-linked URLs
- Attribute lists (`{.class #id}`)
- Newline to `<br>` conversion

### Example

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
mode = "print"
compact = false
files = ["intro.md", "chapter*.md", "appendix.md"]
version = "v1.0"

[theme]
font-heading = "Montserrat"
font-body = "PT Serif"
font-mono = "Ubuntu Mono"
color-accent = "#2563EB"
color-text = "#1a1a1a"

# Optional fine-tuning
font-size-body = "9.25pt"
font-size-h1 = "13pt"
page-number-color = "#999"
page-number-size = "8pt"
column-justify = "flex-start"
custom-css = "my-style.css"

[margins]
vertical = "10mm"
horizontal = "8mm"
spine = "12mm"

[output]
path = "build/output.html"
booklet = false
mini-zine = false
```

All fields are optional. Defaults are shown above where applicable.

### Page sizes

| Preset | Dimensions | Notes |
|--------|-----------|-------|
| `a4` | 210 x 297mm | |
| `a5` | 148 x 210mm | Default, classic zine size |
| `a6` | 105 x 148mm | |
| `a7` | 74 x 105mm | Classic mini-zine |
| `letter` | 215.9 x 279.4mm | US Letter |
| `half-letter` | 139.7 x 215.9mm | |
| `quarter-letter` | 108 x 139.7mm | |
| `digest` | 139.7 x 215.9mm | Same as half-letter |

Landscape variants available: `a4-landscape`, `a5-landscape`, `a6-landscape`.

Custom sizes: `120x170mm` (any `WxHmm` format).

### Theme colors

| Key | Default | Description |
|-----|---------|-------------|
| `color-text` | `#1a1a1a` | Body text |
| `color-border` | `#333` | Borders and rules |
| `color-bg-muted` | `#f5f5f5` | Muted backgrounds |
| `color-text-muted` | `#666` | Muted text |
| `color-table-header-bg` | `#000` | Table header background |
| `color-table-header-text` | `#fff` | Table header text |
| `color-accent` | `#2563EB` | Links and accents |

## Booklet printing

Generate saddle-stitch booklet imposition — pages rearranged for double-sided printing, folding, and stapling:

```bash
zinewire build my-zine.md --booklet
```

This produces `my-zine-booklet.html` with A5 pages paired on A4 landscape sheets in the correct folding order. Print double-sided, fold in half, staple at the spine.

## Mini zines

Generate an 8-page mini zine on a single sheet:

```bash
zinewire build my-zine.md --mini-zine
```

Print, fold, and cut to make a pocket-sized zine from one piece of paper.

## JSON tables

Create a JSON file with your data:

```json
{
    "columns": ["Name", "Price", "Weight"],
    "items": [
        {"name": "Sword", "price": "10g", "weight": "3lb"},
        {"name": "Shield", "price": "8g", "weight": "5lb"}
    ],
    "align": ["left", "right", "center"],
    "display_columns": ["Item", "Cost", "Wt"]
}
```

Reference it in your markdown:

```
/table equipment.json
```

`align` and `display_columns` are optional.

## Dev server

```bash
zinewire serve my-zine.md
```

Opens a browser with:

- **Config editor** — visual controls for fonts, colors, margins, page size, columns
- **Live preview** — auto-rebuilds on file changes
- **Mode tabs** — switch between Print, Spread, Mini, Manual, and Web views
- **Zoom control** — scale the preview from 25% to 150%

The config editor saves changes to `zinewire.toml` automatically.

### Server URLs

| URL | Description |
|-----|-------------|
| `/_config` | Config editor (default) |
| `/print` | Print mode preview |
| `/spread` | Two-page spread preview |
| `/mini` | Mini zine preview |
| `/manual` | Web manual preview |
| `/web` | Web page preview |

## Multi-file builds

Use the `files` list in `zinewire.toml` to build from multiple markdown files:

```toml
[zine]
title = "My Zine"
files = ["intro.md", "chapter*.md", "appendix.md"]
```

Glob patterns are supported. Files are concatenated in order.

## Custom CSS

Add a `custom-css` field in the theme section:

```toml
[theme]
custom-css = "my-style.css"
```

The CSS file path is relative to the TOML config location. Custom CSS is loaded after all built-in styles, so it can override anything.

## Installation

### Prerequisites

Install [Python 3.10 or newer](https://www.python.org/downloads/):

| OS | Command |
|----|---------|
| **macOS** | `brew install python` or download from [python.org](https://www.python.org/downloads/) |
| **Ubuntu/Debian** | `sudo apt install python3 python3-pip python3-venv` |
| **Fedora** | `sudo dnf install python3 python3-pip` |
| **Windows** | Download from [python.org](https://www.python.org/downloads/) — check "Add to PATH" during install |

Verify with `python3 --version` (or `python --version` on Windows).

### Install zinewire

```bash
git clone https://github.com/yourusername/zinewire.git
cd zinewire
pip install -e .
```

On some systems you may need `pip3` instead of `pip`, or use `python3 -m pip install -e .`.

## Dependencies

- [markdown](https://python-markdown.github.io/) — Markdown parsing
- [pymdown-extensions](https://facelessuser.github.io/pymdown-extensions/) — Extended markdown features

The dev server uses Python stdlib only (no Flask, no Node.js).

## License

MIT
