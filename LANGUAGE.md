# zinewire Language Reference

Complete reference for zinewire's directive language, configuration, and markdown extensions. For installation and getting started, see [README.md](README.md).

---

## Directives

Directives are line-level commands starting with `/` that control layout and structure. Each directive must be on its own line.

### `/title`

Sets the document title (used in `<title>` and can be referenced by templates).

```markdown
/title My Zine Title
/title "My Zine Title"
```

Title priority: explicit `title` in zinewire.toml > `/title` directive > first `# H1` heading > filename.

### `/cover`

Creates a cover page. Several forms:

```markdown
/cover
```
Blank cover page (content after this becomes the cover).

```markdown
/cover background.jpg
```
Cover with a background image.

```markdown
/cover background.jpg auto
/cover background.jpg contain
/cover background.jpg cover
```
Cover with a background image and CSS `background-size` hint. The second argument is passed directly as the `background-size` value.

```markdown
/cover ||contain
```
Cover with no image but a size hint (use `||` as a placeholder for an empty image path).

### `/page`

Hard page break. Starts a new page.

```markdown
## Chapter 1

Some content on page one.

/page

## Chapter 2

This starts on a new page.
```

### `/page-break`

Section break. Functionally similar to `/page` — starts a new page.

### `/col`, `/column`

Column break within the current multi-column layout. Both forms are equivalent.

```markdown
/two-columns

Left column content goes here.

/col

Right column content goes here.
```

### `/column-visible`

Column break with a visible vertical divider line between columns.

```markdown
/two-columns

Left side.

/column-visible

Right side, with a visible line separating the columns.
```

### Column layouts

Switch all subsequent content to a different number of columns. The layout persists until another column directive or a page break.

| Directive | Columns | Implementation |
|-----------|---------|----------------|
| `/one-column` | 1 | CSS `column-count` |
| `/two-columns` | 2 | CSS `column-count` |
| `/three-columns` | 3 | Flexbox |
| `/four-columns` | 4 | Flexbox |
| `/five-columns` | 5 | Flexbox |

Columns 1-2 use CSS `column-count` (content flows naturally). Columns 3-5 use flexbox (content is split at `/col` breaks into equal-width boxes).

```markdown
/three-columns

## Dandelion

Every part is edible.

/col

## Nettle

Wear gloves when picking.

/col

## Clover

Flowers make a mild tea.
```

### `/large`, `/normal`

Toggle large text. `/large` increases the font size for a section, `/normal` returns to the default.

```markdown
/large

This text will be larger than normal.

/normal

Back to regular size.
```

### `/space`

Inserts a vertical spacer.

```markdown
Some content above.

/space

Some content below, with extra space between.
```

### `/version`

Replaced with the version string from `zinewire.toml` (`version` field) or from a `VERSION` file in the source directory. If neither exists, the literal text `/version` remains.

```markdown
Current version: /version
```

### `/table`

Loads a JSON file and renders it as a table. The file path is relative to the zinewire.toml directory.

```markdown
/table data/equipment.json
```

**Simple JSON format:**

```json
{
    "columns": ["Name", "Price", "Weight"],
    "items": [
        {"name": "Sword", "price": "10g", "weight": "3lb"},
        {"name": "Shield", "price": "8g", "weight": "5lb"}
    ]
}
```

**Optional fields:**

```json
{
    "columns": ["Name", "Price", "Weight"],
    "items": [...],
    "align": ["left", "right", "center"],
    "display_columns": ["Item", "Cost", "Wt"]
}
```

- `align` — column alignment (left, right, center). Defaults to left.
- `display_columns` — display names for column headers (overrides `columns` in the rendered output).

**Nested format** (for grouped tables with multiple sections):

```json
{
    "units": {
        "columns": ["Name", "Move", "Attack"],
        "items": [...]
    },
    "behavior": {
        "columns": ["Roll", "Action"],
        "items": [...],
        "title": "Behavior Table"
    },
    "special_rule": "Optional text rendered between tables"
}
```

### Web/landing mode directives

These directives produce `<div>` wrappers and are primarily used in `web` and `manual` modes. They wrap all content until the next `## ` heading or end of file.

#### `/hero`

