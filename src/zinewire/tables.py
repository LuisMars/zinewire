"""JSON table directive for zinewire.

Processes /table directives that load data from JSON files and render
as markdown tables before the main markdown conversion.

JSON format:
    {
        "columns": ["Name", "Price", "Weight"],
        "items": [
            {"name": "Sword", "price": "10g", "weight": "3lb"},
            {"name": "Shield", "price": "8g", "weight": "5lb"}
        ],
        "align": ["left", "right", "center"],       // optional
        "display_columns": ["Item", "Cost", "Wt"]   // optional header aliases
    }

Column lookup: items are matched by lowercase column name as dict key.
If "display_columns" is provided, those are shown as headers instead.
"""

import json
import re
from pathlib import Path


def render_table(data: dict) -> str:
    """Render a JSON table definition to markdown table syntax."""
    columns = data["columns"]
    items = data["items"]
    display = data.get("display_columns", columns)
    align = data.get("align", [])

    # Header row
    header = "| " + " | ".join(display) + " |"

    # Separator with alignment
    sep_parts = []
    for i in range(len(columns)):
        a = align[i] if i < len(align) else "left"
        if a == "center":
            sep_parts.append(":---:")
        elif a == "right":
            sep_parts.append("---:")
        else:
            sep_parts.append(":---")
    separator = "|" + "|".join(sep_parts) + "|"

    # Data rows
    rows = []
    for item in items:
        values = []
        for col in columns:
            key = col.lower().replace(" ", "_")
            value = item.get(key, item.get(col, item.get(col.lower(), "")))
            values.append(str(value) if value is not None else "")
        rows.append("| " + " | ".join(values) + " |")

    return "\n".join([header, separator] + rows)


def process_tables(md_text: str, base_dir: Path | None = None) -> str:
    """Replace /table directives with rendered markdown tables.

    Args:
        md_text: Raw markdown text.
        base_dir: Directory to resolve relative JSON paths from.

    Returns:
        Markdown text with /table directives replaced by table markup.
    """
    if base_dir is None:
        base_dir = Path(".")

    def _replace(match):
        json_path = base_dir / match.group(1)
        if not json_path.exists():
            return f"<!-- ERROR: Table file not found: {match.group(1)} -->"
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            return "\n" + render_table(data) + "\n"
        except json.JSONDecodeError as e:
            return f"<!-- ERROR: Invalid JSON in {match.group(1)}: {e} -->"
        except KeyError as e:
            return f"<!-- ERROR: Missing key {e} in {match.group(1)} -->"

    return re.sub(r"^/table\s+(\S+)\s*$", _replace, md_text, flags=re.MULTILINE)