Hero section with a full-bleed background image.

```markdown
/hero banner.jpg

# Welcome to My Zine

A subtitle or description goes here.

## Next Section
```

#### `/cards`

Wraps content in a card container. Each `### ` heading within becomes a card.

```markdown
/cards

### Feature One

Description of the first feature.

### Feature Two

Description of the second feature.

## Next Section
```

#### `/grid`

Responsive grid layout. Optional number sets the column count.

```markdown
/grid 3

### Item A

Content in first grid cell.

### Item B

Content in second grid cell.

### Item C

Content in third grid cell.

## Next Section
```

Without a number, `/grid` uses a default responsive layout.

#### `/link-card`

Clickable card with a URL. The first `**bold text**` on the first line becomes a hyperlink.

```markdown
/link-card "https://example.com"

**Example Site**

A description of what this link is about.

/link-card "https://another.com"

**Another Link**

More descriptive text here.

## Next Section
```

---

## Configuration

All configuration lives in `zinewire.toml`. Every field is optional — defaults are used when omitted. Only fields that differ from defaults are written when saving via the config editor.

### `[zine]`

| Key | Default | Description |
|-----|---------|-------------|
| `title` | `"Untitled Zine"` | Document title |
| `version` | `""` | Version string (replaces `/version` in content) |
| `page-size` | `"a5"` | Page size preset or custom `WxHmm` |
| `columns` | `2` | Default column count (1-5) |
| `mode` | `"print"` | Output mode: `"print"`, `"web"`, or `"manual"` |
| `files` | `[]` | Source files list; glob patterns supported |

```toml
[zine]
title = "My Zine"
page-size = "half-letter"
columns = 2
files = ["intro.md", "chapter*.md", "appendix.md"]
```

### `[theme]` — Fonts

| Key | Default | Description |
|-----|---------|-------------|
| `font-heading` | `"Montserrat"` | Heading font family |
| `font-body` | `"PT Serif"` | Body text font family |
| `font-mono` | `"Ubuntu Mono"` | Monospace/code font family |

Any [Google Fonts](https://fonts.google.com/) name works. Spaces in font names are preserved.

```toml
[theme]
font-heading = "Bitter"
font-body = "Cormorant Garamond"
font-mono = "JetBrains Mono"
```

### `[theme]` — Font sizes

All font size fields accept any CSS size value (`"9.25pt"`, `"10px"`, `"1.2rem"`). Empty string = use the CSS default.

| Key | CSS Variable | Description |
|-----|-------------|-------------|
| `font-size-body` | `--font-size-body` | Body text |
| `font-size-h1` | `--font-size-h1` | H1 headings |
| `font-size-h2` | `--font-size-h2` | H2 headings |
| `font-size-h3` | `--font-size-h3` | H3 headings |
| `font-size-h4` | `--font-size-h4` | H4 headings |
| `font-size-cover-h1` | `--font-size-cover-h1` | Cover page H1 |
| `font-size-cover-h2` | `--font-size-cover-h2` | Cover page H2 |
| `font-size-small` | `--font-size-small` | Small text |
| `font-size-tiny` | `--font-size-tiny` | Tiny text |
| `font-size-micro` | `--font-size-micro` | Micro text |

```toml
[theme]
font-size-body = "9.25pt"
font-size-h1 = "13pt"
font-size-small = "7pt"
```

### `[theme]` — Colors

| Key | Default | Description |
|-----|---------|-------------|
| `color-text` | `"#1a1a1a"` | Body text color |
| `color-border` | `"#333"` | Borders and rules |
| `color-bg-muted` | `"#f5f5f5"` | Muted backgrounds (blockquotes, code) |
| `color-text-muted` | `"#666"` | Muted text |
| `color-table-header-bg` | `"#000"` | Table header background |
| `color-table-header-text` | `"#fff"` | Table header text |
| `color-accent` | `"#2563EB"` | Links and accent color |
| `color-row-alt` | `""` | Alternating table row background |
| `color-row-border` | `""` | Table row border color |

```toml
[theme]
color-accent = "#2d6a4f"
color-text = "#1a1a1a"
color-table-header-bg = "#1e1b4b"
color-bg-muted = "#fef2f2"
```

### `[theme]` — Typography

| Key | CSS Variable | Description |
|-----|-------------|-------------|
| `line-height` | `--line-height` | Body line height |
| `paragraph-spacing` | `--paragraph-spacing` | Space between paragraphs |
| `letter-spacing-h1` | `--letter-spacing-h1` | H1 letter spacing |
| `letter-spacing-h2` | `--letter-spacing-h2` | H2 letter spacing |
| `letter-spacing-h3` | `--letter-spacing-h3` | H3 letter spacing |
| `letter-spacing-h4` | `--letter-spacing-h4` | H4 letter spacing |

```toml
[theme]
line-height = "1.5"
paragraph-spacing = "0.5em"
letter-spacing-h1 = "-0.02em"
```

### `[theme]` — Layout

| Key | CSS Variable | Description |
|-----|-------------|-------------|
| `column-justify` | `--column-justify` | `justify-content` for 3-5 column flexbox layouts |
| `column-gap` | `--column-gap` | Gap between columns |
| `table-padding` | `--table-cell-padding` | Table cell padding |
| `table-font-size` | `--table-font-size` | Table font size |
| `list-padding` | `--list-padding` | List indentation |

```toml
[theme]
column-gap = "12px"
table-padding = "4px 8px"
table-font-size = "8pt"
```

### `[theme]` — Page numbers

| Key | Default | Description |
|-----|---------|-------------|
| `page-numbers` | `true` | Show/hide page numbers |
| `page-number-color` | `""` | Page number color |
| `page-number-size` | `""` | Page number font size |
| `page-number-font` | `""` | Page number font family |
| `page-number-position` | `""` | Page number position |

```toml
[theme]
page-numbers = true
page-number-color = "#999"
page-number-size = "8pt"
```

### `[theme]` — Custom CSS

| Key | Description |
|-----|-------------|
| `custom-css` | Path to an extra CSS file (relative to zinewire.toml) |

```toml
[theme]
custom-css = "my-style.css"
```

Custom CSS is loaded after all built-in styles, so it can override anything.

### `[margins]`

| Key | Default | Description |
|-----|---------|-------------|
| `vertical` | `"10mm"` | Top and bottom page margin |
| `horizontal` | `"8mm"` | Left and right page margin |
| `spine` | `"12mm"` | Spine-side margin (inner margin for booklets) |

```toml
[margins]
vertical = "12mm"
horizontal = "10mm"
spine = "14mm"
```

### `[output]`

| Key | Default | Description |
|-----|---------|-------------|
| `path` | none | Custom output file path |
| `booklet` | `false` | Enable booklet imposition |
| `mini-zine` | `false` | Enable mini-zine imposition |
| `trifold` | `false` | Enable tri-fold imposition |
| `french-fold` | `false` | Enable French fold imposition |
| `micro-mini` | `false` | Enable micro-mini imposition |

```toml
[output]
booklet = true
```

### `[dev]`

| Key | Default | Description |
|-----|---------|-------------|
| `dev` | `false` | Enable dev mode — shows per-page fill indicators with percentages |

---

## Page sizes

### Presets

| Preset | Dimensions | Notes |
|--------|-----------|-------|
| `a4` | 210 x 297mm | |
| `a5` | 148 x 210mm | Default. Classic zine size |
| `a6` | 105 x 148mm | |
| `a7` | 74 x 105mm | Classic mini-zine (A4 folded in eighths) |
| `letter` | 215.9 x 279.4mm | US Letter |
| `half-letter` | 139.7 x 215.9mm | Letter folded in half |
| `quarter-letter` | 107.95 x 139.7mm | Letter folded in quarters |
| `eighth-letter` | 69.85 x 107.95mm | Letter folded in eighths |
| `digest` | 139.7 x 215.9mm | Same as half-letter |

### Landscape variants

Append `-landscape` to any ISO size: `a4-landscape`, `a5-landscape`, `a6-landscape`.

### Custom sizes

Use `WxHmm` format for any custom dimensions:

```toml
[zine]
page-size = "120x170mm"
```

### Imposition page sizes

When using imposition modes, `page-size` refers to the **sheet you print on**. The reading page size is derived automatically:

| Mode | Reading page | From sheet |
|------|-------------|------------|
| Booklet | width/2 x height | 2 pages side by side |
| Mini-zine | width/4 x height/2 | 4x2 grid |
| Micro-mini | width/4 x height/2 | 4x2 grid per side |
| Tri-fold | width/3 x height | 3 panels per side |
| French fold | width/2 x height/2 | 2x2 grid |

---

## Markdown extensions

Beyond standard markdown, zinewire enables:

| Extension | Syntax | Example |
|-----------|--------|---------|
| Tables | Pipe tables | `| A | B |` |
| Fenced code | Triple backticks | ` ```python ` |
| Attribute lists | `{.class #id}` | `## Heading {.highlight}` |
| Strikethrough | Tilde | `~struck text~` |
| Auto-linked URLs | Bare URLs | `https://example.com` |
| Newline to `<br>` | Line breaks | Newlines become `<br>` |
| Markdown in HTML | `markdown="1"` | Used internally by `/hero`, `/cards`, `/grid` |
| Heading anchors | Auto-generated | Slugified IDs for ToC linking |

---

## Python API

```python
from zinewire import build
from zinewire.config import ZineConfig

# Minimal — uses all defaults
html = build("my-zine.md")

# With configuration
config = ZineConfig(
    title="My Zine",
    page_size="a5",
    default_columns=2,
    font_heading="Bitter",
    color_accent="#2d6a4f",
    booklet=True,
)
html = build("my-zine.md", output="my-zine-booklet.html", config=config)
```

### `build()` parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | `str` | Path to markdown file |
| `output` | `str \| None` | Output HTML path (default: source with `.html` extension) |
| `config` | `ZineConfig \| None` | Build configuration (default: `ZineConfig()`) |
| `registry` | `DirectiveRegistry \| None` | Custom directive registry (default: all built-in directives) |
| `base_dir` | `str \| Path \| None` | Directory for resolving relative paths (default: source file's parent) |

Returns the generated HTML string and writes the file to disk.

---

## Recipes

### Your first zine

A minimal 4-page A5 zine with a cover and two-column body.

**`zine.md`:**

```markdown
/title My First Zine

/cover

# My First Zine

## A pocket guide

/page
/two-columns

## Getting Started

Write your content in markdown. zinewire
handles pagination, columns, and print
layout automatically.

Each `/page` directive starts a new page.
Each `/col` directive starts a new column.

/col

## Tips

- Keep paragraphs short
- Use headings to break up content
- Bold and *italic* work as expected
- Lists are great for quick info

> Blockquotes make good pull quotes
> or callouts.

/page
/one-column

/large

Thanks for reading!

/normal

/space

*Made with zinewire.*
```

Build it:

```bash
zinewire build zine.md
```

This produces `zine.html` — open it in a browser, print to PDF or paper.

---

### Multi-column reference sheet

A dense reference layout using three columns and a JSON data table.

**`reference.md`:**

```markdown
/title Quick Reference Card

/cover

# Quick Reference

## Essential Info

/page
/three-columns

## Section A

Key facts and figures for the
first topic. Keep entries brief.

- Item one
- Item two
- Item three

/col

## Section B

Second column of reference
material.

| Key | Value |
|-----|-------|
| A   | 100   |
| B   | 200   |

/col

## Section C

Third column wrapping up the
reference card.

- Note alpha
- Note beta
- Note gamma

/page
/one-column

/table data/stats.json
```

**`data/stats.json`:**

```json
{
    "columns": ["Category", "Count", "Percentage"],
    "items": [
        {"category": "Alpha", "count": "42", "percentage": "35%"},
        {"category": "Beta", "count": "58", "percentage": "48%"},
        {"category": "Gamma", "count": "20", "percentage": "17%"}
    ],
    "align": ["left", "right", "right"],
    "display_columns": ["Type", "Count", "%"]
}
```

---

### Multi-file project

Split a longer zine across multiple markdown files with a shared config.

**`zinewire.toml`:**

```toml
[zine]
title = "Field Guide"
page-size = "a5"
files = ["cover.md", "intro.md", "chapter*.md", "appendix.md"]

[theme]
font-heading = "Bitter"
color-accent = "#2d6a4f"
```

**`cover.md`:**

```markdown
/cover hero.jpg

# Field Guide

## Volume One
```

**`intro.md`:**

```markdown
/page
/two-columns

## Introduction

Welcome to the guide...
```

**`chapter-01.md`:**

```markdown
/page
/two-columns

## Chapter 1: Basics

Content here...
```

Files are concatenated in the order listed. Glob patterns (`chapter*.md`) expand alphabetically. Build with:

```bash
zinewire build
```

When no source file is specified and a `zinewire.toml` exists, zinewire uses the `files` list automatically.

---

### Print-ready booklet

Build a saddle-stitch booklet — pages rearranged on landscape sheets for double-sided printing, folding, and stapling.

**`zinewire.toml`:**

```toml
[zine]
title = "Booklet Zine"
page-size = "a4-landscape"

[output]
booklet = true
```

Write your content normally — zinewire handles the page imposition:

```bash
zinewire build zine.md
```

This produces:
- `zine-print.html` — normal paginated pages
- `zine-booklet.html` — imposed A4 landscape sheets

**Printing workflow:**
1. Open `zine-booklet.html` in a browser
2. Print double-sided (flip on short edge)
3. Stack all sheets together
4. Fold in half
5. Staple at the spine with a long-reach stapler

Page count should be a multiple of 4 for clean booklets. zinewire adds a warning comment in the HTML if it isn't.

---

### Web manual with sidebar

Build a scrollable web manual with auto-generated table of contents and scroll spy.

**`zinewire.toml`:**

```toml
[zine]
title = "Workshop Manual"
mode = "manual"

[theme]
font-heading = "Space Grotesk"
color-accent = "#7c3aed"
```

**`manual.md`:**

```markdown
/title Workshop Manual

# Workshop Manual

## Getting Started

### Prerequisites

You'll need the following tools...

### Setup

Follow these steps to set up your workspace...

## Techniques

### Basic Method

Start with the fundamentals...

### Advanced Method

Once you're comfortable with the basics...

## Troubleshooting

### Common Issues

If something goes wrong...
```

The table of contents is generated automatically from `h1`, `h2`, and `h3` headings. It appears as a sidebar on desktop and a hamburger menu on mobile.

```bash
zinewire build manual.md --mode manual
```

---

### Landing page

Build a single-page website with hero section, cards, and grid layouts.

**`landing.md`:**

```markdown
/hero banner.jpg

# Welcome

A short tagline about your project.

## Features

/cards

### Easy to Use

Write in markdown, get print-ready HTML.

### Customizable

Fonts, colors, margins — all configurable.

### Multiple Formats

Print, web, and manual from the same source.

## Gallery

/grid 3

### Project A

![Screenshot](img/a.png)

Description of project A.

### Project B

![Screenshot](img/b.png)

Description of project B.

### Project C

![Screenshot](img/c.png)

Description of project C.

## Links

/link-card "https://github.com/example/repo"

**Source Code**

View the project on GitHub.

/link-card "https://example.com/docs"

**Documentation**

Read the full documentation.
```

```bash
zinewire build landing.md --mode web
```

---

### Custom styling

Override built-in styles with a custom CSS file.

**`zinewire.toml`:**

```toml
[zine]
title = "Styled Zine"

[theme]
font-heading = "DM Sans"
font-body = "DM Sans"
color-accent = "#dc2626"
color-border = "#991b1b"
color-bg-muted = "#fef2f2"
font-size-body = "9pt"
line-height = "1.4"
paragraph-spacing = "0.3em"
page-number-color = "#999"
page-number-size = "7pt"
custom-css = "custom.css"

[margins]
vertical = "8mm"
horizontal = "6mm"
```

**`custom.css`:**

```css
/* Custom CSS is loaded after all built-in styles */

h1 {
    text-transform: uppercase;
    border-bottom: 2px solid var(--color-accent);
    padding-bottom: 4px;
}

blockquote {
    border-left: 3px solid var(--color-accent);
    font-style: italic;
}

.page:first-child {
    background: linear-gradient(135deg, #fef2f2, #fff);
}
```

The CSS file path is relative to the `zinewire.toml` location. Custom CSS loads after all built-in styles, so it can override any default styling. You can reference the CSS custom properties (variables) that zinewire sets from your theme configuration.

---

## How pagination works

zinewire's paginator is a state machine, not a content-measuring layout engine. Understanding how it works helps you write content that paginates well.

### Pages are opened by content, closed by markers

Pages are created lazily — a new page opens only when non-whitespace content is encountered. Pages close when the paginator hits a `/page` break, a `/cover` directive, or the end of the document. There is no automatic page splitting based on content height. If your content is longer than one page, it will overflow visually — the paginator does not break paragraphs or elements across pages. You control pagination with explicit `/page` directives.

### Column behavior differs by count

**1-2 columns** use CSS `column-count`. Content flows naturally into columns and the browser handles the split. A `/col` break uses CSS `break-after: column` to force a column break at that point.

**3-5 columns** use flexbox with explicit `<div class="column">` elements. Each `/col` break starts a new column box. Content between `/col` breaks is placed into equal-width flex children. Within each column, sections (grouped by headings) are distributed using `justify-content` (configurable via `column-justify`).

This means:
- With 2 columns, text naturally reflows if one side is longer
- With 3+ columns, content is split exactly at your `/col` breaks — if you forget a `/col`, everything ends up in one column

### Dev mode overflow detection

Run with `--dev` to see per-page fill indicators. Each page gets a badge showing its fill percentage (e.g. `p3: 87%`). Pages that overflow show a red "OVERFLOW" badge. This helps you find pages that need a `/page` break or content trimming.

### Cover pages

Content after a `/cover` directive (until the next `/page`) becomes the cover page content. Typically this is an H1 title and H2 subtitle. Cover pages have no page numbers and no column layout — they're always single-column with centered content.

---

## Dev server config editor

The `/_config` page (default when running `zinewire serve`) provides a visual editor with a live preview.

### Layout

The editor has a left sidebar with controls and a right panel showing the live preview in an iframe. Mode tabs at the top of the preview let you switch between Print, Manual, and Web views. A zoom slider scales the preview.

### Controls

The sidebar is organized into sections:

- **Document** — title, page size, orientation, column count, version
- **Output** — imposition mode dropdown (booklet, mini-zine, trifold, french fold, micro-mini) with folding instructions that appear when an imposition is selected
- **Fonts** — heading, body, and mono font dropdowns with preset Google Fonts options plus a custom text input
- **Font sizes** — body, H1-H4, cover H1/H2, small, tiny, micro — each with a number and unit selector
- **Typography** — line height, paragraph spacing, letter spacing for H1-H4
- **Colors** — color picker swatches + hex text inputs for all theme colors
- **Margins** — vertical, horizontal, spine with units
- **Page numbers** — show/hide toggle, color, size, position, font
- **Layout** — column justify, column gap, table padding/font size, list padding, custom CSS path

### Save behavior

Changing any control instantly updates the live preview (debounced 200ms) without saving to disk. The **Save** button writes the current configuration to `zinewire.toml`. If no TOML file exists yet, one is created next to the source file. Only fields that differ from defaults are written.

---

## Printing tips

### Browser print settings

When printing zinewire HTML from a browser:

- **Margins**: set to "None" — zinewire's `@page` rule sets `margin: 0` and handles margins internally via CSS
- **Background graphics**: enable this — without it, cover images, table header backgrounds, and accent colors won't print
- **Scale**: 100% — the `@page { size: }` rule tells the browser the exact page dimensions

### Color fidelity

zinewire injects `print-color-adjust: exact` to ensure colors print as specified. Most modern browsers respect this, but some printer drivers may still convert to grayscale.

### Fonts

Fonts are loaded from Google Fonts via CDN. If you're printing offline or the network is unavailable, the browser falls back to system fonts (sans-serif for headings, serif for body, monospace for code). For reliable offline printing, use `custom-css` to declare `@font-face` rules pointing to local font files.

### `@page` and CSS variables

The `@page { size: }` rule uses literal mm values, not CSS variables, because browsers don't support CSS custom properties inside `@page`. This is handled automatically — you don't need to worry about it unless you're writing custom CSS that targets `@page`.
